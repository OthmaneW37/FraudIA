"""
predict.py — Endpoint /predict : score de fraude.

Reçoit une transaction → retourne la probabilité de fraude + décision.
Pas d'appel LLM ici (performant, < 100ms).
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from api.schemas import ExplanationResponse, PredictionResponse, RiskLevel, TransactionInput


router = APIRouter(prefix="/predict", tags=["Détection"])


def get_model_service():
    """Injection de dépendance — sera remplacé par le vrai service en main.py."""
    from api.main import model_service
    return model_service


@router.post(
    "/",
    response_model=PredictionResponse,
    summary="Analyser une transaction",
    description="Retourne le score de fraude et la décision pour une transaction.",
)
async def predict_fraud(
    transaction: TransactionInput,
    service=Depends(get_model_service),
) -> PredictionResponse:
    """
    Endpoint de prédiction rapide.

    - Input  : TransactionInput (validé par Pydantic)
    - Output : PredictionResponse (score + décision + niveau de risque)
    - SLA    : < 200ms (pas d'appel LLM)
    """
    start = time.perf_counter()

    try:
        result = service.predict(transaction.model_dump(), model_name=transaction.selected_model)
    except Exception as e:
        logger.error(f"Erreur prédiction [{transaction.transaction_id}]: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la prédiction : {str(e)}",
        )

    elapsed_ms = (time.perf_counter() - start) * 1000
    fraud_prob = result["fraud_probability"]

    # Calcul du niveau de risque
    risk = _compute_risk_level(fraud_prob)

    logger.info(
        f"[{transaction.transaction_id}] proba={fraud_prob:.3f} "
        f"risk={risk} ({elapsed_ms:.1f}ms)"
    )

    return PredictionResponse(
        transaction_id=transaction.transaction_id,
        fraud_probability=fraud_prob,
        is_fraud=fraud_prob >= result["threshold"],
        risk_level=risk,
        threshold_used=result["threshold"],
        model_name=result["model_name"],
        processing_time_ms=round(elapsed_ms, 2),
    )


def _compute_risk_level(probability: float) -> RiskLevel:
    """Convertit une probabilité en niveau de risque catégoriel."""
    if probability >= 0.9:
        return RiskLevel.CRITIQUE
    elif probability >= 0.7:
        return RiskLevel.ELEVE
    elif probability >= 0.4:
        return RiskLevel.MOYEN
    else:
        return RiskLevel.FAIBLE
