"""
retrain_optimized.py — Réentraînement XGBoost optimisé avec :
  1. Feature engineering enrichi (interactions, bins)
  2. Tuning bayésien des hyperparamètres via Optuna
  3. Suppression des features inutiles
"""
import sys, warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import optuna
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, classification_report
from xgboost import XGBClassifier

sys.path.insert(0, ".")
from src.data.preprocessor import FraudPreprocessor

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

MODELS_DIR = Path("models")
RANDOM_STATE = 42


# ── 1. Feature Engineering Enrichi ──────────────────────────────────────────

def enrich_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute des features dérivées à fort pouvoir discriminant."""
    df = df.copy()

    # Interactions heure × montant
    df["night_x_amount"] = df["is_night"] * df["transaction_amount"]
    df["night_x_log_amount"] = df["is_night"] * np.log1p(df["transaction_amount"])

    # Bins de montant (captures non-linéarités)
    df["amount_bin"] = pd.qcut(df["transaction_amount"], q=10, labels=False, duplicates="drop")

    # Heure cyclique (23h ≈ 0h)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    # Log du montant
    df["log_amount"] = np.log1p(df["transaction_amount"])

    # Ratio fee / amount
    if "fee_amount" in df.columns:
        df["fee_ratio"] = df["fee_amount"] / (df["transaction_amount"] + 1e-9)

    # Heure au carré (renforce le signal non-linéaire)
    df["hour_sq"] = df["hour"] ** 2

    # Interaction nuit × time_diff
    if "time_diff" in df.columns:
        df["night_x_timediff"] = df["is_night"] * df["time_diff"]

    return df


# ── 2. Préparation des données ──────────────────────────────────────────────

def prepare_data():
    print("Chargement du dataset...")
    df = pd.read_csv("data/raw/improved_fraud_dataset.csv", low_memory=False)
    print(f"  {len(df):,} lignes, fraude = {df['is_fraud'].mean():.2%}")

    # Suppression des colonnes inutiles
    cols_to_drop = [
        "organization", "transaction_id", "user_id", "transaction_timestamp",
        "currency", "country",  # 1 seule valeur → zéro signal
    ]
    df_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    # Feature engineering
    df_clean = enrich_features(df_clean)

    X = df_clean.drop(columns=["is_fraud"])
    y = df_clean["is_fraud"]

    # Splits stratifiés
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.15, stratify=y, random_state=RANDOM_STATE
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.15 / 0.85, stratify=y_temp, random_state=RANDOM_STATE
    )

    # Preprocessing (imputation + encoding + scaling)
    preprocessor = FraudPreprocessor(smote_sampling_strategy=0.3)
    X_train_proc, y_train_proc = preprocessor.fit_transform_train(X_train, y_train)
    X_val_proc = preprocessor.transform(X_val)
    X_test_proc = preprocessor.transform(X_test)

    return X_train_proc, y_train_proc, X_val_proc, y_val, X_test_proc, y_test, preprocessor


# ── 3. Tuning Optuna ────────────────────────────────────────────────────────

def objective(trial, X_train, y_train, X_val, y_val):
    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())

    params = {
        "n_estimators": trial.suggest_int("n_estimators", 300, 1500),
        "max_depth": trial.suggest_int("max_depth", 4, 12),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 50),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        "gamma": trial.suggest_float("gamma", 0.0, 5.0),
        "scale_pos_weight": n_neg / max(n_pos, 1),
        "eval_metric": "aucpr",
        "tree_method": "hist",
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
    }

    model = XGBClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=0,
    )

    y_prob = model.predict_proba(X_val)[:, 1]
    return roc_auc_score(y_val, y_prob)


def tune(X_train, y_train, X_val, y_val, n_trials=50):
    print(f"\nOptimisation bayésienne ({n_trials} essais)...")
    study = optuna.create_study(direction="maximize", study_name="xgb-fraud")
    study.optimize(
        lambda trial: objective(trial, X_train, y_train, X_val, y_val),
        n_trials=n_trials,
        show_progress_bar=True,
    )

    print(f"\n  Meilleur AUC-ROC (val) : {study.best_value:.4%}")
    print(f"  Meilleurs paramètres   : {study.best_params}")
    return study.best_params


# ── 4. Entraînement final ───────────────────────────────────────────────────

def train_final(best_params, X_train, y_train, X_val, y_val, X_test, y_test):
    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())

    final_params = {
        **best_params,
        "scale_pos_weight": n_neg / max(n_pos, 1),
        "eval_metric": "aucpr",
        "tree_method": "hist",
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
    }

    print("\nEntraînement du modèle final...")
    model = XGBClassifier(**final_params)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=50)

    # Évaluation sur test
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    auc_roc = roc_auc_score(y_test, y_prob)
    auc_pr = average_precision_score(y_test, y_prob)
    f1 = f1_score(y_test, y_pred)

    print(f"\n{'='*55}")
    print(f"  RÉSULTATS FINAUX — TEST SET")
    print(f"{'='*55}")
    print(f"  AUC-ROC   : {auc_roc:.4%}")
    print(f"  AUC-PR    : {auc_pr:.4%}")
    print(f"  F1-Score  : {f1:.4%}")
    print(f"{'='*55}")
    print(classification_report(y_test, y_pred, target_names=["Légit", "Fraude"]))

    return model, auc_roc


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    X_train, y_train, X_val, y_val, X_test, y_test, preprocessor = prepare_data()

    # Charger ancien score pour comparaison (calculé précédemment sur l'ancien preprocessing)
    old_auc = 0.8836  # AUC-ROC de l'ancien modèle sur test set
    print(f"\nAUC-ROC ancien modèle : {old_auc:.4%}")

    # Tuning
    best_params = tune(X_train, y_train, X_val, y_val, n_trials=50)

    # Entraînement final
    new_model, new_auc = train_final(best_params, X_train, y_train, X_val, y_val, X_test, y_test)

    # Sauvegarde si meilleur
    if new_auc > old_auc:
        # Backup ancien modèle
        backup_path = MODELS_DIR / "xgboost_backup.joblib"
        old_model = joblib.load(MODELS_DIR / "xgboost.joblib")
        joblib.dump(old_model, backup_path)
        print(f"\n  Ancien modèle sauvegardé : {backup_path}")

        joblib.dump(new_model, MODELS_DIR / "xgboost.joblib")
        preprocessor.save()
        print(f"  Nouveau modèle sauvegardé !")
        print(f"\n  Amélioration : {old_auc:.4%} → {new_auc:.4%} (+{(new_auc - old_auc)*100:.2f} pts)")
    else:
        print(f"\n  Pas d'amélioration ({old_auc:.4%} → {new_auc:.4%}). Ancien modèle conservé.")
