from __future__ import annotations

import json
from typing import Any, Dict

import numpy as np
import pandas as pd
from loguru import logger

from src.agent.llm_client import FraudAgent
from src.data.preprocessor import FraudPreprocessor, MODELS_DIR
from src.models.trainer import ModelTrainer
from src.xai.explainer import FraudExplainer

THRESHOLDS_PATH = MODELS_DIR / "thresholds.json"


class ModelService:
    """Service gerant la prediction rapide (sans explication) pour plusieurs modeles."""

    def __init__(self, preprocessor: FraudPreprocessor, trainers: Dict[str, ModelTrainer]):
        self.preprocessor = preprocessor
        self.trainers = trainers
        self.thresholds = self._load_thresholds()

    @staticmethod
    def _load_thresholds() -> Dict[str, float]:
        defaults = {
            "xgboost": 0.60,
            "random_forest": 0.50,
            "logistic_regression": 0.50,
        }

        if not THRESHOLDS_PATH.exists():
            logger.warning(
                f"Fichier de seuils absent ({THRESHOLDS_PATH}). Utilisation des seuils calibres par defaut."
            )
            return defaults

        try:
            with THRESHOLDS_PATH.open("r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            thresholds = {**defaults, **{name: float(value) for name, value in loaded.items()}}
            logger.info(f"Seuils charges depuis {THRESHOLDS_PATH}: {thresholds}")
            return thresholds
        except Exception as exc:
            logger.warning(f"Impossible de charger les seuils calibres: {exc}")
            return defaults

    @classmethod
    def load_default(cls) -> "ModelService":
        """Charge les modeles disponibles depuis le dossier models/."""
        try:
            preprocessor = FraudPreprocessor.load(MODELS_DIR / "preprocessor.joblib")

            trainers: Dict[str, ModelTrainer] = {}
            for name in ["xgboost", "random_forest", "logistic_regression"]:
                path = MODELS_DIR / f"{name}.joblib"
                if path.exists():
                    trainers[name] = ModelTrainer.load(path, model_name=name)
                    logger.info(f"Modele {name} charge.")
                else:
                    logger.warning(f"Modele {name} manquant a l'emplacement {path}")

            if not trainers:
                raise FileNotFoundError("Aucun modele trouve dans le dossier models/")

            return cls(preprocessor, trainers)
        except Exception as exc:
            logger.error(f"Erreur de chargement des modeles ML: {exc}")
            raise

    def _prepare_transaction(self, tx: Dict[str, Any]) -> pd.DataFrame:
        """Injecte les valeurs par defaut pour les features ML non saisies par l'utilisateur."""
        defaults = {
            "fee_amount": 27.76,
            "user_account_age_days": 1006.0,
            "day_of_week": 1,
            "operating_system": "Windows",
            "browser": "Chrome",
            "payment_method": "card" if tx.get("payment_method") in (None, "", "credit_card") else tx.get("payment_method"),
            "card_type": "credit" if tx.get("card_type") in (None, "", "visa") else tx.get("card_type"),
            "avg_amount_30d": tx.get("avg_amount_30d", tx.get("transaction_amount", 1000.0)),
            "time_since_last_txn": tx.get("time_since_last_txn", 480.0),
            "txn_count_24h": tx.get("txn_count_24h", 2.0),
            "txn_sum_24h": tx.get("txn_sum_24h", tx.get("transaction_amount", 1000.0) * 2),
            "is_new_city": tx.get("is_new_city", 0),
            "country": tx.get("country", "Bangladesh"),
            "currency": tx.get("currency", "BDT"),
        }
        prepared = {**defaults, **tx}
        return pd.DataFrame([prepared])

    def predict(self, transaction: Dict[str, Any], model_name: str = "xgboost") -> Dict[str, Any]:
        """Retourne les resultats bruts de prediction avec le modele choisi."""
        df_in = self._prepare_transaction(transaction)
        X_proc = self.preprocessor.transform(df_in)

        trainer = self.trainers.get(model_name, self.trainers.get("xgboost"))
        if not trainer:
            raise ValueError(f"Modele {model_name} non charge.")

        proba = trainer.predict_proba(X_proc)[0, 1]
        threshold = self.thresholds.get(model_name, 0.5)

        return {
            "fraud_probability": float(proba),
            "threshold": threshold,
            "model_name": model_name,
        }


class FullService:
    """Service gerant la prediction ET l'explication (SHAP + LLM)."""

    def __init__(self, model_service: ModelService):
        self.model_service = model_service
        self.preprocessor = model_service.preprocessor

        self.explainers: Dict[str, FraudExplainer] = {}
        for name, trainer in model_service.trainers.items():
            try:
                self.explainers[name] = FraudExplainer(
                    model=trainer.model,
                    feature_names=self.preprocessor.feature_names,
                    model_type="tree" if name != "logistic_regression" else "linear",
                    background_data=np.zeros((10, len(self.preprocessor.feature_names)))
                    if name == "logistic_regression"
                    else None,
                )
            except Exception as exc:
                logger.error(f"Erreur initialisation explainer pour {name}: {exc}")

        self.agent = FraudAgent()

    def predict_and_shap(self, transaction: Dict[str, Any], model_name: str = "xgboost") -> Dict[str, Any]:
        """Effectue la prediction + SHAP. Pas de LLM."""
        df_in = self.model_service._prepare_transaction(transaction)
        X_proc = self.preprocessor.transform(df_in)

        trainer = self.model_service.trainers.get(model_name, self.model_service.trainers.get("xgboost"))
        explainer = self.explainers.get(model_name, self.explainers.get("xgboost"))
        threshold = self.model_service.thresholds.get(model_name, 0.5)

        proba = trainer.predict_proba(X_proc)[0, 1]
        shap_values = explainer.explain_instance(X_proc)
        top_features = explainer.get_top_features(shap_values, n=10)

        return {
            "fraud_probability": float(proba),
            "threshold": threshold,
            "top_features": top_features,
            "llm_model": getattr(self.agent, "model", "sonar"),
        }

    def generate_explanation(
        self,
        transaction: Dict[str, Any],
        fraud_probability: float,
        top_features: list,
        threshold: float = 0.5,
        llm_provider: str = "local",
    ) -> str:
        """Genere uniquement l'explication LLM."""
        return self.agent.explain(
            transaction=transaction,
            fraud_probability=fraud_probability,
            top_features=top_features,
            threshold=threshold,
            llm_provider=llm_provider,
        )

    def predict_and_explain(self, transaction: Dict[str, Any], model_name: str = "xgboost") -> Dict[str, Any]:
        """Effectue la prediction, extrait SHAP puis genere l'explication LLM."""
        df_in = self.model_service._prepare_transaction(transaction)
        X_proc = self.preprocessor.transform(df_in)

        trainer = self.model_service.trainers.get(model_name, self.model_service.trainers.get("xgboost"))
        explainer = self.explainers.get(model_name, self.explainers.get("xgboost"))
        threshold = self.model_service.thresholds.get(model_name, 0.5)

        proba = trainer.predict_proba(X_proc)[0, 1]
        shap_values = explainer.explain_instance(X_proc)
        top_features = explainer.get_top_features(shap_values, n=10)

        explanation = self.agent.explain(
            transaction=transaction,
            fraud_probability=float(proba),
            top_features=top_features,
            threshold=threshold,
        )

        return {
            "fraud_probability": float(proba),
            "threshold": threshold,
            "top_features": top_features,
            "explanation": explanation,
            "llm_model": getattr(self.agent, "model", "sonar"),
        }
