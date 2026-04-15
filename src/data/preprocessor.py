"""
preprocessor.py — Pipeline sklearn de preprocessing + SMOTE.

RÈGLE CRITIQUE : SMOTE est appliqué UNIQUEMENT sur le train set.
L'appliquer sur val/test constituerait une fuite de données (data leakage)
et produirait des métriques artificiellement gonflées.

Pipeline :
  1. Imputation des valeurs manquantes
  2. Encodage des variables catégorielles (OrdinalEncoder)
  3. Normalisation des variables numériques (StandardScaler)
  4. SMOTE sur le train uniquement (dans fit_transform)
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from loguru import logger
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, StandardScaler


# ── Constantes ──────────────────────────────────────────────────────────────

RANDOM_STATE = 42
SMOTE_SAMPLING_STRATEGY = 0.2   # Ratio souhaité minorité/majorité après SMOTE
                                  # 0.2 = 20% de fraudes par rapport aux légitimes
                                  # Le dataset brut a déjà ~9% de fraudes.

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"


# ── Classe principale ────────────────────────────────────────────────────────

class FraudPreprocessor:
    """
    Orchestre le preprocessing complet :
    - ColumnTransformer pour les features numériques / catégorielles
    - SMOTE pour rééquilibrer le train set
    - Sauvegarde / chargement du pipeline via joblib
    """

    def __init__(
        self,
        numerical_features: List[str] | None = None,
        categorical_features: List[str] | None = None,
        smote_sampling_strategy: float = SMOTE_SAMPLING_STRATEGY,
        random_state: int = RANDOM_STATE,
    ) -> None:
        self.numerical_features = numerical_features or []
        self.categorical_features = categorical_features or []
        self.smote_sampling_strategy = smote_sampling_strategy
        self.random_state = random_state

        self._preprocessor: ColumnTransformer | None = None
        self._feature_names_out: List[str] = []

    # ── Construction du pipeline sklearn ────────────────────────────────────

    def _build_preprocessor(self) -> ColumnTransformer:
        """
        Construit le ColumnTransformer.

        Numérique : Imputation médiane → StandardScaler
          Médiane plutôt que moyenne car robuste aux outliers (montants extrêmes).

        Catégoriel : Imputation mode → OrdinalEncoder
          OrdinalEncoder est suffisant pour les modèles à base d'arbres (XGBoost,
          RF) qui n'ont pas besoin de one-hot encoding.
        """
        num_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])

        cat_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OrdinalEncoder(
                handle_unknown="use_encoded_value",
                unknown_value=-1,           # Nouvelles catégories → -1 en inference
            )),
        ])

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", num_pipeline, self.numerical_features),
                ("cat", cat_pipeline, self.categorical_features),
            ],
            remainder="drop",               # Supprimer les colonnes non spécifiées
        )
        return preprocessor

    def _apply_feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ajoute des features calculées pour aider le modèle à mieux séparer la fraude."""
        df = df.copy()
        
        # 1. Ratio Montant / Moyenne (Très puissant pour la fraude)
        # Si avg_amount_30d n'existe pas, on met 1.0 (on ne peut pas diviser par 0)
        avg = df.get("avg_amount_30d", df.get("transaction_amount", 1.0)).fillna(df["transaction_amount"])
        df["amount_ratio"] = df["transaction_amount"] / (avg + 1e-9)
        
        # 2. Heure cyclique (23h est proche de 00h)
        if "hour" in df.columns:
            df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
            df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
            
        # 3. Log du montant (réduit l'impact des outliers)
        df["log_amount"] = np.log1p(df["transaction_amount"])
        
        return df

    # ── API publique ─────────────────────────────────────────────────────────

    def fit_transform_train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fit le preprocessor sur le TRAIN uniquement, puis applique SMOTE.
        """
        # Feature Engineering
        X_train = self._apply_feature_engineering(X_train)

        if not self.numerical_features and not self.categorical_features:
            # Auto-détection des colonnes si non spécifiées
            num, cat = self._auto_detect_columns(X_train)
            self.numerical_features = num
            self.categorical_features = cat
            logger.info(f"Features numériques  : {self.numerical_features}")
            logger.info(f"Features catégorielles: {self.categorical_features}")

        self._preprocessor = self._build_preprocessor()

        logger.info("Fit + Transform du preprocessor sur le train set...")
        X_processed = self._preprocessor.fit_transform(X_train)
        self._feature_names_out = self._get_feature_names()

        # Ratio fraudes avant SMOTE
        n_fraud_before = y_train.sum()
        logger.info(f"Avant SMOTE : {n_fraud_before:,} fraudes / {len(y_train):,} total")

        # Application SMOTE uniquement sur le train
        logger.info(f"Application SMOTE (sampling_strategy={self.smote_sampling_strategy})...")
        smote = SMOTE(
            sampling_strategy=self.smote_sampling_strategy,
            random_state=self.random_state,
            n_jobs=-1,
        )
        X_resampled, y_resampled = smote.fit_resample(X_processed, y_train)

        n_fraud_after = y_resampled.sum()
        logger.info(f"Après SMOTE  : {n_fraud_after:,} fraudes / {len(y_resampled):,} total")
        logger.success("Preprocessing train OK ✓")

        return X_resampled, y_resampled

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """
        Applique le pipeline déjà fitté sur val ou test.
        Pas de SMOTE ici (sinon data leakage).

        Parameters
        ----------
        X : pd.DataFrame
            Données val ou test.

        Returns
        -------
        np.ndarray
            Features transformées.
        """
        if self._preprocessor is None:
            raise RuntimeError(
                "Appeler fit_transform_train() avant transform()."
            )
        # Feature Engineering
        X = self._apply_feature_engineering(X)
        return self._preprocessor.transform(X)

    # ── Sauvegarde / chargement ──────────────────────────────────────────────

    def save(self, path: str | Path | None = None) -> Path:
        """Sauvegarde le preprocessor fitté via joblib."""
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        save_path = Path(path) if path else MODELS_DIR / "preprocessor.joblib"
        joblib.dump(self._preprocessor, save_path)
        logger.info(f"Preprocessor sauvegardé : {save_path}")
        return save_path

    @classmethod
    def load(cls, path: str | Path) -> "FraudPreprocessor":
        """Charge un preprocessor préalablement sauvegardé."""
        instance = cls()
        instance._preprocessor = joblib.load(path)
        # Reconstruire les feature names qui n'ont pas été dumpés
        instance._feature_names_out = instance._get_feature_names()
        logger.info(f"Preprocessor chargé : {path}")
        return instance

    # ── Helpers ─────────────────────────────────────────────────────────────

    @property
    def feature_names(self) -> List[str]:
        """Noms des features après transformation (utile pour SHAP)."""
        return self._feature_names_out

    def _get_feature_names(self) -> List[str]:
        """Reconstruit les noms de colonnes après ColumnTransformer."""
        names: List[str] = []
        for name, trans, cols in self._preprocessor.transformers_:
            if name == "remainder":
                continue
            if hasattr(trans, "get_feature_names_out"):
                names.extend(trans.get_feature_names_out(cols))
            else:
                names.extend(cols)
        return names

    @staticmethod
    def _auto_detect_columns(
        df: pd.DataFrame,
    ) -> Tuple[List[str], List[str]]:
        """
        Détecte automatiquement les colonnes numériques et catégorielles.
        Utilisé si l'utilisateur n'a pas spécifié les colonnes manuellement.
        """
        numerical = df.select_dtypes(include=["number"]).columns.tolist()
        categorical = df.select_dtypes(
            include=["object", "category", "bool"]
        ).columns.tolist()
        return numerical, categorical


# ── Script standalone ────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.data.loader import DataLoader

    loader = DataLoader()
    df = loader.load()
    X_train, X_val, X_test, y_train, y_val, y_test = loader.get_splits(df)

    preprocessor = FraudPreprocessor()
    X_train_proc, y_train_proc = preprocessor.fit_transform_train(X_train, y_train)
    X_val_proc = preprocessor.transform(X_val)
    X_test_proc = preprocessor.transform(X_test)

    logger.info(f"Shape train (après SMOTE) : {X_train_proc.shape}")
    logger.info(f"Shape val                  : {X_val_proc.shape}")
    logger.success("Preprocessor OK ✓")
