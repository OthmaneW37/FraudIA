from __future__ import annotations

import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple

from loguru import logger

from src.data.preprocessor import FraudPreprocessor, MODELS_DIR
from src.models.trainer import ModelTrainer
from src.xai.explainer import FraudExplainer
from src.agent.llm_client import FraudAgent

class ModelService:
    """Service gérant la prédiction rapide (sans explication)."""
    
    def __init__(self, preprocessor: FraudPreprocessor, trainer: ModelTrainer):
        self.preprocessor = preprocessor
        self.trainer = trainer
        # Le seuil par défaut peut être fixé à 0.35 d'après notre EDA/Tuning
        self.threshold = 0.35

    @classmethod
    def load_default(cls) -> "ModelService":
        """Charge les modèles depuis la racine du projet."""
        try:
            preprocessor = FraudPreprocessor.load(MODELS_DIR / "preprocessor.joblib")
            trainer = ModelTrainer.load(MODELS_DIR / "xgboost.joblib", model_name="xgboost")
            return cls(preprocessor, trainer)
        except Exception as e:
            logger.error(f"Erreur de chargement des modèles ML: {e}")
            raise

    def _prepare_transaction(self, tx: Dict[str, Any]) -> pd.DataFrame:
        """Injecte les valeurs par défaut pour les features ML non saisies par l'utilisateur."""
        defaults = {
            "fee_amount": 27.76,                    # Médiane saine du dataset
            "user_account_age_days": 1006.0,        # Médiane saine (compte ancien = safe)
            "time_diff": 850943.0,                  # Médiane saine (en secondes, soit ~9.8 jours)
            "day_of_week": 1,
            "is_night": tx.get("hour", 12) < 6 or tx.get("hour", 12) > 22,
            "operating_system": "Windows",
            "browser": "Chrome",
            "payment_method": "credit_card",
            "card_type": "visa"
        }
        for k, v in defaults.items():
            if k not in tx:
                tx[k] = v
        return pd.DataFrame([tx])

    def predict(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Retourne les résultats bruts de prédiction."""
        df_in = self._prepare_transaction(transaction)
        
        # Preprocessing
        X_proc = self.preprocessor.transform(df_in)
        
        # Predict
        proba = self.trainer.predict_proba(X_proc)[0, 1]
        
        return {
            "fraud_probability": float(proba),
            "threshold": self.threshold,
            "model_name": getattr(self.trainer, "model_name", "xgboost")
        }

class FullService:
    """Service gérant la prédiction ET l'explication (SHAP + LLM)."""
    
    def __init__(self, model_service: ModelService):
        self.model_service = model_service
        self.preprocessor = model_service.preprocessor
        self.trainer = model_service.trainer
        
        # Initialisation XAI
        self.explainer = FraudExplainer(
            model=self.trainer.model,
            feature_names=self.preprocessor.feature_names,
            model_type="tree"
        )
        
        # Initialisation LLM
        self.agent = FraudAgent(model="mistral")

    def predict_and_explain(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Effectue la prédiction, extrait les motifs SHAP, puis génère l'explication LLM."""
        df_in = self.model_service._prepare_transaction(transaction)
        X_proc = self.preprocessor.transform(df_in)
        
        # 1. Proba
        proba = self.trainer.predict_proba(X_proc)[0, 1]
        
        # 2. SHAP
        shap_values = self.explainer.explain_instance(X_proc)
        top_features = self.explainer.get_top_features(shap_values, n=5)
        
        # 3. LLM
        explanation = self.agent.explain(
            transaction=transaction,
            fraud_probability=float(proba),
            top_features=top_features,
            threshold=self.model_service.threshold
        )
        
        # Format attendu par la route explain
        return {
            "fraud_probability": float(proba),
            "threshold": self.model_service.threshold,
            "top_features": top_features,
            "explanation": explanation,
            "llm_model": getattr(self.agent, "model", "mistral")
        }
