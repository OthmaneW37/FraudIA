import sys
from pathlib import Path
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import precision_recall_curve

# Ajouter le projet au path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.data.loader import DataLoader
from src.data.preprocessor import FraudPreprocessor
from src.models.trainer import ModelTrainer
from src.models.evaluator import ModelEvaluator

def train_and_optimize():
    loader = DataLoader()
    df = loader.load()

    # Nettoyage minimal
    cols_to_drop = ['organization', 'transaction_id', 'user_id', 'transaction_timestamp']
    df_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    # Splitting
    X_train, X_val, X_test, y_train, y_val, y_test = loader.get_splits(df_clean)

    # Preprocessing
    preprocessor = FraudPreprocessor(smote_sampling_strategy=0.2)
    X_train_proc, y_train_proc = preprocessor.fit_transform_train(X_train, y_train)
    X_val_proc = preprocessor.transform(X_val)
    
    # Sauvegarde preprocessor
    preprocessor.save()

    models_to_train = ["xgboost", "random_forest", "logistic_regression"]
    results = {}

    for name in models_to_train:
        logger.info(f"--- Entraînement de {name} ---")
        trainer = ModelTrainer(model_name=name)
        
        if name == "xgboost":
            trainer.fit(X_train_proc, y_train_proc, X_val=X_val_proc, y_val=y_val)
        else:
            trainer.fit(X_train_proc, y_train_proc)
        
        # Trouver le seuil pour Precision > 95%
        y_val_prob = trainer.predict_proba(X_val_proc)[:, 1]
        precisions, recalls, thresholds = precision_recall_curve(y_val, y_val_prob)
        
        # On cherche le premier seuil où precision >= 0.95
        # Note: precision_recall_curve retourne precision/recall avec un element de plus à la fin
        mask = precisions >= 0.95
        if mask.any():
            # On prend le plus petit seuil qui garantit 95% de précision pour garder le max de recall
            idx = np.where(mask)[0][0]
            # Si idx est le dernier index (qui correspond à precision=1.0, recall=0.0), 
            # on essaie de reculer un peu si possible
            if idx >= len(thresholds):
                idx = len(thresholds) - 1
            
            target_threshold = float(thresholds[idx])
            current_precision = precisions[idx]
            current_recall = recalls[idx]
        else:
            # Si impossible, on prend le max de précision trouvé
            idx = np.argmax(precisions)
            target_threshold = float(thresholds[min(idx, len(thresholds)-1)])
            current_precision = precisions[idx]
            current_recall = recalls[idx]
            logger.warning(f"Impossible d'atteindre 95% de précision pour {name}. Max: {current_precision:.2%}")

        logger.info(f"Modèle {name} : Seuil optimal pour Précision >95% : {target_threshold:.4f}")
        logger.info(f"Performance à ce seuil : Précision={current_precision:.2%}, Rappel={current_recall:.2%}")

        # Sauvegarde
        trainer.save()
        results[name] = {"threshold": target_threshold, "precision": current_precision, "recall": current_recall}

    logger.success("Tous les modèles sont entraînés et sauvegardés !")
    return results

if __name__ == "__main__":
    train_and_optimize()
