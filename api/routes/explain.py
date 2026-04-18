"""
explain.py — Endpoints d'explication :
  /explain/shap — Score + SHAP features (rapide, ~2-3s)
  /explain/llm  — Explication LLM seule (lent, ~30-60s)  
  /explain/     — Tout-en-un (legacy)
"""

from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from typing import List, Optional

from api.schemas import ExplanationResponse, RiskLevel, ShapFeature, TransactionInput

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")


router = APIRouter(prefix="/explain", tags=["Explicabilité"])


def get_full_service():
    """Injection de dépendance — service complet (modèle + SHAP + LLM)."""
    from api.main import full_service
    return full_service


# ── Schema pour la réponse SHAP (sans LLM) ──────────────────────────────────

class ShapResponse(BaseModel):
    transaction_id: str
    fraud_probability: float
    is_fraud: bool
    risk_level: RiskLevel
    top_features: List[ShapFeature]
    threshold_used: float
    model_name: str
    processing_time_ms: float


class LLMRequest(BaseModel):
    transaction_id: str
    transaction_amount: float
    currency: str = "MAD"
    hour: int
    transaction_type: str = ""
    merchant_category: str = ""
    city: str = ""
    country: str = ""
    device_type: str = ""
    fraud_probability: float
    top_features: List[ShapFeature]
    threshold: float = 0.5
    # Provider LLM : 'local' (Ollama Mistral) ou 'perplexity'
    llm_provider: str = "local"


class LLMResponse(BaseModel):
    transaction_id: str
    explanation: str
    llm_model: str
    llm_provider: str = "local"
    processing_time_ms: float


# ── Endpoint SHAP (rapide) ───────────────────────────────────────────────────

@router.post("/shap", response_model=ShapResponse, summary="Score + SHAP (rapide)")
def explain_shap(
    transaction: TransactionInput,
    service=Depends(get_full_service),
) -> ShapResponse:
    start = time.perf_counter()
    try:
        result = service.predict_and_shap(transaction.model_dump(), model_name=transaction.selected_model)
    except Exception as e:
        logger.error(f"Erreur SHAP [{transaction.transaction_id}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    elapsed_ms = (time.perf_counter() - start) * 1000
    fraud_prob = result["fraud_probability"]
    risk = _compute_risk_level(fraud_prob)

    return ShapResponse(
        transaction_id=transaction.transaction_id,
        fraud_probability=fraud_prob,
        is_fraud=fraud_prob >= result["threshold"],
        risk_level=risk,
        top_features=[ShapFeature(**f) for f in result["top_features"]],
        threshold_used=result["threshold"],
        model_name=transaction.selected_model,
        processing_time_ms=round(elapsed_ms, 2),
    )


# ── Endpoint LLM (lent) ─────────────────────────────────────────────────────

@router.post("/llm", response_model=LLMResponse, summary="Explication LLM seule")
def explain_llm(
    req: LLMRequest,
    service=Depends(get_full_service),
) -> LLMResponse:
    start = time.perf_counter()
    provider = req.llm_provider if req.llm_provider in ("local", "perplexity") else "local"
    model_used = OLLAMA_MODEL if provider == "local" else getattr(service.agent, "model", "sonar")

    try:
        tx_dict = req.model_dump()
        features_raw = [f.model_dump() for f in req.top_features]

        explanation = service.generate_explanation(
            transaction=tx_dict,
            fraud_probability=req.fraud_probability,
            top_features=features_raw,
            threshold=req.threshold,
            llm_provider=provider,
        )
    except Exception as e:
        logger.error(f"Erreur LLM [{req.transaction_id}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    elapsed_ms = (time.perf_counter() - start) * 1000
    return LLMResponse(
        transaction_id=req.transaction_id,
        explanation=explanation,
        llm_model=model_used,
        llm_provider=provider,
        processing_time_ms=round(elapsed_ms, 2),
    )


@router.post(
    "/",
    response_model=ExplanationResponse,
    summary="Analyser + expliquer une transaction",
    description=(
        "Retourne le score de fraude **et** une explication en langage naturel "
        "générée par le LLM local (Ollama). Plus lent que /predict (~2-10s)."
    ),
)
def explain_fraud(
    transaction: TransactionInput,
    service=Depends(get_full_service),
) -> ExplanationResponse:
    """
    Endpoint d'explication complète.

    - Input  : TransactionInput
    - Output : ExplanationResponse (score + SHAP features + texte LLM)
    - SLA    : < 15s (temps de génération LLM local)
    """
    start = time.perf_counter()

    try:
        result = service.predict_and_explain(transaction.model_dump(), model_name=transaction.selected_model)
    except Exception as e:
        logger.error(f"Erreur explication [{transaction.transaction_id}]: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'explication : {str(e)}",
        )

    elapsed_ms = (time.perf_counter() - start) * 1000
    fraud_prob = result["fraud_probability"]
    risk = _compute_risk_level(fraud_prob)

    # Convertir les top features en objets Pydantic
    shap_features = [
        ShapFeature(
            feature=f["feature"],
            shap_value=f["shap_value"],
            direction=f["direction"],
            impact=f["impact"],
        )
        for f in result["top_features"]
    ]

    logger.info(
        f"[{transaction.transaction_id}] proba={fraud_prob:.3f} "
        f"risk={risk} ({elapsed_ms:.1f}ms)"
    )

    return ExplanationResponse(
        transaction_id=transaction.transaction_id,
        fraud_probability=fraud_prob,
        is_fraud=fraud_prob >= result["threshold"],
        risk_level=risk,
        top_features=shap_features,
        explanation=result["explanation"],
        model_name=transaction.selected_model,
        llm_model=result["llm_model"],
        processing_time_ms=round(elapsed_ms, 2),
    )


def _compute_risk_level(probability: float) -> RiskLevel:
    if probability >= 0.9:
        return RiskLevel.CRITIQUE
    elif probability >= 0.7:
        return RiskLevel.ELEVE
    elif probability >= 0.4:
        return RiskLevel.MOYEN
    else:
        return RiskLevel.FAIBLE
