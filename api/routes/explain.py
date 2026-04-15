"""
explain.py — Endpoint /explain : score + explication LLM.

Pipeline complet :
  transaction → preprocessing → modèle → SHAP → LLM → explication NL
  
Plus lent que /predict (~2-10s selon le LLM) mais retourne l'explication complète.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from api.schemas import ExplanationResponse, RiskLevel, ShapFeature, TransactionInput


router = APIRouter(prefix="/explain", tags=["Explicabilité"])


def get_full_service():
    """Injection de dépendance — service complet (modèle + SHAP + LLM)."""
    from api.main import full_service
    return full_service


@router.post(
    "/",
    response_model=ExplanationResponse,
    summary="Analyser + expliquer une transaction",
    description=(
        "Retourne le score de fraude **et** une explication en langage naturel "
        "générée par le LLM local (Ollama). Plus lent que /predict (~2-10s)."
    ),
)
async def explain_fraud(
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
