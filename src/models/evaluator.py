"""
evaluator.py — Calcul des métriques et génération des courbes d'évaluation.

Métriques utilisées (jamais l'Accuracy) :
  - F1-Score   : Compromis précision / rappel sur la classe minoritaire (fraude)
  - AUC-PR     : Area Under Precision-Recall Curve
                 → Métrique gold standard pour datasets très déséquilibrés
                 → Insensible au nombre de vrais négatifs (contrairement à AUC-ROC)
  - Recall     : Taux de détection des vraies fraudes
                 → Minimiser les faux négatifs est prioritaire (fraude manquée = coût élevé)
  - Precision  : Annoncé pour contexte, mais pas la métrique principale
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


# ── Constantes ──────────────────────────────────────────────────────────────

FIGURES_DIR = Path("notebooks/figures")
THRESHOLD_DEFAULT = 0.5


# ── Classe principale ────────────────────────────────────────────────────────

class ModelEvaluator:
    """
    Calcule les métriques et génère les courbes de performance.

    Usage :
        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate(y_true, y_proba)
        evaluator.plot_precision_recall_curve(y_true, y_proba, model_name="XGBoost")
    """

    def __init__(self, threshold: float = THRESHOLD_DEFAULT) -> None:
        """
        Parameters
        ----------
        threshold : float
            Seuil de décision. 0.5 par défaut, mais pour la fraude on
            privilégie souvent un seuil plus bas (0.3-0.4) pour maximiser le recall.
        """
        self.threshold = threshold

    # ── Métriques ────────────────────────────────────────────────────────────

    def evaluate(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        model_name: str = "Modèle",
    ) -> Dict[str, float]:
        """
        Calcule et affiche toutes les métriques.

        Parameters
        ----------
        y_true   : labels réels (0/1)
        y_proba  : probabilités de fraude (colonne 1 de predict_proba)
        model_name : nom du modèle pour les logs

        Returns
        -------
        dict avec f1, auc_pr, recall, precision, auc_roc
        """
        y_pred = (y_proba >= self.threshold).astype(int)

        metrics = {
            "f1_score":  f1_score(y_true, y_pred, zero_division=0),
            "auc_pr":    average_precision_score(y_true, y_proba),
            "recall":    recall_score(y_true, y_pred, zero_division=0),
            "precision": precision_score(y_true, y_pred, zero_division=0),
            "auc_roc":   roc_auc_score(y_true, y_proba),
        }

        logger.info(f"\n{'='*50}")
        logger.info(f"  Résultats — {model_name}  (seuil={self.threshold})")
        logger.info(f"{'='*50}")
        logger.info(f"  ★ AUC-PR     : {metrics['auc_pr']:.4f}  ← métrique principale")
        logger.info(f"  ★ F1-Score   : {metrics['f1_score']:.4f}")
        logger.info(f"  ★ Recall     : {metrics['recall']:.4f}")
        logger.info(f"    Precision  : {metrics['precision']:.4f}")
        logger.info(f"    AUC-ROC    : {metrics['auc_roc']:.4f}")
        logger.info(f"{'='*50}\n")

        # Rapport détaillé
        logger.info(classification_report(y_true, y_pred, target_names=["Légit.", "Fraude"]))

        return metrics

    def find_best_threshold(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        metric: str = "f1",
    ) -> float:
        """
        Cherche le seuil optimal qui maximise le F1-Score (ou le recall).

        Utile pour réduire les faux positifs sans sacrifier trop de recall.
        """
        precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)

        if metric == "f1":
            f1_scores = 2 * precisions * recalls / (precisions + recalls + 1e-9)
            best_idx = np.argmax(f1_scores[:-1])
        elif metric == "recall":
            # Trouver le seuil qui donne recall >= 0.95
            mask = recalls[:-1] >= 0.95
            best_idx = np.argmax(precisions[:-1][mask]) if mask.any() else 0
        else:
            raise ValueError(f"Métrique '{metric}' inconnue. Choisir 'f1' ou 'recall'.")

        best_threshold = float(thresholds[best_idx])
        logger.info(f"Seuil optimal ({metric}) : {best_threshold:.3f}")
        return best_threshold

    def confusion_matrix_df(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
    ) -> pd.DataFrame:
        """Retourne la matrice de confusion sous forme de DataFrame annoté."""
        y_pred = (y_proba >= self.threshold).astype(int)
        cm = confusion_matrix(y_true, y_pred)
        return pd.DataFrame(
            cm,
            index=["Réel: Légit.", "Réel: Fraude"],
            columns=["Prédit: Légit.", "Prédit: Fraude"],
        )

    # ── Courbes ──────────────────────────────────────────────────────────────

    def plot_precision_recall_curve(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        model_name: str = "Modèle",
        save: bool = True,
    ) -> plt.Figure:
        """
        Trace la courbe Precision-Recall.

        Pourquoi PR et pas ROC ?
        → La courbe ROC peut être trompeuse avec des datasets déséquilibrés.
           Un classificateur naïf peut avoir AUC-ROC = 0.95 juste parce qu'il
           y a beaucoup de vrais négatifs. La courbe PR est plus informative.
        """
        precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)
        auc_pr = average_precision_score(y_true, y_proba)

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(recalls, precisions, lw=2, label=f"{model_name} (AUC-PR = {auc_pr:.3f})")
        ax.axhline(y=y_true.mean(), color="gray", linestyle="--", label="Baseline (aléatoire)")

        ax.set_xlabel("Recall", fontsize=12)
        ax.set_ylabel("Precision", fontsize=12)
        ax.set_title(f"Courbe Precision-Recall — {model_name}", fontsize=14)
        ax.legend(fontsize=11)
        ax.grid(alpha=0.3)
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])

        if save:
            FIGURES_DIR.mkdir(parents=True, exist_ok=True)
            path = FIGURES_DIR / f"pr_curve_{model_name.lower().replace(' ', '_')}.png"
            fig.savefig(path, dpi=150, bbox_inches="tight")
            logger.info(f"Courbe PR sauvegardée : {path}")

        return fig

    def compare_models(
        self,
        results: Dict[str, Dict[str, float]],
        save: bool = True,
    ) -> pd.DataFrame:
        """
        Génère un tableau comparatif des modèles.

        Parameters
        ----------
        results : {model_name: metrics_dict, ...}
        """
        df = pd.DataFrame(results).T[["auc_pr", "f1_score", "recall", "precision", "auc_roc"]]
        df.columns = ["AUC-PR ★", "F1-Score ★", "Recall ★", "Precision", "AUC-ROC"]
        df = df.sort_values("AUC-PR ★", ascending=False)

        logger.info("\n" + df.to_string())

        if save:
            FIGURES_DIR.mkdir(parents=True, exist_ok=True)
            df.to_csv(FIGURES_DIR / "model_comparison.csv")

        return df
