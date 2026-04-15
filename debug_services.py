import sys
from pathlib import Path
import numpy as np
import pandas as pd
from loguru import logger

# Ajouter le projet au path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from api.services import ModelService, FullService
from src.data.preprocessor import FraudPreprocessor
from src.models.trainer import ModelTrainer

def debug():
    try:
        logger.info("Tentative de chargement des services...")
        model_service = ModelService.load_default()
        full_service = FullService(model_service=model_service)
        logger.success("Services chargés !")

        tx = {
            "transaction_id": "DEBUG",
            "transaction_amount": 1000.0,
            "currency": "MAD",
            "hour": 10,
            "minute": 0,
            "transaction_type": "transfer",
            "merchant_category": "test",
            "city": "test",
            "country": "test",
            "device_type": "test",
            "kyc_verified": True,
            "otp_used": True
        }

        logger.info("Test predict_and_explain avec Random Forest...")
        res = full_service.predict_and_explain(tx, model_name="random_forest")
        logger.success(f"Résultat RF : {res['fraud_probability']}")
        
    except Exception as e:
        logger.exception(f"Erreur détectée : {e}")

if __name__ == "__main__":
    debug()
