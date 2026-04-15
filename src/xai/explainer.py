"""
explainer.py — Wrapper SHAP pour l'explicabilité des prédictions.

Pourquoi SHAP ?
  → Basé sur la théorie des jeux (valeurs de Shapley) : chaque feature reçoit
    une contribution mathématiquement juste à la prédiction finale.
  → TreeExplainer est spécialement optimisé pour XGBoost/RF : beaucoup plus
    rapide qu'un KernelExplainer générique.
  → Output : valeurs SHAP par feature = input directement exploitable par le LLM.

Flux :
  transaction → modèle → prédiction (probabilité)
                       ↘→ SHAP values → top features + sens (+ ou -) → LLM
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from loguru import logger


# ── Constantes ──────────────────────────────────────────────────────────────

FIGURES_DIR = Path("notebooks/figures")


# ── Classe principale ────────────────────────────────────────────────────────

class FraudExplainer:
    """
    Wrapper SHAP pour expliquer les prédictions de fraude.

    Supporte :
    - TreeExplainer  : XGBoost, Random Forest (rapide, exact)
    - LinearExplainer: Régression Logistique

    Usage :
        explainer = FraudExplainer(model, feature_names)
        shap_vals = explainer.explain_instance(x_single)
        top_feats = explainer.get_top_features(shap_vals, n=5)
    """

    def __init__(
        self,
        model,
        feature_names: List[str],
        model_type: str = "tree",   # "tree" | "linear"
        background_data: Optional[np.ndarray] = None,
    ) -> None:
        """
        Parameters
        ----------
        model        : modèle sklearn/xgboost entraîné
        feature_names: noms des features (après preprocessing)
        model_type   : "tree" pour XGBoost/RF, "linear" pour LR
        background_data : échantillon de données de référence (pour KernelExplainer)
        """
        self.model = model
        self.feature_names = feature_names
        self.model_type = model_type
        self._explainer = None

        self._build_explainer(background_data)

    # ── Construction ─────────────────────────────────────────────────────────

    def _build_explainer(self, background_data: Optional[np.ndarray]) -> None:
        """
        Instancie le bon type d'explainer SHAP selon le modèle.

        TreeExplainer : ne nécessite pas de background_data (calcul exact).
        LinearExplainer : nécessite des données de background pour les interactions.
        """
        logger.info(f"Initialisation SHAP {self.model_type.capitalize()}Explainer...")

        if self.model_type == "tree":
            # TreeExplainer est ~1000x plus rapide que KernelExplainer
            self._explainer = shap.TreeExplainer(
                self.model,
                feature_perturbation="tree_path_dependent",
            )
        elif self.model_type == "linear":
            if background_data is None:
                raise ValueError("LinearExplainer requiert un background_data.")
            self._explainer = shap.LinearExplainer(self.model, background_data)
        else:
            raise ValueError(f"model_type '{self.model_type}' inconnu. Choisir 'tree' ou 'linear'.")

        logger.success(f"SHAP Explainer prêt ✓")

    # ── Explication d'une instance unique ────────────────────────────────────

    def explain_instance(
        self,
        x: np.ndarray,
    ) -> Dict[str, float]:
        """
        Calcule les valeurs SHAP pour UNE transaction.

        Parameters
        ----------
        x : np.ndarray, shape (1, n_features) ou (n_features,)

        Returns
        -------
        dict {feature_name: shap_value}
          → valeur positive = pousse vers fraude
          → valeur négative = pousse vers légit.
        """
        if x.ndim == 1:
            x = x.reshape(1, -1)

        shap_values = self._explainer.shap_values(x)

        # Pour les classificateurs binaires, shap_values peut être une liste [class0, class1]
        if isinstance(shap_values, list):
            # RandomForest scikit-learn avec TreeExplainer retourne souvent [prob_class0, prob_class1]
            shap_values = shap_values[1]

        # S'assurer qu'on a un tableau 2D (n_samples, n_features)
        if hasattr(shap_values, "ndim") and shap_values.ndim == 3:
            # Cas rare où on a (samples, features, classes)
            shap_values = shap_values[:, :, 1]

        shap_array = shap_values[0]  # Première (seule) ligne
        
        # Si shap_array est encore un tableau/liste (cas multi-output persistant), on prend le dernier niveau
        if hasattr(shap_array, "__len__") and not isinstance(shap_array, (str, bytes)):
            if len(shap_array.shape) > 0 and shap_array.shape[-1] == 2:
                 # C'est probablement encore [contrib_class0, contrib_class1]
                 shap_array = shap_array[:, 1] if len(shap_array.shape) > 1 else shap_array[1]

        return dict(zip(self.feature_names, np.array(shap_array).flatten().tolist()))

    # ── Top features ─────────────────────────────────────────────────────────

    def get_top_features(
        self,
        shap_dict: Dict[str, float],
        n: int = 6,
    ) -> List[Dict]:
        """
        Retourne les N features les plus influentes pour une transaction.

        Format de sortie conçu pour être consommé directement par le LLM.

        Parameters
        ----------
        shap_dict : dict retourné par explain_instance()
        n         : nombre de features à retourner

        Returns
        -------
        Liste de dicts triée par |impact| décroissant :
          [{"feature": str, "shap_value": float, "direction": "↑fraude" | "↓fraude"}, ...]
        """
        sorted_features = sorted(
            shap_dict.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )[:n]

        return [
            {
                "feature": feat,
                "shap_value": round(val, 4),
                "direction": "↑fraude" if val > 0 else "↓fraude",
                "impact": "fort" if abs(val) > 0.5 else "modéré" if abs(val) > 0.2 else "faible",
            }
            for feat, val in sorted_features
        ]

    # ── Visualisations ───────────────────────────────────────────────────────

    def plot_waterfall(
        self,
        x: np.ndarray,
        transaction_id: str = "TX_001",
        save: bool = True,
    ) -> plt.Figure:
        """
        Waterfall plot SHAP pour une transaction.
        Montre visuellement la contribution de chaque feature.
        """
        if x.ndim == 1:
            x = x.reshape(1, -1)

        shap_values = self._explainer(x)
        if hasattr(shap_values, "values") and shap_values.values.ndim == 3:
            # Multi-classe → prendre la classe fraude
            shap_values = shap.Explanation(
                values=shap_values.values[0, :, 1],
                base_values=shap_values.base_values[0, 1],
                data=shap_values.data[0],
                feature_names=self.feature_names,
            )
        else:
            shap_values = shap.Explanation(
                values=shap_values.values[0] if shap_values.values.ndim > 1 else shap_values.values,
                base_values=shap_values.base_values[0] if hasattr(shap_values.base_values, "__len__") else shap_values.base_values,
                data=shap_values.data[0],
                feature_names=self.feature_names,
            )

        fig, ax = plt.subplots(figsize=(10, 6))
        shap.plots.waterfall(shap_values, show=False)
        plt.title(f"Explication SHAP — Transaction {transaction_id}")

        if save:
            FIGURES_DIR.mkdir(parents=True, exist_ok=True)
            path = FIGURES_DIR / f"shap_waterfall_{transaction_id}.png"
            plt.savefig(path, dpi=150, bbox_inches="tight")
            logger.info(f"Waterfall SHAP sauvegardé : {path}")

        return plt.gcf()

    def plot_summary(
        self,
        X_sample: np.ndarray,
        max_display: int = 15,
        save: bool = True,
    ) -> None:
        """
        Summary plot SHAP global sur un échantillon.
        Montre les features les plus importantes globalement.
        """
        logger.info(f"Calcul SHAP sur {len(X_sample)} échantillons...")
        shap_values = self._explainer.shap_values(X_sample)

        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        plt.figure(figsize=(10, 8))
        shap.summary_plot(
            shap_values,
            X_sample,
            feature_names=self.feature_names,
            max_display=max_display,
            show=False,
        )
        plt.title("Importance globale des features (SHAP)")

        if save:
            FIGURES_DIR.mkdir(parents=True, exist_ok=True)
            path = FIGURES_DIR / "shap_summary.png"
            plt.savefig(path, dpi=150, bbox_inches="tight")
            logger.info(f"Summary SHAP sauvegardé : {path}")
