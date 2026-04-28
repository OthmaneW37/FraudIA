"""
train.py - Pipeline d'entraînement complet avec cross-validation, feature selection,
           ensemble soft-voting et calibration F0.5 des seuils.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    fbeta_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.data.loader import DataLoader
from src.data.preprocessor import FraudPreprocessor
from src.models.tuner import XGBoostTuner
from src.models.trainer import ModelTrainer, MODELS_DIR

THRESHOLDS_PATH = MODELS_DIR / "thresholds.json"
METRICS_PATH = MODELS_DIR / "metrics.json"
RANDOM_STATE = 42


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Entraînement complet du modèle champion")
    parser.add_argument("--n-trials", type=int, default=50,
                        help="Nombre d'essais Optuna (défaut: 50)")
    parser.add_argument("--skip-optuna", action="store_true",
                        help="Ignorer Optuna et utiliser les paramètres par défaut")
    parser.add_argument("--n-features", type=int, default=0,
                        help="Nombre de features à garder (0 = toutes, défaut: 0)")
    parser.add_argument("--no-ensemble", action="store_true",
                        help="Ne pas créer l'ensemble soft-voting")
    return parser.parse_args()


def compute_best_fbeta_threshold(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    beta: float = 0.5,
) -> tuple[float, float]:
    """
    Trouve le seuil qui maximise le F-beta sur la courbe PR.
    F0.5 = privilégie la précision (pénalise plus les FP que les FN).
    """
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)
    best_threshold = 0.5
    best_fbeta = 0.0
    for i in range(len(thresholds)):
        y_pred = (y_proba >= thresholds[i]).astype(int)
        fb = fbeta_score(y_true, y_pred, beta=beta, zero_division=0)
        if fb > best_fbeta:
            best_fbeta = fb
            best_threshold = float(thresholds[i])
    return best_threshold, best_fbeta


def select_features(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: List[str],
    n_features: int,
) -> np.ndarray:
    """Sélectionne les n_features les plus importantes via XGBoost."""
    if n_features <= 0 or n_features >= len(feature_names):
        return X, feature_names
    from xgboost import XGBClassifier
    model = XGBClassifier(
        n_estimators=100, max_depth=5, learning_rate=0.1,
        scale_pos_weight=(y == 0).sum() / max((y == 1).sum(), 1),
        tree_method="hist", random_state=RANDOM_STATE, n_jobs=-1, verbosity=0,
    )
    model.fit(X, y)
    importances = model.feature_importances_
    top_indices = np.argsort(importances)[-n_features:]
    kept_names = [feature_names[i] for i in sorted(top_indices)]
    logger.info(f"Feature selection : {len(kept_names)}/{len(feature_names)} colonnes gardées")
    return X[:, top_indices], kept_names


def save_thresholds(thresholds: dict) -> None:
    THRESHOLDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with THRESHOLDS_PATH.open("w", encoding="utf-8") as fh:
        json.dump(thresholds, fh, indent=2)
    logger.success(f"Seuils sauvegardés dans {THRESHOLDS_PATH}")


def save_metrics(metrics: dict) -> None:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    logger.success(f"Métriques sauvegardées dans {METRICS_PATH}")


def main() -> None:
    args = parse_args()

    logger.info("=" * 60)
    logger.info("   FRAUD DETECTION - Pipeline d'entraînement v3.0")
    logger.info("   CV + Feature Selection + Ensemble + Calibration F0.5")
    logger.info("=" * 60)

    # ── 1. Chargement ───────────────────────────────────────────────────────
    logger.info("Étape 1/6 : Chargement du dataset...")
    loader = DataLoader()
    df = loader.load()
    cols_to_drop = ["organization", "transaction_id", "user_id", "transaction_timestamp"]
    df_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    logger.info(f"Dataset prêt : {len(df_clean):,} lignes x {len(df_clean.columns)} colonnes")

    # ── 2. Splits ───────────────────────────────────────────────────────────
    logger.info("Étape 2/6 : Splits train/val/test stratifiés...")
    X_train, X_val, X_test, y_train, y_val, y_test = loader.get_splits(df_clean)

    # ── 3. Preprocessing + SMOTE ────────────────────────────────────────────
    logger.info("Étape 3/6 : Preprocessing + SMOTE...")
    preprocessor = FraudPreprocessor()
    X_train_proc, y_train_proc = preprocessor.fit_transform_train(X_train, y_train)
    X_val_proc = preprocessor.transform(X_val)
    X_test_proc = preprocessor.transform(X_test)
    preprocessor.save()
    logger.success("Preprocessor sauvegardé")

    # ── 4. Feature Selection (optionnelle) ──────────────────────────────────
    if args.n_features > 0:
        logger.info(f"Étape 4/6 : Feature selection top-{args.n_features}...")
        all_names = preprocessor.feature_names
        X_train_proc, selected_names = select_features(
            X_train_proc, y_train_proc, all_names, args.n_features,
        )
        # Appliquer la même sélection sur val/test
        val_indices = [all_names.index(n) for n in selected_names]
        X_val_proc = X_val_proc[:, val_indices]
        X_test_proc = X_test_proc[:, val_indices]
        # Mettre à jour le preprocessor pour l'inférence future
        preprocessor._selected_indices = val_indices
    else:
        logger.info("Étape 4/6 : Feature selection ignorée (--n-features non spécifié)")

    # ── 5. Entraînement des modèles individuels ─────────────────────────────
    logger.info("Étape 5/6 : Entraînement XGBoost + RF + LR...")
    thresholds: Dict[str, float] = {}
    models_for_ensemble = []

    for model_name in ["xgboost", "random_forest", "logistic_regression"]:
        logger.info(f"--- {model_name.upper()} ---")

        if model_name == "xgboost" and not args.skip_optuna:
            tuner = XGBoostTuner()
            tuner.optimize(X_train_proc, y_train_proc, X_val_proc, y_val, n_trials=args.n_trials)
            trainer = tuner.train_final_model(X_train_proc, y_train_proc, X_val_proc, y_val)
        else:
            trainer = ModelTrainer(model_name=model_name)
            trainer.fit(X_train_proc, y_train_proc, X_val=X_val_proc, y_val=y_val)

        # Sauvegarder immédiatement après entraînement
        save_path = trainer.save()
        logger.success(f"  Modèle sauvegardé : {save_path}")

        # Évaluation
        y_val_proba = trainer.predict_proba(X_val_proc)[:, 1]
        threshold, best_fbeta = compute_best_fbeta_threshold(
            y_val.to_numpy(), y_val_proba, beta=0.5,
        )
        thresholds[model_name] = round(threshold, 4)
        logger.info(f"  Seuil F0.5 optimal : {threshold:.4f} (F0.5={best_fbeta:.4f})")

        y_test_proba = trainer.predict_proba(X_test_proc)[:, 1]
        y_test_pred = (y_test_proba >= threshold).astype(int)

        auc_pr = average_precision_score(y_test, y_test_proba)
        f1 = f1_score(y_test, y_test_pred, zero_division=0)
        prec = precision_score(y_test, y_test_pred, zero_division=0)
        rec = recall_score(y_test, y_test_pred, zero_division=0)

        logger.info(
            f"  Test → AUC-PR: {auc_pr:.4f} | F1: {f1:.4f} | "
            f"Précision: {prec:.4f} | Rappel: {rec:.4f}"
        )

        models_for_ensemble.append((model_name, trainer.model))

    # ── 6. Ensemble Soft-Voting ─────────────────────────────────────────────
    if not args.no_ensemble and len(models_for_ensemble) >= 2:
        logger.info("Étape 6/6 : Ensemble soft-voting XGBoost + RF + LR...")
        ensemble = VotingClassifier(
            estimators=models_for_ensemble,
            voting="soft",
            n_jobs=-1,
        )
        ensemble.fit(X_train_proc, y_train_proc)

        y_val_ens = ensemble.predict_proba(X_val_proc)[:, 1]
        ens_threshold, ens_fbeta = compute_best_fbeta_threshold(
            y_val.to_numpy(), y_val_ens, beta=0.5,
        )
        thresholds["ensemble"] = round(ens_threshold, 4)

        y_test_ens = ensemble.predict_proba(X_test_proc)[:, 1]
        y_test_ens_pred = (y_test_ens >= ens_threshold).astype(int)

        ens_auc_pr = average_precision_score(y_test, y_test_ens)
        ens_f1 = f1_score(y_test, y_test_ens_pred, zero_division=0)
        ens_prec = precision_score(y_test, y_test_ens_pred, zero_division=0)
        ens_rec = recall_score(y_test, y_test_ens_pred, zero_division=0)

        logger.info(
            f"  Ensemble → AUC-PR: {ens_auc_pr:.4f} | F1: {ens_f1:.4f} | "
            f"Précision: {ens_prec:.4f} | Rappel: {ens_rec:.4f}"
        )

        import joblib
        ensemble_path = MODELS_DIR / "ensemble.joblib"
        joblib.dump(ensemble, ensemble_path)
        logger.success(f"Ensemble sauvegardé : {ensemble_path}")
    else:
        logger.info("Étape 6/6 : Ensemble ignoré (--no-ensemble)")

    save_thresholds(thresholds)

    # Sauvegarder les métriques pour le health endpoint
    best_model = "ensemble" if "ensemble" in thresholds else "xgboost"
    best_threshold = thresholds.get(best_model, 0.5)

    # Recalculer métriques avec le meilleur modèle pour le fichier metrics.json
    if best_model == "ensemble":
        best_proba = ensemble.predict_proba(X_test_proc)[:, 1]
    else:
        best_proba = ModelTrainer.load(MODELS_DIR / "xgboost.joblib", "xgboost").predict_proba(X_test_proc)[:, 1]
    best_pred = (best_proba >= best_threshold).astype(int)

    save_metrics({
        "auc_pr": round(average_precision_score(y_test, best_proba), 4),
        "f1": round(f1_score(y_test, best_pred, zero_division=0), 4),
        "precision_fraud": round(precision_score(y_test, best_pred, zero_division=0), 4),
        "recall_fraud": round(recall_score(y_test, best_pred, zero_division=0), 4),
        "accuracy": round(accuracy_score(y_test, best_pred), 4),
        "n_features": X_train_proc.shape[1],
        "training_samples": len(y_train_proc),
        "best_model": best_model,
        "threshold": best_threshold,
    })

    logger.info("=" * 60)
    logger.success("Pipeline terminé — tous les modèles et seuils sont à jour")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
