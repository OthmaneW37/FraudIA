"""
trainer.py — Entraînement et sauvegarde des modèles de détection de fraude.

Modèles implémentés :
  - LogisticRegression  : baseline linéaire rapide
  - RandomForestClassifier : baseline ensembliste robuste
  - XGBoostClassifier      : modèle principal (state-of-the-art sur données tabulaires)
  - IsolationForest        : détection d'anomalie non supervisée

Pourquoi XGBoost comme modèle principal ?
  → Meilleur score AUC-PR sur datasets tabulaires déséquilibrés (Kaggle benchmarks)
  → Paramètre scale_pos_weight natif pour gérer le déséquilibre de classes
  → Compatible avec SHAP TreeExplainer (explicabilité native)
  → 10-100x plus rapide que Random Forest sur les grands datasets
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np
from loguru import logger
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier


# ── Constantes ──────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
RANDOM_STATE = 42


# ── Configurations par modèle ────────────────────────────────────────────────

DEFAULT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "logistic_regression": {
        "C": 1.0,
        "max_iter": 1000,
        "solver": "lbfgs",
        "class_weight": "balanced",   # Compense le déséquilibre sans SMOTE
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
    },
    "random_forest": {
        "n_estimators": 300,
        "max_depth": 20,
        "min_samples_leaf": 5,
        "class_weight": "balanced_subsample",  # Chaque arbre rééquilibré
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
        "verbose": 1,
    },
    "xgboost": {
        # scale_pos_weight = n_négatifs / n_positifs
        # Sera calculé dynamiquement dans fit() selon le train set
        "n_estimators": 500,
        "max_depth": 7,
        "learning_rate": 0.05,       # Faible LR + plus d'arbres → meilleure généralisation
        "subsample": 0.8,            # Sous-échantillonnage des lignes (évite overfitting)
        "colsample_bytree": 0.8,     # Sous-échantillonnage des features
        "min_child_weight": 10,      # Régularise les nœuds avec peu de samples (fraudes rares)
        "eval_metric": "aucpr",      # Optimiser AUC-PR directement (métrique principale)
        "tree_method": "hist",       # Algorithme histogram : rapide sur grands datasets
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
    },
    "isolation_forest": {
        "n_estimators": 200,
        "contamination": 0.01,       # ~1% de fraudes attendues (ajuster selon EDA)
        "max_features": 1.0,
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
        "verbose": 1,
    },
}


# ── Classe principale ────────────────────────────────────────────────────────

class ModelTrainer:
    """
    Entraîne, sauvegarde et charge les modèles de détection de fraude.

    Usage :
        trainer = ModelTrainer(model_name="xgboost")
        trainer.fit(X_train, y_train, X_val, y_val)
        trainer.save()
    """

    SUPPORTED_MODELS = list(DEFAULT_CONFIGS.keys())

    def __init__(
        self,
        model_name: str = "xgboost",
        config_override: Optional[Dict[str, Any]] = None,
    ) -> None:
        if model_name not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Modèle '{model_name}' inconnu. "
                f"Choisir parmi : {self.SUPPORTED_MODELS}"
            )

        self.model_name = model_name
        self.config = {**DEFAULT_CONFIGS[model_name], **(config_override or {})}
        self._model = None

    # ── Entraînement ─────────────────────────────────────────────────────────

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> "ModelTrainer":
        """
        Entraîne le modèle.

        Pour XGBoost : utilise X_val/y_val pour l'early stopping afin
        d'éviter l'overfitting sans fixer arbitrairement n_estimators.

        Parameters
        ----------
        custom_params : dict, optional
            Paramètres personnalisés (ex: fournis par Optuna) qui écrasent la config par défaut.

        Returns self pour le method chaining.
        """
        logger.info(f"Entraînement : {self.model_name} ...")

        # Appliquer les paramètres custom (Optuna) si fournis
        active_config = {**self.config, **(custom_params or {})}

        if self.model_name == "logistic_regression":
            self._model = LogisticRegression(**active_config)
            self._model.fit(X_train, y_train)

        elif self.model_name == "random_forest":
            self._model = RandomForestClassifier(**active_config)
            self._model.fit(X_train, y_train)

        elif self.model_name == "xgboost":
            # Calcul dynamique de scale_pos_weight si pas déjà dans les params
            if "scale_pos_weight" not in active_config:
                n_neg = int((y_train == 0).sum())
                n_pos = int((y_train == 1).sum())
                active_config["scale_pos_weight"] = n_neg / max(n_pos, 1)
            logger.info(f"  scale_pos_weight = {active_config['scale_pos_weight']:.1f}")

            self._model = XGBClassifier(**active_config)

            # Early stopping si val set disponible
            fit_params: Dict[str, Any] = {}
            if X_val is not None and y_val is not None:
                fit_params["eval_set"] = [(X_val, y_val)]
                fit_params["verbose"] = 50     # Log toutes les 50 itérations

            self._model.fit(X_train, y_train, **fit_params)

        elif self.model_name == "isolation_forest":
            # Non supervisé : pas besoin de y_train
            self._model = IsolationForest(**active_config)
            self._model.fit(X_train)
            logger.info("  Isolation Forest entraîné (non supervisé)")

        logger.success(f"Modèle {self.model_name} entraîné ✓")
        return self


    # ── Prédiction ───────────────────────────────────────────────────────────

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Retourne les labels prédits (0 ou 1)."""
        self._check_fitted()
        if self.model_name == "isolation_forest":
            # IsolationForest : -1 = anomalie → convertir en 1 (fraude)
            raw = self._model.predict(X)
            return (raw == -1).astype(int)
        return self._model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Retourne les probabilités de fraude [p_légit, p_fraude].
        Pour IsolationForest, retourne le score d'anomalie normalisé.
        """
        self._check_fitted()
        if self.model_name == "isolation_forest":
            scores = -self._model.score_samples(X)   # Plus haut = plus anormal
            scores_norm = (scores - scores.min()) / (scores.max() - scores.min() + 1e-9)
            return np.column_stack([1 - scores_norm, scores_norm])
        return self._model.predict_proba(X)

    # ── Sauvegarde / chargement ──────────────────────────────────────────────

    def save(self, path: Optional[str | Path] = None) -> Path:
        """Sauvegarde le modèle entraîné via joblib."""
        self._check_fitted()
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        save_path = Path(path) if path else MODELS_DIR / f"{self.model_name}.joblib"
        joblib.dump(self._model, save_path)
        logger.info(f"Modèle sauvegardé : {save_path}")
        return save_path

    @classmethod
    def load(cls, path: str | Path, model_name: str = "xgboost") -> "ModelTrainer":
        """Charge un modèle sauvegardé."""
        instance = cls(model_name=model_name)
        instance._model = joblib.load(path)
        logger.info(f"Modèle chargé : {path}")
        return instance

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def model(self):
        """Accès direct au modèle sklearn/xgboost sous-jacent."""
        self._check_fitted()
        return self._model

    def _check_fitted(self) -> None:
        if self._model is None:
            raise RuntimeError("Le modèle n'est pas encore entraîné. Appeler fit() d'abord.")
