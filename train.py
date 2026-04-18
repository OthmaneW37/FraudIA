"""
train.py — Script de ré-entraînement complet du modèle Champion.

Pipeline complet :
  1. Chargement du dataset (+ Feature Engineering Séquentiel automatique)
  2. Preprocessing (SMOTE pour rééquilibrer)
  3. AutoML Optuna : 50 essais pour trouver les meilleurs hyperparamètres XGBoost
  4. Entraînement final avec les meilleurs paramètres
  5. Sauvegarde → models/xgboost.joblib + models/preprocessor.joblib

Usage :
    python train.py
    python train.py --n-trials 100   # Plus de trials = meilleure précision
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ajouter la racine au path pour les imports src.*
sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    f1_score,
)

from src.data.loader import DataLoader
from src.data.preprocessor import FraudPreprocessor
from src.models.tuner import XGBoostTuner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Entraîner le modèle XGBoost Champion")
    parser.add_argument(
        "--n-trials",
        type=int,
        default=50,
        help="Nombre d'essais Optuna (défaut: 50, recommandé: 50-100)",
    )
    parser.add_argument(
        "--skip-optuna",
        action="store_true",
        help="Ignorer Optuna et utiliser les paramètres par défaut (plus rapide)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logger.info("=" * 60)
    logger.info("   FRAUD DETECTION — Pipeline d'Entraînement v2.0")
    logger.info("=" * 60)

    # ── 1. Chargement du dataset ─────────────────────────────────────────────
    logger.info("Étape 1/5 : Chargement du dataset + Feature Engineering Séquentiel...")
    loader = DataLoader()
    df = loader.load()  # Feature Engineering Séquentiel intégré ici

    # Colonnes à exclure de X (identifiants non prédictifs)
    cols_to_drop = ["organization", "transaction_id", "user_id", "transaction_timestamp"]
    df_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    logger.info(f"Dataset prêt : {len(df_clean):,} lignes × {len(df_clean.columns)} colonnes")

    # ── 2. Splits Train / Val / Test ─────────────────────────────────────────
    logger.info("Étape 2/5 : Splits train/val/test stratifiés...")
    X_train, X_val, X_test, y_train, y_val, y_test = loader.get_splits(df_clean)

    # ── 3. Preprocessing Pipeline (SMOTE inclus) ─────────────────────────────
    logger.info("Étape 3/5 : Preprocessing + SMOTE...")
    preprocessor = FraudPreprocessor(smote_sampling_strategy=0.2)
    X_train_proc, y_train_proc = preprocessor.fit_transform_train(X_train, y_train)
    X_val_proc   = preprocessor.transform(X_val)
    X_test_proc  = preprocessor.transform(X_test)

    # Sauvegarde du preprocessor
    preprocessor.save()
    logger.success("Preprocessor sauvegardé ✓")

    # ── 4. Entraînement des Modèles ──────────────────────────────────────────
    from src.models.trainer import ModelTrainer
    models_to_train = ["xgboost", "random_forest", "logistic_regression"]
    
    for m_name in models_to_train:
        logger.info(f"Étape 4/5 : Entraînement de {m_name}...")
        
        if m_name == "xgboost" and not args.skip_optuna:
            logger.info(f"AutoML Optuna pour XGBoost — {args.n_trials} essais...")
            tuner = XGBoostTuner()
            best_params, _ = tuner.optimize(
                X_train_proc, y_train_proc,
                X_val_proc,   y_val,
                n_trials=args.n_trials,
            )
            trainer = tuner.train_final_model(X_train_proc, y_train_proc, X_val_proc, y_val)
        else:
            # Pour RF et LR, on utilise les paramètres par défaut optimisés
            trainer = ModelTrainer(model_name=m_name)
            trainer.fit(X_train_proc, y_train_proc, X_val=X_val_proc, y_val=y_val)

        # Évaluation rapide
        y_proba_test = trainer.predict_proba(X_test_proc)[:, 1]
        auc_pr = average_precision_score(y_test, y_proba_test)
        logger.info(f"Résultat {m_name} -> AUC-PR: {auc_pr:.4f}")

        # Sauvegarde
        save_path = trainer.save()
        logger.success(f"Modèle {m_name} sauvegardé : {save_path}")

    logger.info("=" * 60)
    logger.success("   Tous les modèles ont été mis à jour avec 27 features ✓")
    logger.info("=" * 60)

    logger.info("➜ Relancez le backend : .\\venv\\Scripts\\python.exe -m uvicorn api.main:app --reload")


if __name__ == "__main__":
    main()
