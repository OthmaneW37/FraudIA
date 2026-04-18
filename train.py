"""
train.py - Script de re-entrainement complet du modele champion.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from loguru import logger
from sklearn.metrics import average_precision_score, f1_score, precision_recall_curve

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.data.loader import DataLoader
from src.data.preprocessor import FraudPreprocessor
from src.models.tuner import XGBoostTuner


THRESHOLDS_PATH = Path("models/thresholds.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Entrainer le modele XGBoost champion")
    parser.add_argument(
        "--n-trials",
        type=int,
        default=50,
        help="Nombre d'essais Optuna (defaut: 50, recommande: 50-100).",
    )
    parser.add_argument(
        "--skip-optuna",
        action="store_true",
        help="Ignorer Optuna et utiliser les parametres par defaut.",
    )
    return parser.parse_args()


def compute_best_f1_threshold(y_true: np.ndarray, y_proba: np.ndarray) -> tuple[float, float]:
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)
    f1_scores = 2 * precisions[:-1] * recalls[:-1] / (precisions[:-1] + recalls[:-1] + 1e-9)
    best_idx = int(np.argmax(f1_scores))
    return float(thresholds[best_idx]), float(f1_scores[best_idx])


def save_thresholds(thresholds: dict[str, float]) -> None:
    THRESHOLDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with THRESHOLDS_PATH.open("w", encoding="utf-8") as fh:
        json.dump(thresholds, fh, indent=2)
    logger.success(f"Seuils calibres sauvegardes dans {THRESHOLDS_PATH}")


def main() -> None:
    args = parse_args()

    logger.info("=" * 60)
    logger.info("   FRAUD DETECTION - Pipeline d'entrainement v2.1")
    logger.info("=" * 60)

    logger.info("Etape 1/5 : Chargement du dataset + Feature Engineering sequentiel...")
    loader = DataLoader()
    df = loader.load()

    cols_to_drop = ["organization", "transaction_id", "user_id", "transaction_timestamp"]
    df_clean = df.drop(columns=[column for column in cols_to_drop if column in df.columns])
    logger.info(f"Dataset pret : {len(df_clean):,} lignes x {len(df_clean.columns)} colonnes")

    logger.info("Etape 2/5 : Splits train/val/test stratifies...")
    X_train, X_val, X_test, y_train, y_val, y_test = loader.get_splits(df_clean)

    logger.info("Etape 3/5 : Preprocessing + SMOTE...")
    preprocessor = FraudPreprocessor()
    X_train_proc, y_train_proc = preprocessor.fit_transform_train(X_train, y_train)
    X_val_proc = preprocessor.transform(X_val)
    X_test_proc = preprocessor.transform(X_test)

    preprocessor.save()
    logger.success("Preprocessor sauvegarde")

    from src.models.trainer import ModelTrainer

    thresholds: dict[str, float] = {}
    models_to_train = ["xgboost", "random_forest", "logistic_regression"]

    for model_name in models_to_train:
        logger.info(f"Etape 4/5 : Entrainement de {model_name}...")

        if model_name == "xgboost" and not args.skip_optuna:
            logger.info(f"AutoML Optuna pour XGBoost - {args.n_trials} essais...")
            tuner = XGBoostTuner()
            tuner.optimize(
                X_train_proc,
                y_train_proc,
                X_val_proc,
                y_val,
                n_trials=args.n_trials,
            )
            trainer = tuner.train_final_model(X_train_proc, y_train_proc, X_val_proc, y_val)
        else:
            trainer = ModelTrainer(model_name=model_name)
            trainer.fit(X_train_proc, y_train_proc, X_val=X_val_proc, y_val=y_val)

        y_val_proba = trainer.predict_proba(X_val_proc)[:, 1]
        threshold, best_f1 = compute_best_f1_threshold(y_val.to_numpy(), y_val_proba)
        thresholds[model_name] = round(threshold, 4)
        logger.info(f"Seuil F1 optimal pour {model_name}: {threshold:.4f} (F1={best_f1:.4f})")

        y_test_proba = trainer.predict_proba(X_test_proc)[:, 1]
        auc_pr = average_precision_score(y_test, y_test_proba)
        y_test_pred = (y_test_proba >= threshold).astype(int)
        f1 = f1_score(y_test, y_test_pred, zero_division=0)
        logger.info(f"Resultat {model_name} -> AUC-PR: {auc_pr:.4f} | F1@seuil: {f1:.4f}")

        save_path = trainer.save()
        logger.success(f"Modele {model_name} sauvegarde : {save_path}")

    save_thresholds(thresholds)

    logger.info("=" * 60)
    logger.success("Tous les modeles ont ete mis a jour avec seuils calibres")
    logger.info("=" * 60)
    logger.info("Relancez le backend : .\\venv\\Scripts\\python.exe -m uvicorn api.main:app --reload")


if __name__ == "__main__":
    main()
