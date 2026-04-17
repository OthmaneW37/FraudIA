"""Évaluation rapide du modèle XGBoost sur val/test."""
import joblib, numpy as np, pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, precision_score, recall_score,
    f1_score, average_precision_score, roc_auc_score,
)
import sys; sys.path.insert(0, ".")
from src.data.preprocessor import FraudPreprocessor

models_dir = Path("models")
df = pd.read_csv("data/raw/improved_fraud_dataset.csv", low_memory=False)
print(f"Dataset : {df.shape[0]} lignes, {df.shape[1]} colonnes")
fraud_col = "is_fraud"
ratio = df[fraud_col].mean()
print(f"Taux de fraude : {ratio:.4%}")

cols_to_drop = ["organization", "transaction_id", "user_id", "transaction_timestamp"]
df_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
X = df_clean.drop(columns=[fraud_col])
y = df_clean[fraud_col]

X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=0.15, stratify=y, random_state=42)
X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.15/0.85, stratify=y_temp, random_state=42)

preprocessor = FraudPreprocessor.load(models_dir / "preprocessor.joblib")
X_val_proc = preprocessor.transform(X_val)
X_test_proc = preprocessor.transform(X_test)

xgb = joblib.load(models_dir / "xgboost.joblib")

for name, X_e, y_e in [("VALIDATION", X_val_proc, y_val), ("TEST", X_test_proc, y_test)]:
    y_prob = xgb.predict_proba(X_e)[:, 1]
    print(f"\n{'='*55}")
    print(f"  XGBoost — {name}")
    print(f"{'='*55}")
    for t in [0.5, 0.8]:
        y_pred = (y_prob >= t).astype(int)
        p = precision_score(y_e, y_pred, zero_division=0)
        r = recall_score(y_e, y_pred, zero_division=0)
        f = f1_score(y_e, y_pred, zero_division=0)
        print(f"  Seuil {t} => Precision={p:.4f}  Recall={r:.4f}  F1={f:.4f}")
    auc_pr = average_precision_score(y_e, y_prob)
    auc_roc = roc_auc_score(y_e, y_prob)
    print(f"  AUC-PR  = {auc_pr:.4f}")
    print(f"  AUC-ROC = {auc_roc:.4f}")
    print()
    print(classification_report(y_e, (y_prob >= 0.5).astype(int), target_names=["Legit", "Fraude"]))
