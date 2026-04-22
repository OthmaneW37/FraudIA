"""
hitl.py — Human-in-the-Loop : Apprentissage incrémental par feedback humain.

Fonctionnement :
  1. Quand un analyste confirme une transaction comme "frauduleuse" ou "valide",
     les features de cette transaction sont sauvegardées dans data/human_feedback.parquet.
  2. Le superadmin peut déclencher un fine-tuning incrémental du modèle XGBoost
     via POST /hitl/retrain. XGBoost ajoute de nouveaux arbres aux arbres existants
     (warm-start) en exploitant uniquement les exemples annotés par les humains.
  3. Le modèle affiné est sauvegardé et rechargé à chaud sans interruption de service.

Architecture :
  Annotations DB  →  save_feedback()  →  human_feedback.parquet
                                                       ↓
  Superadmin UI   →  trigger_retrain() →  XGBoost warm-start  →  model.joblib  →  reload
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
FEEDBACK_PATH = DATA_DIR / "human_feedback.parquet"
HITL_HISTORY_PATH = DATA_DIR / "hitl_history.json"
DB_PATH = PROJECT_ROOT / "users.db"

# Nombre minimum de feedbacks pour déclencher un retrain
MIN_FEEDBACK_FOR_RETRAIN = 5


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def save_feedback(
    transaction_id: str,
    form_data: Dict[str, Any],
    true_label: int,  # 1=fraude, 0=valide
    analyst_id: str,
) -> bool:
    """
    Sauvegarde le feedback humain d'une annotation dans le fichier parquet.
    
    Retourne True si sauvegardé avec succès.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    record = {**form_data, "true_label": true_label, "annotated_at": datetime.utcnow().isoformat(), "analyst_id": analyst_id, "transaction_id": transaction_id, "used_in_retrain": False}

    record_df = pd.DataFrame([record])

    if FEEDBACK_PATH.exists():
        existing = pd.read_parquet(FEEDBACK_PATH)
        # Éviter les doublons : ignorer si cette transaction est déjà annotée
        if transaction_id in existing["transaction_id"].values:
            logger.info(f"[HITL] Feedback déjà enregistré pour {transaction_id}, mise à jour du label...")
            existing.loc[existing["transaction_id"] == transaction_id, "true_label"] = true_label
            existing.loc[existing["transaction_id"] == transaction_id, "used_in_retrain"] = False
            existing.to_parquet(FEEDBACK_PATH, index=False)
            return True
        combined = pd.concat([existing, record_df], ignore_index=True)
    else:
        combined = record_df

    combined.to_parquet(FEEDBACK_PATH, index=False)
    count = int((~combined["used_in_retrain"]).sum())
    logger.info(f"[HITL] Feedback enregistré pour {transaction_id} (label={true_label}). En attente: {count}")
    return True


def get_pending_feedback() -> pd.DataFrame:
    """Retourne les feedbacks non encore utilisés en retrain."""
    if not FEEDBACK_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(FEEDBACK_PATH)
    return df[~df["used_in_retrain"]].copy()


def get_all_feedback() -> pd.DataFrame:
    """Retourne tous les feedbacks."""
    if not FEEDBACK_PATH.exists():
        return pd.DataFrame()
    return pd.read_parquet(FEEDBACK_PATH)


def get_hitl_stats() -> Dict[str, Any]:
    """Retourne les statistiques HITL globales."""
    if not FEEDBACK_PATH.exists():
        return {
            "total_feedback": 0,
            "pending_feedback": 0,
            "used_feedback": 0,
            "fraud_confirmed": 0,
            "valid_confirmed": 0,
            "last_retrain": None,
            "retrain_count": 0,
            "can_retrain": False,
        }

    df = pd.read_parquet(FEEDBACK_PATH)
    history = _load_history()

    pending = int((~df["used_in_retrain"]).sum())
    used = int(df["used_in_retrain"].sum())

    return {
        "total_feedback": len(df),
        "pending_feedback": pending,
        "used_feedback": used,
        "fraud_confirmed": int((df["true_label"] == 1).sum()),
        "valid_confirmed": int((df["true_label"] == 0).sum()),
        "last_retrain": history[-1]["timestamp"] if history else None,
        "retrain_count": len(history),
        "can_retrain": pending >= MIN_FEEDBACK_FOR_RETRAIN,
        "min_feedback_required": MIN_FEEDBACK_FOR_RETRAIN,
    }


def incremental_retrain(
    model_name: str = "xgboost",
    app_state=None,
) -> Dict[str, Any]:
    """
    Déclenche un fine-tuning incrémental du modèle sur les feedbacks humains en attente.
    
    Utilise le warm-start XGBoost : les nouveaux arbres se greffent sur le modèle existant.
    Le modèle mis à jour est sauvegardé et rechargé dans le service API.
    
    Returns dict avec les résultats du retrain.
    """
    logger.info(f"[HITL] Démarrage du fine-tuning incrémental pour {model_name}...")

    pending_df = get_pending_feedback()
    if len(pending_df) < MIN_FEEDBACK_FOR_RETRAIN:
        return {
            "success": False,
            "message": f"Pas assez de feedbacks ({len(pending_df)}/{MIN_FEEDBACK_FOR_RETRAIN} minimum).",
        }

    # ── 1. Charger le préprocesseur et le modèle courant ─────────────────────
    from src.data.preprocessor import FraudPreprocessor
    from src.models.trainer import ModelTrainer

    preprocessor_path = MODELS_DIR / "preprocessor.joblib"
    model_path = MODELS_DIR / f"{model_name}.joblib"

    if not preprocessor_path.exists() or not model_path.exists():
        return {"success": False, "message": "Modèle ou préprocesseur introuvable."}

    preprocessor = FraudPreprocessor.load(preprocessor_path)
    
    # ── 2. Préparer les features de feedback ──────────────────────────────────
    label_col = "true_label"
    feature_cols_to_drop = ["true_label", "annotated_at", "analyst_id", "transaction_id", "used_in_retrain"]
    
    X_feedback_raw = pending_df.drop(columns=[c for c in feature_cols_to_drop if c in pending_df.columns], errors="ignore")
    y_feedback = pending_df[label_col].astype(int).values

    # Vérifier qu'on a les deux classes pour un fine-tuning utile
    unique_labels = np.unique(y_feedback)
    if len(unique_labels) < 2:
        logger.warning("[HITL] Tous les feedbacks ont le même label — retrain ignoré pour éviter le biais.")
        return {
            "success": False,
            "message": "Les feedbacks doivent contenir les deux classes (fraude et valide) pour un retrain utile.",
        }

    # Appliquer le même préprocesseur que le modèle original
    try:
        X_proc = preprocessor.transform(X_feedback_raw)
    except Exception as exc:
        logger.error(f"[HITL] Erreur de preprocessing: {exc}")
        return {"success": False, "message": f"Erreur de preprocessing : {exc}"}

    # ── 3. Fine-tuning XGBoost (warm-start) ──────────────────────────────────
    import joblib
    from xgboost import XGBClassifier

    existing_model = joblib.load(model_path)

    n_neg = int((y_feedback == 0).sum())
    n_pos = int((y_feedback == 1).sum())
    scale_pos_weight = n_neg / max(n_pos, 1)

    # Warm-start : ajouter 50 arbres sur les données de feedback
    fine_tuned = XGBClassifier(
        n_estimators=50,            # Arbres supplémentaires sur le feedback
        max_depth=4,
        learning_rate=0.02,         # LR très faible pour ne pas oublier l'ancien modèle
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
    )
    fine_tuned.fit(X_proc, y_feedback, xgb_model=existing_model)

    # ── 4. Sauvegarder le modèle amélioré ────────────────────────────────────
    joblib.dump(fine_tuned, model_path)
    logger.success(f"[HITL] Modèle {model_name} mis à jour avec {len(pending_df)} feedbacks.")

    # ── 5. Recharger le modèle dans le service API à chaud ───────────────────
    reloaded = False
    if app_state is not None:
        try:
            if hasattr(app_state, "model_service") and app_state.model_service is not None:
                app_state.model_service.trainers[model_name] = ModelTrainer.load(model_path, model_name=model_name)
                # Reconstruire l'explainer SHAP pour ce modèle
                if hasattr(app_state, "full_service") and app_state.full_service is not None:
                    from src.xai.explainer import FraudExplainer
                    app_state.full_service.explainers[model_name] = FraudExplainer(
                        model=app_state.model_service.trainers[model_name].model,
                        feature_names=preprocessor.feature_names,
                        model_type="tree",
                    )
                reloaded = True
                logger.success("[HITL] Modèle rechargé à chaud dans le service API.")
        except Exception as exc:
            logger.warning(f"[HITL] Rechargement à chaud échoué : {exc}. Redémarrage requis.")

    # ── 6. Marquer les feedbacks comme utilisés ──────────────────────────────
    all_df = pd.read_parquet(FEEDBACK_PATH)
    used_ids = pending_df["transaction_id"].values
    all_df.loc[all_df["transaction_id"].isin(used_ids), "used_in_retrain"] = True
    all_df.to_parquet(FEEDBACK_PATH, index=False)

    # ── 7. Enregistrer dans l'historique ─────────────────────────────────────
    history_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "model_name": model_name,
        "feedback_count": len(pending_df),
        "fraud_confirmed": int((y_feedback == 1).sum()),
        "valid_confirmed": int((y_feedback == 0).sum()),
        "reloaded_live": reloaded,
    }
    _save_history_entry(history_entry)

    return {
        "success": True,
        "message": f"Fine-tuning réussi sur {len(pending_df)} annotations humaines.",
        "details": history_entry,
    }


def _load_history() -> List[Dict]:
    if not HITL_HISTORY_PATH.exists():
        return []
    try:
        with HITL_HISTORY_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_history_entry(entry: Dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    history = _load_history()
    history.append(entry)
    with HITL_HISTORY_PATH.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def extract_feedback_from_annotation(
    db_row: Dict[str, Any],
    annotation: str,
    analyst_id: str,
) -> bool:
    """
    Extrait les features de form_data et sauvegarde le feedback.
    Appelé automatiquement après chaque annotation d'un analyste.
    
    annotation : "frauduleuse" ou "valide"
    """
    if annotation not in ("frauduleuse", "valide"):
        return False

    true_label = 1 if annotation == "frauduleuse" else 0

    form_data_raw = db_row.get("form_data")
    if not form_data_raw:
        logger.warning(f"[HITL] Pas de form_data pour tx {db_row.get('transaction_id')} — feedback ignoré.")
        return False

    try:
        form_data = json.loads(form_data_raw) if isinstance(form_data_raw, str) else form_data_raw
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"[HITL] form_data invalide pour tx {db_row.get('transaction_id')} — feedback ignoré.")
        return False

    return save_feedback(
        transaction_id=db_row.get("transaction_id", "unknown"),
        form_data=form_data,
        true_label=true_label,
        analyst_id=analyst_id,
    )
