"""
explain.py - Endpoints d'explication.
"""

from __future__ import annotations

import os
import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel

from api.auth import get_current_user_optional
from api.notifications import notify_fraud_alert
from api.schemas import ExplanationResponse, RiskLevel, ShapFeature, TransactionInput
from api.translation import MoroccanTranslator

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")


router = APIRouter(prefix="/explain", tags=["Explicabilite"])


def get_full_service():
    """Injection de dependance - service complet (modele + SHAP + LLM)."""
    from api.main import full_service

    return full_service


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
    llm_provider: str = "local"


class LLMResponse(BaseModel):
    transaction_id: str
    explanation: str
    llm_model: str
    llm_provider: str = "local"
    processing_time_ms: float


@router.post("/shap", response_model=ShapResponse, summary="Score + SHAP (rapide)")
def explain_shap(
    transaction: TransactionInput,
    service=Depends(get_full_service),
    user: dict | None = Depends(get_current_user_optional),
) -> ShapResponse:
    start = time.perf_counter()
    transaction_data = transaction.model_dump()
    
    adapted_tx, context = MoroccanTranslator.translate_to_bangladesh(transaction_data)

    try:
        result = service.predict_and_shap(adapted_tx, model_name=transaction.selected_model)
    except Exception as exc:
        logger.error(f"Erreur SHAP [{transaction.transaction_id}]: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    elapsed_ms = (time.perf_counter() - start) * 1000
    fraud_prob = result["fraud_probability"]
    threshold = result["threshold"]
    is_fraud = fraud_prob >= threshold
    risk = _compute_risk_level(fraud_prob)
    top_features = [ShapFeature(**feature) for feature in result["top_features"]]

    if is_fraud:
        notify_fraud_alert(
            user=user,
            transaction=transaction_data,
            is_fraud=is_fraud,
            fraud_probability=fraud_prob,
            threshold=threshold,
            risk_level=risk.value,
            model_name=transaction.selected_model,
            top_features=result["top_features"],
        )

    return ShapResponse(
        transaction_id=transaction.transaction_id,
        fraud_probability=fraud_prob,
        is_fraud=is_fraud,
        risk_level=risk,
        top_features=top_features,
        threshold_used=threshold,
        model_name=transaction.selected_model,
        processing_time_ms=round(elapsed_ms, 2),
    )


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
        features_raw = [feature.model_dump() for feature in req.top_features]
        
        adapted_tx, context = MoroccanTranslator.translate_to_bangladesh(tx_dict)

        explanation = service.generate_explanation(
            transaction=adapted_tx,
            fraud_probability=req.fraud_probability,
            top_features=features_raw,
            threshold=req.threshold,
            llm_provider=provider,
        )
        explanation = MoroccanTranslator.translate_explanation_to_maroc(explanation, context)
    except Exception as exc:
        logger.error(f"Erreur LLM [{req.transaction_id}]: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

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
        "Retourne le score de fraude et une explication en langage naturel "
        "generee par le LLM. Plus lent que /predict."
    ),
)
def explain_fraud(
    transaction: TransactionInput,
    service=Depends(get_full_service),
    user: dict | None = Depends(get_current_user_optional),
) -> ExplanationResponse:
    start = time.perf_counter()
    transaction_data = transaction.model_dump()
    
    adapted_tx, context = MoroccanTranslator.translate_to_bangladesh(transaction_data)

    try:
        result = service.predict_and_explain(adapted_tx, model_name=transaction.selected_model)
        if "explanation" in result:
            result["explanation"] = MoroccanTranslator.translate_explanation_to_maroc(result["explanation"], context)
    except Exception as exc:
        logger.error(f"Erreur explication [{transaction.transaction_id}]: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'explication : {exc}",
        ) from exc

    elapsed_ms = (time.perf_counter() - start) * 1000
    fraud_prob = result["fraud_probability"]
    threshold = result["threshold"]
    is_fraud = fraud_prob >= threshold
    risk = _compute_risk_level(fraud_prob)

    shap_features = [
        ShapFeature(
            feature=feature["feature"],
            shap_value=feature["shap_value"],
            direction=feature["direction"],
            impact=feature["impact"],
        )
        for feature in result["top_features"]
    ]

    if is_fraud:
        notify_fraud_alert(
            user=user,
            transaction=transaction_data,
            is_fraud=is_fraud,
            fraud_probability=fraud_prob,
            threshold=threshold,
            risk_level=risk.value,
            model_name=transaction.selected_model,
            top_features=result["top_features"],
        )

    logger.info(
        f"[{transaction.transaction_id}] proba={fraud_prob:.3f} "
        f"risk={risk.value} ({elapsed_ms:.1f}ms)"
    )

    return ExplanationResponse(
        transaction_id=transaction.transaction_id,
        fraud_probability=fraud_prob,
        is_fraud=is_fraud,
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
    if probability >= 0.7:
        return RiskLevel.ELEVE
    if probability >= 0.5:
        return RiskLevel.MOYEN
    return RiskLevel.FAIBLE
