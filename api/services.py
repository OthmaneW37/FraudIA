from __future__ import annotations

import joblib
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
        self._ensemble = None  # VotingClassifier sklearn, chargé par load_default()
        self.thresholds = self._load_thresholds()

    @staticmethod
    def _load_thresholds() -> Dict[str, float]:
        defaults = {
            "xgboost": 0.60,
            "random_forest": 0.50,
            "logistic_regression": 0.50,
            "ensemble": 0.50,
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
        """Charge les modèles disponibles depuis le dossier models/."""
        try:
            preprocessor = FraudPreprocessor.load(MODELS_DIR / "preprocessor.joblib")

            trainers: Dict[str, ModelTrainer] = {}
            for name in ["xgboost", "random_forest", "logistic_regression"]:
                path = MODELS_DIR / f"{name}.joblib"
                if path.exists():
                    trainers[name] = ModelTrainer.load(path, model_name=name)
                    logger.info(f"Modèle {name} chargé.")
                else:
                    logger.warning(f"Modèle {name} manquant à l'emplacement {path}")

            # Charger l'ensemble si disponible
            ensemble_path = MODELS_DIR / "ensemble.joblib"
            if ensemble_path.exists():
                ensemble = joblib.load(ensemble_path)
                # L'ensemble est un VotingClassifier sklearn, pas un ModelTrainer
                instance = cls(preprocessor, trainers)
                instance._ensemble = ensemble
                logger.info("Ensemble soft-voting chargé.")
            else:
                instance = cls(preprocessor, trainers)
                instance._ensemble = None

            if not trainers:
                raise FileNotFoundError("Aucun modèle trouvé dans le dossier models/")

            return instance
        except Exception as exc:
            logger.error(f"Erreur de chargement des modèles ML: {exc}")
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
            "is_night": 1 if tx.get("hour", 12) < 6 or tx.get("hour", 12) >= 22 else 0,
            "time_diff": tx.get("time_since_last_txn", 480.0),
            "country": tx.get("country", "Bangladesh"),
            "currency": tx.get("currency", "BDT"),
        }
        prepared = {**defaults, **tx}
        return pd.DataFrame([prepared])

    @staticmethod
    def _calibrate_probability(proba: float, threshold: float) -> float:
        """
        Normalise linéairement la probabilité autour du seuil de décision.
        - proba = 0        → score = 0
        - proba = threshold → score = 0.5
        - proba = 1        → score = 1
        """
        if proba < threshold:
            return 0.5 * (proba / max(threshold, 1e-9))
        else:
            normalized = (proba - threshold) / max(1.0 - threshold, 1e-9)
            return 0.5 + 0.5 * normalized

    def predict(self, transaction: Dict[str, Any], model_name: str = "xgboost") -> Dict[str, Any]:
        """Retourne les résultats bruts de prédiction avec le modèle choisi."""
        df_in = self._prepare_transaction(transaction)
        X_proc = self.preprocessor.transform(df_in)

        trainer = self.trainers.get(model_name, self.trainers.get("xgboost"))
        if not trainer:
            raise ValueError(f"Modèle {model_name} non chargé.")

        # Ajuster le nombre de features si le modèle a été entraîné avec une version différente
        X_proc = self._align_features(X_proc, trainer)

        # Utiliser l'ensemble si disponible et demandé
        if model_name == "ensemble" and self._ensemble is not None:
            if hasattr(self._ensemble, 'n_features_in_'):
                X_proc = self._align_features_ensemble(X_proc)
            proba = self._ensemble.predict_proba(X_proc)[0, 1]
        else:
            proba = trainer.predict_proba(X_proc)[0, 1]

        threshold = self.thresholds.get(model_name, 0.5)
        calibrated_proba = self._calibrate_probability(float(proba), threshold)

        return {
            "fraud_probability": calibrated_proba,
            "threshold": 0.5,
            "model_name": model_name,
        }

    @staticmethod
    def _align_features(X: np.ndarray, trainer: ModelTrainer) -> np.ndarray:
        """Padde ou tronque X pour correspondre au nombre de features attendu par le modèle."""
        model_n = X.shape[1]
        if hasattr(trainer.model, 'n_features_in_'):
            model_n = trainer.model.n_features_in_
        elif hasattr(trainer.model, 'coef_'):
            model_n = trainer.model.coef_.shape[1]
        if X.shape[1] < model_n:
            padding = np.zeros((X.shape[0], model_n - X.shape[1]))
            X = np.hstack([X, padding])
        elif X.shape[1] > model_n:
            X = X[:, :model_n]
        return X

    def _align_features_ensemble(self, X: np.ndarray) -> np.ndarray:
        """Padde ou tronque pour l'ensemble VotingClassifier."""
        if hasattr(self._ensemble, 'n_features_in_'):
            model_n = self._ensemble.n_features_in_
            if X.shape[1] < model_n:
                padding = np.zeros((X.shape[0], model_n - X.shape[1]))
                X = np.hstack([X, padding])
            elif X.shape[1] > model_n:
                X = X[:, :model_n]
        return X


class FullService:
    """Service gerant la prediction ET l'explication (SHAP + LLM)."""

    def __init__(self, model_service: ModelService):
        self.model_service = model_service
        self.preprocessor = model_service.preprocessor

        self.explainers: Dict[str, FraudExplainer] = {}
        for name, trainer in model_service.trainers.items():
            try:
                pp_features = self.preprocessor.feature_names
                pp_n = len(pp_features)

                # Détecter le nombre de features attendu par le modèle
                model_n = pp_n
                if hasattr(trainer.model, 'n_features_in_'):
                    model_n = trainer.model.n_features_in_
                elif hasattr(trainer.model, 'coef_'):
                    model_n = trainer.model.coef_.shape[1]

                if model_n != pp_n:
                    logger.warning(
                        f"Modèle {name} : {model_n} features attendues, "
                        f"preprocessor en produit {pp_n}. Paddées avec zéros."
                    )
                    # Pad feature names pour correspondre au nombre de features du modèle
                    while len(pp_features) < model_n:
                        pp_features.append(f"extra_{len(pp_features)}")

                self.explainers[name] = FraudExplainer(
                    model=trainer.model,
                    feature_names=pp_features[:model_n],
                    model_type="tree" if name != "logistic_regression" else "linear",
                    background_data=np.zeros((10, model_n))
                    if name == "logistic_regression"
                    else None,
                )
            except Exception as exc:
                logger.error(f"Erreur initialisation explainer pour {name}: {exc}")

        self.agent = FraudAgent()

    def predict_and_shap(self, transaction: Dict[str, Any], model_name: str = "xgboost") -> Dict[str, Any]:
        """Effectue la prédiction + SHAP. Pas de LLM."""
        df_in = self.model_service._prepare_transaction(transaction)
        X_proc = self.preprocessor.transform(df_in)

        # Utiliser l'ensemble pour la proba, XGBoost pour SHAP
        if model_name == "ensemble" and self.model_service._ensemble is not None:
            X_proc = self.model_service._align_features_ensemble(X_proc)
            proba = self.model_service._ensemble.predict_proba(X_proc)[0, 1]
            explainer = self.explainers.get("xgboost", next(iter(self.explainers.values())))
        else:
            trainer = self.model_service.trainers.get(model_name, self.model_service.trainers.get("xgboost"))
            explainer = self.explainers.get(model_name, self.explainers.get("xgboost"))
            X_proc = self.model_service._align_features(X_proc, trainer)
            proba = trainer.predict_proba(X_proc)[0, 1]

        threshold = self.model_service.thresholds.get(model_name, 0.5)

        shap_values = explainer.explain_instance(X_proc)
        top_features = explainer.get_top_features(shap_values, n=10)

        calibrated_proba = self.model_service._calibrate_probability(float(proba), threshold)

        return {
            "fraud_probability": calibrated_proba,
            "threshold": 0.5,
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
        """Effectue la prédiction, extrait SHAP puis génère l'explication LLM."""
        df_in = self.model_service._prepare_transaction(transaction)
        X_proc = self.preprocessor.transform(df_in)

        # Utiliser l'ensemble pour la proba, XGBoost pour SHAP
        if model_name == "ensemble" and self.model_service._ensemble is not None:
            X_proc = self.model_service._align_features_ensemble(X_proc)
            proba = self.model_service._ensemble.predict_proba(X_proc)[0, 1]
            explainer = self.explainers.get("xgboost", next(iter(self.explainers.values())))
        else:
            trainer = self.model_service.trainers.get(model_name, self.model_service.trainers.get("xgboost"))
            explainer = self.explainers.get(model_name, self.explainers.get("xgboost"))
            X_proc = self.model_service._align_features(X_proc, trainer)
            proba = trainer.predict_proba(X_proc)[0, 1]

        threshold = self.model_service.thresholds.get(model_name, 0.5)

        shap_values = explainer.explain_instance(X_proc)
        top_features = explainer.get_top_features(shap_values, n=10)

        calibrated_proba = self.model_service._calibrate_probability(float(proba), threshold)

        explanation = self.agent.explain(
            transaction=transaction,
            fraud_probability=calibrated_proba,
            top_features=top_features,
            threshold=0.5,
        )

        return {
            "fraud_probability": calibrated_proba,
            "threshold": 0.5,
            "top_features": top_features,
            "explanation": explanation,
            "llm_model": getattr(self.agent, "model", "sonar"),
        }
