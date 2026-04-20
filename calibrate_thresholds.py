"""
calibrate_thresholds.py — Calibration des seuils de décision par modèle.

Objectif :
  Trouver pour chaque modèle le seuil qui donne un bon équilibre entre
  précision et rappel sur le val set, et sauvegarder dans models/thresholds.json.

Stratégie : seuil F1-beta (beta=0.5 → pénalise plus les FP que les FN)
  Dans la fraude bancaire, un faux positif (blocage légitime) est aussi
  coûteux qu'un faux négatif (fraude manquée) → beta=0.5 privilégie la précision.
"""

import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import fbeta_score, precision_recall_curve

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.data.loader import DataLoader
from src.data.preprocessor import FraudPreprocessor, MODELS_DIR
from src.models.trainer import ModelTrainer


def calibrate():
    print("=== Chargement dataset ===")
    loader = DataLoader()
    df = loader.load()

    cols_to_drop = ['organization', 'transaction_id', 'user_id', 'transaction_timestamp',
                    'is_night', 'time_diff']
    df_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    _, X_val, _, _, y_val, _ = loader.get_splits(df_clean)

    print("=== Chargement preprocessor ===")
    preprocessor = FraudPreprocessor.load(MODELS_DIR / "preprocessor.joblib")
    X_val_proc = preprocessor.transform(X_val)

    thresholds = {}

    for name in ["xgboost", "random_forest", "logistic_regression"]:
        path = MODELS_DIR / f"{name}.joblib"
        if not path.exists():
            print(f"  [{name}] ABSENT — ignoré")
            continue

        trainer = ModelTrainer.load(path, model_name=name)
        y_prob = trainer.predict_proba(X_val_proc)[:, 1]

        precisions, recalls, thresh_vals = precision_recall_curve(y_val, y_prob)

        # Calcul F0.5 pour chaque seuil (privilégie la précision sur le rappel)
        best_threshold = 0.5
        best_f05 = 0.0

        for i, t in enumerate(thresh_vals):
            if precisions[i] < 0.50:   # Précision minimale acceptable : 50%
                continue
            y_pred = (y_prob >= t).astype(int)
            f05 = fbeta_score(y_val, y_pred, beta=0.5, zero_division=0)
            if f05 > best_f05:
                best_f05 = f05
                best_threshold = float(t)

        # Stats à ce seuil
        y_pred_final = (y_prob >= best_threshold).astype(int)
        n_flagged = y_pred_final.sum()
        tp = ((y_pred_final == 1) & (y_val == 1)).sum()
        fp = ((y_pred_final == 1) & (y_val == 0)).sum()
        precision_at = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall_at = tp / y_val.sum() if y_val.sum() > 0 else 0

        # Distribution des scores (pour info)
        p10, p25, p50, p75, p90 = np.percentile(y_prob, [10, 25, 50, 75, 90])

        print(f"\n  [{name}]")
        print(f"    Seuil optimal F0.5   : {best_threshold:.4f}")
        print(f"    Précision            : {precision_at:.1%}")
        print(f"    Rappel               : {recall_at:.1%}")
        print(f"    Transactions flaggées: {n_flagged:,} / {len(y_val):,}")
        print(f"    Scores (p10/p50/p90) : {p10:.3f} / {p50:.3f} / {p90:.3f}")

        thresholds[name] = round(best_threshold, 4)

    # Sauvegarde
    out_path = MODELS_DIR / "thresholds.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(thresholds, f, indent=2)

    print(f"\n=== Seuils sauvegardés dans {out_path} ===")
    print(json.dumps(thresholds, indent=2))
    return thresholds


if __name__ == "__main__":
    calibrate()
