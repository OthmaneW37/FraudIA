"""
predict.py - Endpoint /predict : score de fraude.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from api.auth import get_current_user_optional
from api.notifications import notify_fraud_alert
from api.schemas import PredictionResponse, RiskLevel, TransactionInput


router = APIRouter(prefix="/predict", tags=["Detection"])


def get_model_service():
    """Injection de dependance - sera remplacee par le vrai service en main.py."""
    from api.main import model_service

    return model_service


@router.post(
    "/",
    response_model=PredictionResponse,
    summary="Analyser une transaction",
    description="Retourne le score de fraude et la decision pour une transaction.",
)
async def predict_fraud(
    transaction: TransactionInput,
    service=Depends(get_model_service),
    user: dict | None = Depends(get_current_user_optional),
) -> PredictionResponse:
    start = time.perf_counter()
    transaction_data = transaction.model_dump()

    try:
        result = service.predict(transaction_data, model_name=transaction.selected_model)
    except Exception as exc:
        logger.error(f"Erreur prediction [{transaction.transaction_id}]: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la prediction : {exc}",
        ) from exc

    elapsed_ms = (time.perf_counter() - start) * 1000
    fraud_prob = result["fraud_probability"]
    threshold = result["threshold"]
    is_fraud = fraud_prob >= threshold
    risk = _compute_risk_level(fraud_prob)

    if is_fraud:
        notify_fraud_alert(
            user=user,
            transaction=transaction_data,
            is_fraud=is_fraud,
            fraud_probability=fraud_prob,
            threshold=threshold,
            risk_level=risk.value,
            model_name=result["model_name"],
        )

    logger.info(
        f"[{transaction.transaction_id}] proba={fraud_prob:.3f} "
        f"risk={risk.value} ({elapsed_ms:.1f}ms)"
    )

    return PredictionResponse(
        transaction_id=transaction.transaction_id,
        fraud_probability=fraud_prob,
        is_fraud=is_fraud,
        risk_level=risk,
        threshold_used=threshold,
        model_name=result["model_name"],
        processing_time_ms=round(elapsed_ms, 2),
    )


def _compute_risk_level(probability: float) -> RiskLevel:
    """Convertit une probabilite en niveau de risque categoriel."""
    if probability >= 0.9:
        return RiskLevel.CRITIQUE
    if probability >= 0.7:
        return RiskLevel.ELEVE
    if probability >= 0.4:
        return RiskLevel.MOYEN
    return RiskLevel.FAIBLE
