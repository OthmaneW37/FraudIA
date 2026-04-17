"""
batch.py — Endpoint /batch/upload : analyse en lot d'un fichier CSV.

Reçoit un fichier CSV de transactions → analyse chaque ligne → retourne un résumé.
"""

from __future__ import annotations

import csv
import io
import time
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from loguru import logger
from pydantic import BaseModel

from api.auth import get_current_user, save_transaction


router = APIRouter(prefix="/batch", tags=["Analyse en lot"])


def get_full_service():
    from api.main import full_service
    return full_service


class BatchResultItem(BaseModel):
    transaction_id: str
    fraud_probability: float
    risk_level: str
    is_fraud: bool
    model_name: str
    top_features: list = []
    error: str | None = None


class BatchResponse(BaseModel):
    total: int
    analyzed: int
    errors: int
    results: List[BatchResultItem]
    processing_time_ms: float


def _compute_risk_level(probability: float) -> str:
    if probability >= 0.9:
        return "CRITIQUE"
    elif probability >= 0.7:
        return "ELEVÉ"
    elif probability >= 0.4:
        return "MOYEN"
    else:
        return "FAIBLE"


# Mapping from CSV column names to expected field names
COLUMN_ALIASES = {
    "id": "transaction_id",
    "tx_id": "transaction_id",
    "amount": "transaction_amount",
    "montant": "transaction_amount",
    "heure": "hour",
    "type": "transaction_type",
    "categorie": "merchant_category",
    "category": "merchant_category",
    "ville": "city",
    "pays": "country",
    "device": "device_type",
    "kyc": "kyc_verified",
    "otp": "otp_used",
    "model": "selected_model",
    "modele": "selected_model",
}


def _normalize_row(row: dict) -> dict:
    """Normalize CSV column names and types."""
    normalized = {}
    for key, value in row.items():
        clean_key = key.strip().lower().replace(" ", "_")
        mapped_key = COLUMN_ALIASES.get(clean_key, clean_key)
        normalized[mapped_key] = value.strip() if isinstance(value, str) else value

    # Type conversions
    if "transaction_amount" in normalized:
        try:
            normalized["transaction_amount"] = float(normalized["transaction_amount"])
        except (ValueError, TypeError):
            normalized["transaction_amount"] = 0.0

    if "hour" in normalized:
        try:
            normalized["hour"] = int(normalized["hour"])
        except (ValueError, TypeError):
            normalized["hour"] = 12

    if "minute" not in normalized:
        normalized["minute"] = 0
    else:
        try:
            normalized["minute"] = int(normalized["minute"])
        except (ValueError, TypeError):
            normalized["minute"] = 0

    # Booleans
    for bool_field in ("kyc_verified", "otp_used"):
        if bool_field in normalized:
            v = str(normalized[bool_field]).lower()
            normalized[bool_field] = v in ("true", "1", "yes", "oui", "vrai")
        else:
            normalized[bool_field] = False

    # Defaults
    normalized.setdefault("currency", "MAD")
    normalized.setdefault("selected_model", "xgboost")
    normalized.setdefault("transaction_type", "purchase")
    normalized.setdefault("merchant_category", "general")
    normalized.setdefault("city", "Casablanca")
    normalized.setdefault("country", "Maroc")
    normalized.setdefault("device_type", "Desktop")

    if "transaction_id" not in normalized or not normalized["transaction_id"]:
        import uuid
        normalized["transaction_id"] = f"BATCH_{uuid.uuid4().hex[:8].upper()}"

    return normalized


@router.post("/upload", response_model=BatchResponse, summary="Analyser un fichier CSV")
def batch_upload(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    service=Depends(get_full_service),
):
    """Upload a CSV file and analyze each transaction."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers CSV sont acceptés.",
        )

    start = time.perf_counter()
    content = file.file.read()

    # Try to decode
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    # Parse CSV
    sample = text[:2048]
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample)
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    except csv.Error:
        reader = csv.DictReader(io.StringIO(text))

    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="Le fichier CSV est vide.")
    if len(rows) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 transactions par fichier.")

    results: list[BatchResultItem] = []
    errors_count = 0
    model_name = "xgboost"

    for row in rows:
        tx_data = _normalize_row(row)
        model_name = tx_data.get("selected_model", "xgboost")

        try:
            result = service.predict_and_shap(tx_data, model_name=model_name)
            fraud_prob = result["fraud_probability"]
            risk = _compute_risk_level(fraud_prob)
            is_fraud = fraud_prob >= result["threshold"]

            top_feats = result.get("top_features", [])[:5]

            item = BatchResultItem(
                transaction_id=tx_data["transaction_id"],
                fraud_probability=round(fraud_prob, 4),
                risk_level=risk,
                is_fraud=is_fraud,
                model_name=model_name,
                top_features=top_feats,
            )

            # Save to user's history
            import json
            save_transaction(user["id"], {
                "transaction_id": tx_data["transaction_id"],
                "fraud_probability": fraud_prob,
                "risk_level": risk,
                "is_fraud": is_fraud,
                "model_name": model_name,
                "form_data": tx_data,
                "result_data": {
                    "fraud_probability": fraud_prob,
                    "risk_level": risk,
                    "is_fraud": is_fraud,
                    "model_name": model_name,
                    "top_features": top_feats,
                    "threshold_used": result["threshold"],
                },
            })

        except Exception as e:
            logger.warning(f"Erreur batch [{tx_data.get('transaction_id', '?')}]: {e}")
            item = BatchResultItem(
                transaction_id=tx_data.get("transaction_id", "?"),
                fraud_probability=0,
                risk_level="ERREUR",
                is_fraud=False,
                model_name=model_name,
                error=str(e),
            )
            errors_count += 1

        results.append(item)

    elapsed_ms = (time.perf_counter() - start) * 1000

    return BatchResponse(
        total=len(rows),
        analyzed=len(rows) - errors_count,
        errors=errors_count,
        results=results,
        processing_time_ms=round(elapsed_ms, 2),
    )
