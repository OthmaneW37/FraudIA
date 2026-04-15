import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve
from pathlib import Path
import sys

# Ajouter le projet au path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.data.loader import DataLoader
from src.data.preprocessor import FraudPreprocessor

def check_perf():
    models_dir = Path("models")
    loader = DataLoader()
    df = loader.load()
    cols_to_drop = ['organization', 'transaction_id', 'user_id', 'transaction_timestamp']
    df_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    _, X_val, _, _, y_val, _ = loader.get_splits(df_clean)

    preprocessor = FraudPreprocessor.load(models_dir / "preprocessor.joblib")
    X_val_proc = preprocessor.transform(X_val)

    xgb = joblib.load(models_dir / "xgboost.joblib")
    y_val_prob = xgb.predict_proba(X_val_proc)[:, 1]

    precisions, recalls, thresholds = precision_recall_curve(y_val, y_val_prob)
    
    # Check max precision where recall > 0.01
    mask = recalls > 0.01
    valid_precisions = precisions[:-1][mask[:-1]]
    valid_thresholds = thresholds[mask[:-1]]
    
    if len(valid_precisions) > 0:
        max_p = np.max(valid_precisions)
        best_t = valid_thresholds[np.argmax(valid_precisions)]
        print(f"Max Precision (with >1% recall): {max_p:.4f} at threshold {best_t:.4f}")
    else:
        print("No threshold found with >1% recall")

    # Find threshold for 95% precision
    mask_95 = precisions >= 0.95
    if mask_95.any():
        idx = np.where(mask_95)[0][0]
        if idx < len(thresholds):
            print(f"95% Precision threshold: {thresholds[idx]:.4f} (Recall: {recalls[idx]:.4f})")
        else:
            print("95% Precision only at recall 0")
    else:
        print("95% Precision never reached")

if __name__ == "__main__":
    check_perf()
