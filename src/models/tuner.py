"""
tuner.py — Hyperparameter Tuning avec Optuna pour XGBoost.

Optuna est une bibliothèque d'optimisation bayésienne d'hyperparamètres.
Au lieu de tester toutes les combinaisons (GridSearch), Optuna apprend de
chaque essai pour proposer intelligemment le suivant.

Métriques d'optimisation : F1-Score (seuil 0.5) — robuste sur données déséquilibrées.

Usage :
    from src.models.tuner import XGBoostTuner
    tuner = XGBoostTuner()
    best_params, best_score = tuner.optimize(X_train, y_train, X_val, y_val, n_trials=50)
    model = tuner.get_best_model()
    model.save()  # → models/xgboost.joblib
"""

from __future__ import annotations

from typing import Dict, Any, Tuple

import numpy as np
from loguru import logger
from sklearn.metrics import f1_score, average_precision_score

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    logger.warning("Optuna non installé — `pip install optuna` pour activer le tuning AutoML")

from src.models.trainer import ModelTrainer


# ── Constantes ──────────────────────────────────────────────────────────────

SEARCH_SPACE = {
    "n_estimators":      (200,  1500),
    "max_depth":         (3,    10),
    "learning_rate":     (0.01, 0.3),
    "subsample":         (0.6,  1.0),
    "colsample_bytree":  (0.5,  1.0),
    "gamma":             (0.0,  5.0),
    "min_child_weight":  (1,    10),
    "reg_alpha":         (0.0,  1.0),    # L1 regularization
    "reg_lambda":        (1.0,  10.0),   # L2 regularization
}


# ── Classe principale ────────────────────────────────────────────────────────

class XGBoostTuner:
    """
    Optimise automatiquement les hyperparamètres XGBoost via Optuna.

    Chaque "trial" = une combinaison d'hyperparamètres testée.
    Optuna utilise l'algorithme TPE (Tree-structured Parzen Estimator)
    pour guider intelligemment la recherche vers les meilleures zones.
    """

    def __init__(self) -> None:
        self._best_params: Dict[str, Any] | None = None
        self._best_score: float = 0.0
        self._study = None
        self._trainer: ModelTrainer | None = None

    def optimize(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        n_trials: int = 50,
    ) -> Tuple[Dict[str, Any], float]:
        """
        Lance l'optimisation Optuna.

        Parameters
        ----------
        n_trials : int
            Nombre d'essais = nb de modèles testés. Plus c'est élevé, mieux c'est
            (mais plus ça prend du temps). Recommandé : 50 pour un bon équilibre.

        Returns
        -------
        (best_params, best_auc_pr) : le meilleur set d'hyperparamètres + score AUC-PR
        """
        if not OPTUNA_AVAILABLE:
            raise ImportError("Veuillez installer Optuna : pip install optuna")

        logger.info(f"Démarrage AutoML Optuna — {n_trials} essais...")

        # Calcul de scale_pos_weight pour compenser le déséquilibre
        n_neg = (y_train == 0).sum()
        n_pos = (y_train == 1).sum()
        scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0
        logger.info(f"scale_pos_weight = {scale_pos_weight:.1f} (ratio non-fraude / fraude)")

        def objective(trial: optuna.Trial) -> float:
            params = {
                "n_estimators":     trial.suggest_int("n_estimators", *SEARCH_SPACE["n_estimators"]),
                "max_depth":        trial.suggest_int("max_depth", *SEARCH_SPACE["max_depth"]),
                "learning_rate":    trial.suggest_float("learning_rate", *SEARCH_SPACE["learning_rate"], log=True),
                "subsample":        trial.suggest_float("subsample", *SEARCH_SPACE["subsample"]),
                "colsample_bytree": trial.suggest_float("colsample_bytree", *SEARCH_SPACE["colsample_bytree"]),
                "gamma":            trial.suggest_float("gamma", *SEARCH_SPACE["gamma"]),
                "min_child_weight": trial.suggest_int("min_child_weight", *SEARCH_SPACE["min_child_weight"]),
                "reg_alpha":        trial.suggest_float("reg_alpha", *SEARCH_SPACE["reg_alpha"]),
                "reg_lambda":       trial.suggest_float("reg_lambda", *SEARCH_SPACE["reg_lambda"]),
                "scale_pos_weight": scale_pos_weight,
                "use_label_encoder": False,
                "eval_metric": "logloss",
                "random_state": 42,
                "n_jobs": -1,
                "tree_method": "hist",  # Rapide sur CPU
            }

            # Entraîner un XGBoost avec ces paramètres
            trainer = ModelTrainer(model_name="xgboost")
            trainer.fit(X_train, y_train,
                        X_val=X_val, y_val=y_val,
                        custom_params=params)

            # Score : AUC-PR (Average Precision) = meilleure métrique pour données déséquilibrées
            y_proba = trainer.predict_proba(X_val)[:, 1]
            auc_pr = average_precision_score(y_val, y_proba)

            # Aussi calculer F1 au seuil 0.5 pour info
            y_pred = (y_proba >= 0.5).astype(int)
            f1 = f1_score(y_val, y_pred, average="macro", zero_division=0)

            trial.set_user_attr("f1_macro", f1)
            return auc_pr  # Optuna MAXIMISE cette valeur

        # Lancer l'optimisation
        self._study = optuna.create_study(
            direction="maximize",
            study_name="xgboost_fraud_detection",
            sampler=optuna.samplers.TPESampler(seed=42),
        )

        self._study.optimize(
            objective,
            n_trials=n_trials,
            show_progress_bar=True,
            n_jobs=1,  # Séquentiel pour éviter les conflits mémoire
        )

        self._best_params = self._study.best_params
        self._best_score = self._study.best_value

        # Ajouter les paramètres fixes
        self._best_params.update({
            "scale_pos_weight": scale_pos_weight,
            "use_label_encoder": False,
            "eval_metric": "logloss",
            "random_state": 42,
            "n_jobs": -1,
            "tree_method": "hist",
        })

        logger.success(
            f"Optuna terminé ✓ | Meilleur AUC-PR: {self._best_score:.4f} | "
            f"Params: n_estimators={self._best_params['n_estimators']}, "
            f"lr={self._best_params['learning_rate']:.4f}, "
            f"max_depth={self._best_params['max_depth']}"
        )

        return self._best_params, self._best_score

    def train_final_model(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> ModelTrainer:
        """
        Entraîne le modèle final avec les meilleurs paramètres trouvés.
        Doit être appelé après optimize().
        """
        if self._best_params is None:
            raise RuntimeError("Appeler optimize() avant train_final_model().")

        logger.info("Entraînement du modèle final avec les meilleurs paramètres...")
        self._trainer = ModelTrainer(model_name="xgboost")
        self._trainer.fit(
            X_train, y_train,
            X_val=X_val, y_val=y_val,
            custom_params=self._best_params,
        )
        logger.success("Modèle final entraîné ✓")
        return self._trainer

    def get_best_model(self) -> ModelTrainer:
        """Retourne le modèle final (après train_final_model())."""
        if self._trainer is None:
            raise RuntimeError("Appeler train_final_model() d'abord.")
        return self._trainer
