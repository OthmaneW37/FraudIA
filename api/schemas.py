"""
schemas.py — Modèles Pydantic pour la validation des requêtes/réponses FastAPI.

Pourquoi Pydantic v2 ?
  → Validation automatique des types à l'entrée de chaque endpoint
  → Documentation OpenAPI (Swagger) générée automatiquement
  → Erreurs claires pour les clients de l'API
  → Plus rapide que Pydantic v1 grâce au core Rust

Schémas définis :
  - TransactionInput   : données d'une transaction à analyser
  - PredictionResponse : réponse du /predict (score + décision)
  - ExplanationResponse: réponse du /explain (score + explication LLM)
  - HealthResponse     : réponse du /health
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ────────────────────────────────────────────────────────────────────

class TransactionType(str, Enum):
    TRANSFER    = "transfer"
    PAYMENT     = "payment"
    WITHDRAWAL  = "withdrawal"
    DEPOSIT     = "deposit"
    PURCHASE    = "purchase"
    OTHER       = "other"


class KYCStatus(str, Enum):
    COMPLETE    = "complete"
    INCOMPLETE  = "incomplete"
    PENDING     = "pending"
    REJECTED    = "rejected"


class RiskLevel(str, Enum):
    FAIBLE    = "FAIBLE"
    MOYEN     = "MOYEN"
    ELEVE     = "ELEVÉ"
    CRITIQUE  = "CRITIQUE"


# ── Input ─────────────────────────────────────────────────────────────────────

class TransactionInput(BaseModel):
    """
    Données d'une transaction envoyée à l'API pour analyse.
    Correspond aux colonnes réelles du dataset Bangladesh Fraud Detection.
    """
    transaction_id:        str   = Field(..., description="Identifiant unique de la transaction")
    transaction_amount:    float = Field(..., gt=0, description="Montant en BDT")
    currency:              str   = Field(default="BDT", max_length=3)
    hour:                  int   = Field(..., ge=0, le=23)
    day_of_week:           Optional[int]   = Field(None, ge=0, le=6)
    transaction_type:      str   = Field(..., description="purchase | withdrawal | transfer")
    merchant_category:     str   = Field(..., description="grocery | fashion | electronics | travel")
    city:                  str   = Field(..., description="Dhaka | Chittagong | Khulna | Rajshahi")
    country:               str   = Field(default="Bangladesh")
    device_type:           str   = Field(..., description="mobile | desktop | tablet")
    payment_method:        Optional[str]   = Field(None, description="bkash | nagad | card | bank")
    card_type:             Optional[str]   = Field(None, description="debit | credit")
    operating_system:      Optional[str]   = Field(None, description="Android | Windows | iOS")
    browser:               Optional[str]   = Field(None, description="Chrome | Edge | Safari")
    kyc_verified:          bool  = Field(...)
    otp_used:              bool  = Field(...)
    user_account_age_days: Optional[float] = Field(None, ge=0)
    selected_model:        str   = Field(default="xgboost")

    # Features séquentielles (vélocité temporelle)
    txn_count_24h:         Optional[float] = Field(None, ge=0)
    txn_sum_24h:           Optional[float] = Field(None, ge=0)
    time_since_last_txn:   Optional[float] = Field(None)
    is_new_city:           Optional[int]   = Field(None, ge=0, le=1)

    # Champs legacy — conservés pour compatibilité
    avg_amount_30d:        Optional[float] = Field(None, ge=0)
    txn_count_today:       Optional[int]   = Field(None, ge=0)
    minute:                Optional[int]   = Field(None, ge=0, le=59)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, v: str) -> str:
        return v.upper()

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id":        "TX_2024_BD_001",
                "transaction_amount":    5000.0,
                "currency":              "BDT",
                "hour":                  2,
                "transaction_type":      "transfer",
                "merchant_category":     "electronics",
                "city":                  "Dhaka",
                "country":               "Bangladesh",
                "device_type":           "mobile",
                "payment_method":        "bkash",
                "card_type":             "debit",
                "kyc_verified":          False,
                "otp_used":              False,
                "user_account_age_days": 30,
                "txn_count_24h":         8,
                "txn_sum_24h":           40000,
                "time_since_last_txn":   5,
                "is_new_city":           1,
            }
        }
    }


# ── Outputs ──────────────────────────────────────────────────────────────────

class ShapFeature(BaseModel):
    """Contribution SHAP d'une feature individuelle."""
    feature:    str
    shap_value: float
    direction:  str   # "↑fraude" | "↓fraude"
    impact:     str   # "fort" | "modéré" | "faible"


class PredictionResponse(BaseModel):
    """Réponse de l'endpoint /predict."""
    model_config = {"protected_namespaces": ()}
    transaction_id:   str
    fraud_probability: float = Field(..., ge=0.0, le=1.0, description="Score de fraude [0, 1]")
    is_fraud:         bool
    risk_level:       RiskLevel
    threshold_used:   float
    model_name:       str
    processing_time_ms: float


class ExplanationResponse(BaseModel):
    """Réponse de l'endpoint /explain — inclut score + explication LLM + SHAP."""
    model_config = {"protected_namespaces": ()}
    transaction_id:    str
    fraud_probability: float
    is_fraud:          bool
    risk_level:        RiskLevel
    top_features:      List[ShapFeature]
    explanation:       str = Field(..., description="Explication en langage naturel (LLM)")
    model_name:        str = Field(..., description="Nom du modèle ML utilisé")
    llm_model:         str
    processing_time_ms: float


class HealthResponse(BaseModel):
    """Réponse de l'endpoint /health avec métriques du modèle."""
    model_config = {"protected_namespaces": ()}
    status:       str   # "healthy" | "degraded" | "unhealthy"
    model_loaded: bool
    llm_online:   bool
    version:      str = "2.0.0"
    model_metrics: Optional[Dict] = Field(default=None, description="Métriques de performance XGBoost")
