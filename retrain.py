import sys
from pathlib import Path
from loguru import logger
from src.data.loader import DataLoader
from src.data.preprocessor import FraudPreprocessor
from src.models.trainer import ModelTrainer
from src.models.evaluator import ModelEvaluator

loader = DataLoader()
df = loader.load()

cols_to_drop = ['organization', 'transaction_id', 'user_id', 'transaction_timestamp']
df_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

X_train, X_val, X_test, y_train, y_val, y_test = loader.get_splits(df_clean)

preprocessor = FraudPreprocessor(smote_sampling_strategy=0.2)
X_train_proc, y_train_proc = preprocessor.fit_transform_train(X_train, y_train)
X_val_proc = preprocessor.transform(X_val)

# 🔥 SAUVEGARDE DU PREPROCESSOR POUR LA PRODUCTION 🔥
preprocessor.save()

evaluator = ModelEvaluator()

logger.info("Entraînement de XGBoost...")
xgb_trainer = ModelTrainer(model_name="xgboost")
xgb_trainer.fit(X_train_proc, y_train_proc, X_val=X_val_proc, y_val=y_val)

y_val_prob_xgb = xgb_trainer.predict_proba(X_val_proc)[:, 1]

# Sauvegarde du Modèle Champion 🏆
xgb_trainer.save()
print("Retraining complete. New joblib files written.")
