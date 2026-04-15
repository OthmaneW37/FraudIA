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
    Tous les champs sont validés automatiquement par Pydantic.
    """
    transaction_id:   str   = Field(..., description="Identifiant unique de la transaction")
    transaction_amount: float = Field(..., gt=0, description="Montant de la transaction (doit être > 0)")
    currency:         str   = Field(default="MAD", max_length=3, description="Code devise ISO 4217")
    hour:             int   = Field(..., ge=0, le=23, description="Heure de la transaction (0-23)")
    minute:           int   = Field(default=0, ge=0, le=59)
    transaction_type: TransactionType = Field(..., description="Type de transaction")
    merchant_category: str  = Field(..., description="Catégorie du marchand")
    city:             str   = Field(..., description="Ville de la transaction")
    country:          str   = Field(..., description="Pays de la transaction")
    device_type:      str   = Field(..., description="Type de device")
    kyc_verified:     bool  = Field(..., description="Le KYC est-il vérifié ? (booléen)")
    otp_used:         bool  = Field(..., description="L'OTP a-t-il été utilisé ? (booléen)")
    selected_model:    str   = Field(default="xgboost", description="Modèle à utiliser pour l'analyse")

    # Features optionnelles (historique client — enrichissement)
    avg_amount_30d:   Optional[float] = Field(None, ge=0, description="Montant moyen sur 30j")
    txn_count_today:  Optional[int]   = Field(None, ge=0, description="Nombre de transactions aujourd'hui")

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, v: str) -> str:
        return v.upper()

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id":     "TX_2024_001",
                "transaction_amount": 15000.0,
                "currency":           "MAD",
                "hour":               2,
                "minute":             37,
                "transaction_type":   "transfer",
                "merchant_category":  "Virement international",
                "city":               "Rabat",
                "country":            "Maroc",
                "device_type":        "device_inconnu_x7",
                "kyc_verified":       False,
                "otp_used":           False,
                "avg_amount_30d":     500.0,
                "txn_count_today":    12,
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
    transaction_id:   str
    fraud_probability: float = Field(..., ge=0.0, le=1.0, description="Score de fraude [0, 1]")
    is_fraud:         bool
    risk_level:       RiskLevel
    threshold_used:   float
    model_name:       str
    processing_time_ms: float


class ExplanationResponse(BaseModel):
    """Réponse de l'endpoint /explain — inclut score + explication LLM + SHAP."""
    transaction_id:    str
    fraud_probability: float
    is_fraud:          bool
    risk_level:        RiskLevel
    top_features:      List[ShapFeature]
    explanation:       str = Field(..., description="Explication en langage naturel (LLM)")
    llm_model:         str
    processing_time_ms: float


class HealthResponse(BaseModel):
    """Réponse de l'endpoint /health."""
    status:       str   # "healthy" | "degraded" | "unhealthy"
    model_loaded: bool
    llm_online:   bool
    version:      str = "1.0.0"
