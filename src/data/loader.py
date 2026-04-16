"""
loader.py — Chargement et split stratifié du dataset.

Responsabilité unique : lire le CSV et produire des splits
train/val/test reproductibles et stratifiés sur is_fraud.

Pourquoi stratifié ? Le dataset est très déséquilibré (<1% de fraudes).
Un split aléatoire classique risquerait de concentrer les fraudes dans
un seul split, ce qui biaiserait l'évaluation des modèles.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import pandas as pd
from loguru import logger
from sklearn.model_selection import train_test_split


# ── Constantes ──────────────────────────────────────────────────────────────

# Path is now relative to this file (src/data/loader.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "improved_fraud_dataset.zip"
TARGET_COLUMN = "is_fraud"
RANDOM_STATE = 42

# Splits : 70% train · 15% val · 15% test
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15   # val  = 15% du total
TEST_RATIO = 0.15  # test = 15% du total


# ── Classe principale ────────────────────────────────────────────────────────

class DataLoader:
    """
    Charge le dataset de fraude et le divise en ensembles train/val/test
    de manière stratifiée pour respecter la distribution de is_fraud.
    """

    def __init__(
        self,
        data_path: str | Path = DEFAULT_DATA_PATH,
        target_col: str = TARGET_COLUMN,
        random_state: int = RANDOM_STATE,
    ) -> None:
        self.data_path = Path(data_path)
        self.target_col = target_col
        self.random_state = random_state

        self._df: pd.DataFrame | None = None

    # ── Chargement ──────────────────────────────────────────────────────────

    def load(self) -> pd.DataFrame:
        """
        Charge le CSV en mémoire avec les dtypes optimisés.

        Returns
        -------
        pd.DataFrame
            Dataset complet non filtré.
        """
        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Dataset introuvable : {self.data_path.resolve()}\n"
                "Vérifier que improved_fraud_dataset.csv est dans data/raw/"
            )

        logger.info(f"Chargement du dataset : {self.data_path} ...")

        self._df = pd.read_csv(
            self.data_path,
            dtype=self._get_dtype_hints(),
            low_memory=False,
        )

        self._log_basic_stats()
        return self._df

    @staticmethod
    def _get_dtype_hints() -> dict[str, str]:
        """
        Suggestions de types pour optimiser la mémoire.
        Ajuster selon les colonnes réelles du CSV.
        """
        return {
            "is_fraud": "int8",        # 0 ou 1 — int8 économise de la mémoire
            # Les colonnes numériques seront inférées automatiquement
            # Les catégorielles seront converties dans le preprocessor
        }

    def _log_basic_stats(self) -> None:
        """Affiche les statistiques basiques du dataset chargé."""
        df = self._df
        n_total = len(df)
        n_fraud = df[self.target_col].sum()
        fraud_pct = 100 * n_fraud / n_total

        logger.info(f"  Lignes       : {n_total:,}")
        logger.info(f"  Colonnes     : {len(df.columns)}")
        logger.info(f"  Fraudes      : {n_fraud:,}  ({fraud_pct:.2f}%)")
        logger.info(f"  Légitimes    : {n_total - n_fraud:,}  ({100 - fraud_pct:.2f}%)")
        logger.info(f"  Ratio déséq. : 1:{int((n_total - n_fraud) / n_fraud)}")

    # ── Split ────────────────────────────────────────────────────────────────

    def get_splits(
        self,
        df: pd.DataFrame | None = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame,
               pd.Series, pd.Series, pd.Series]:
        """
        Retourne (X_train, X_val, X_test, y_train, y_val, y_test).

        Stratégie :
        1. Séparer target des features
        2. Split stratifié 70/30 → train + temp
        3. Re-split stratifié 50/50 sur temp → val + test

        Parameters
        ----------
        df : pd.DataFrame, optional
            Si None, utilise le DataFrame chargé par load().

        Returns
        -------
        Tuple de 6 DataFrames/Series
        """
        if df is None:
            if self._df is None:
                raise RuntimeError("Appeler load() avant get_splits().")
            df = self._df

        if self.target_col not in df.columns:
            raise ValueError(f"Colonne cible '{self.target_col}' manquante.")

        X = df.drop(columns=[self.target_col])
        y = df[self.target_col]

        # Split 1 : train (70%) vs temp (30%)
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y,
            test_size=(VAL_RATIO + TEST_RATIO),
            stratify=y,
            random_state=self.random_state,
        )

        # Split 2 : val (50% de temp = 15% total) vs test (50% de temp = 15% total)
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp,
            test_size=0.5,
            stratify=y_temp,
            random_state=self.random_state,
        )

        logger.info("Splits créés :")
        logger.info(f"  Train : {len(X_train):,} lignes | Fraudes: {y_train.sum():,}")
        logger.info(f"  Val   : {len(X_val):,} lignes | Fraudes: {y_val.sum():,}")
        logger.info(f"  Test  : {len(X_test):,} lignes | Fraudes: {y_test.sum():,}")

        return X_train, X_val, X_test, y_train, y_val, y_test


# ── Script standalone (test rapide) ─────────────────────────────────────────

if __name__ == "__main__":
    loader = DataLoader()
    df = loader.load()
    splits = loader.get_splits()
    logger.success("DataLoader OK ✓")
