from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple

from loguru import logger

from src.data.preprocessor import FraudPreprocessor, MODELS_DIR
from src.models.trainer import ModelTrainer
from src.xai.explainer import FraudExplainer
from src.agent.llm_client import FraudAgent

class ModelService:
    """Service gérant la prédiction rapide (sans explication) pour plusieurs modèles."""
    
    def __init__(self, preprocessor: FraudPreprocessor, trainers: Dict[str, ModelTrainer]):
        self.preprocessor = preprocessor
        self.trainers = trainers
        # Seuils calibrés pour Haute Précision (>95% si possible, sinon max possible)
        self.thresholds = {
            "xgboost": 0.80,
            "random_forest": 0.85,
            "logistic_regression": 0.85
        }

    @classmethod
    def load_default(cls) -> "ModelService":
        """Charge les modèles disponibles depuis le dossier models/."""
        try:
            preprocessor = FraudPreprocessor.load(MODELS_DIR / "preprocessor.joblib")
            
            trainers = {}
            for name in ["xgboost", "random_forest", "logistic_regression"]:
                path = MODELS_DIR / f"{name}.joblib"
                if path.exists():
                    trainers[name] = ModelTrainer.load(path, model_name=name)
                    logger.info(f"Modèle {name} chargé.")
                else:
                    logger.warning(f"Modèle {name} manquant à l'emplacement {path}")
            
            if not trainers:
                raise FileNotFoundError("Aucun modèle trouvé dans le dossier models/")
                
            return cls(preprocessor, trainers)
        except Exception as e:
            logger.error(f"Erreur de chargement des modèles ML: {e}")
            raise

    def _prepare_transaction(self, tx: Dict[str, Any]) -> pd.DataFrame:
        """Injecte les valeurs par défaut pour les features ML non saisies par l'utilisateur."""
        defaults = {
            "fee_amount": 27.76, 
            "user_account_age_days": 1006.0,
            "time_diff": 850943.0,
            "day_of_week": 1,
            "is_night": tx.get("hour", 12) < 6 or tx.get("hour", 12) > 22,
            "operating_system": "Windows",
            "browser": "Chrome",
            "payment_method": "credit_card",
            "card_type": "visa",
            "avg_amount_30d": tx.get("transaction_amount", 1000.0) # Défaut si non spécifié
        }
        for k, v in defaults.items():
            if k not in tx:
                tx[k] = v
        return pd.DataFrame([tx])

    def predict(self, transaction: Dict[str, Any], model_name: str = "xgboost") -> Dict[str, Any]:
        """Retourne les résultats bruts de prédiction avec le modèle choisi."""
        df_in = self._prepare_transaction(transaction)
        
        # Preprocessing (inclut maintenant le feature engineering)
        X_proc = self.preprocessor.transform(df_in)
        
        # Sélection du trainer
        trainer = self.trainers.get(model_name, self.trainers.get("xgboost"))
        if not trainer:
            raise ValueError(f"Modèle {model_name} non chargé.")

        # Predict
        proba = trainer.predict_proba(X_proc)[0, 1]
        threshold = self.thresholds.get(model_name, 0.5)
        
        return {
            "fraud_probability": float(proba),
            "threshold": threshold,
            "model_name": model_name
        }

class FullService:
    """Service gérant la prédiction ET l'explication (SHAP + LLM)."""
    
    def __init__(self, model_service: ModelService):
        self.model_service = model_service
        self.preprocessor = model_service.preprocessor
        
        # Cache pour les explainers (un par modèle)
        self.explainers: Dict[str, FraudExplainer] = {}
        for name, trainer in model_service.trainers.items():
            try:
                # Si c'est un modèle linéaire, on utilise background_data (simulé ici par des zéros si non dispos)
                # Ou mieux: on utilise shap.Explainer qui est polymorphique
                self.explainers[name] = FraudExplainer(
                    model=trainer.model,
                    feature_names=self.preprocessor.feature_names,
                    model_type="tree" if name != "logistic_regression" else "linear",
                    background_data=np.zeros((10, len(self.preprocessor.feature_names))) if name == "logistic_regression" else None
                )
            except Exception as e:
                logger.error(f"Erreur initialisation explainer pour {name}: {e}")
        
        # Initialisation LLM — modèle configurable via LLM_MODEL dans .env
        import os
        llm_model = os.getenv("LLM_MODEL", "mistral")
        self.agent = FraudAgent(model=llm_model)

    def predict_and_shap(self, transaction: Dict[str, Any], model_name: str = "xgboost") -> Dict[str, Any]:
        """Effectue la prédiction + SHAP (rapide, ~2-3s). Pas de LLM."""
        df_in = self.model_service._prepare_transaction(transaction)
        X_proc = self.preprocessor.transform(df_in)
        
        trainer = self.model_service.trainers.get(model_name, self.model_service.trainers.get("xgboost"))
        explainer = self.explainers.get(model_name, self.explainers.get("xgboost"))
        threshold = self.model_service.thresholds.get(model_name, 0.5)
        
        proba = trainer.predict_proba(X_proc)[0, 1]
        shap_values = explainer.explain_instance(X_proc)
        top_features = explainer.get_top_features(shap_values, n=5)
        
        return {
            "fraud_probability": float(proba),
            "threshold": threshold,
            "top_features": top_features,
            "llm_model": getattr(self.agent, "model", "mistral")
        }

    def generate_explanation(self, transaction: Dict[str, Any], fraud_probability: float, top_features: list, threshold: float = 0.5) -> str:
        """Génère uniquement l'explication LLM (lent, ~30-60s)."""
        return self.agent.explain(
            transaction=transaction,
            fraud_probability=fraud_probability,
            top_features=top_features,
            threshold=threshold
        )

    def predict_and_explain(self, transaction: Dict[str, Any], model_name: str = "xgboost") -> Dict[str, Any]:
        """Effectue la prédiction, extrait les motifs SHAP, puis génère l'explication LLM."""
        df_in = self.model_service._prepare_transaction(transaction)
        X_proc = self.preprocessor.transform(df_in)
        
        # 1. Sélection can modèle et explainer
        trainer = self.model_service.trainers.get(model_name, self.model_service.trainers.get("xgboost"))
        explainer = self.explainers.get(model_name, self.explainers.get("xgboost"))
        threshold = self.model_service.thresholds.get(model_name, 0.5)
        
        # 2. Proba
        proba = trainer.predict_proba(X_proc)[0, 1]
        
        # 3. SHAP
        shap_values = explainer.explain_instance(X_proc)
        top_features = explainer.get_top_features(shap_values, n=5)
        
        # 4. LLM
        explanation = self.agent.explain(
            transaction=transaction,
            fraud_probability=float(proba),
            top_features=top_features,
            threshold=threshold
        )
        
        return {
            "fraud_probability": float(proba),
            "threshold": threshold,
            "top_features": top_features,
            "explanation": explanation,
            "llm_model": getattr(self.agent, "model", "mistral")
        }
