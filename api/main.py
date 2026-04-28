"""
main.py - Point d'entree FastAPI.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from api.routes import auth_routes, explain, predict
from api.routes import batch as batch_routes
from api.routes import hitl_routes
from api.schemas import HealthResponse

load_dotenv()

model_service = None
full_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application."""
    global model_service, full_service

    logger.info("Demarrage de l'API Fraud Detection...")

    from api.auth import init_db

    init_db()

    try:
        from api.services import FullService, ModelService

        model_service = ModelService.load_default()
        full_service = FullService(model_service=model_service)
        app.state.model_service = model_service
        app.state.full_service = full_service
        logger.success("Services charges")
    except Exception as exc:
        model_service = None
        full_service = None
        app.state.model_service = None
        app.state.full_service = None
        logger.warning(f"Impossible de charger les services : {exc}")
        logger.warning("L'API demarre en mode degrade (modele non charge).")

    yield

    logger.info("Arret de l'API Fraud Detection.")


app = FastAPI(
    title="Fraud Detection API",
    description=(
        "API de detection et d'explication de fraude financiere.\n\n"
        "Stack : XGBoost · SHAP · LLM\n\n"
        "Projet PFA - EMSI 4eme annee IA & Data"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Erreur de validation sur {request.url.path} : {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(predict.router)
app.include_router(explain.router)
app.include_router(batch_routes.router)
app.include_router(hitl_routes.router)


@app.get("/", tags=["Root"], summary="Bienvenue")
async def root():
    return {
        "message": "Fraud Detection API operationnelle",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
async def health_check() -> HealthResponse:
    """Vérifie l'état de l'API, du modèle ML et du LLM."""
    model_loaded = model_service is not None
    llm_online = False

    if full_service is not None:
        try:
            llm_online = full_service.agent.health_check()
        except Exception:
            llm_online = False

    overall_status = (
        "healthy"
        if model_loaded and llm_online
        else "degraded"
        if model_loaded or llm_online
        else "unhealthy"
    )

    # Charger les métriques réelles depuis models/metrics.json
    import json
    from pathlib import Path
    metrics_path = Path(__file__).resolve().parent.parent / "models" / "metrics.json"
    try:
        with metrics_path.open("r", encoding="utf-8") as f:
            saved = json.load(f)
        model_metrics = {
            "auc_pr": saved.get("auc_pr", 0),
            "f1": saved.get("f1", 0),
            "precision_fraud": saved.get("precision_fraud", 0),
            "recall_fraud": saved.get("recall_fraud", 0),
            "n_features": saved.get("n_features", 27),
            "training_samples": saved.get("training_samples", 0),
            "best_model": saved.get("best_model", "xgboost"),
        }
    except Exception:
        model_metrics = None if not model_loaded else {
            "auc_pr": 0,
            "f1": 0,
            "precision_fraud": 0,
            "recall_fraud": 0,
            "n_features": 27,
            "training_samples": 0,
            "best_model": "xgboost",
        }

    return HealthResponse(
        status=overall_status,
        model_loaded=model_loaded,
        llm_online=llm_online,
        model_metrics=model_metrics,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
