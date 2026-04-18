"""
main.py — Point d'entrée FastAPI.

Initialise l'application, monte les routers et gère le cycle de vie (lifespan).

Endpoints exposés :
  GET  /health             → Vérification état de l'API + modèle + LLM
  POST /predict/           → Score de fraude (rapide, sans LLM)
  POST /explain/           → Score + explication LLM (complet)
  GET  /docs               → Swagger UI auto-généré
  GET  /redoc              → ReDoc auto-généré
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api.routes import explain, predict
from api.routes import auth_routes
from api.routes import batch as batch_routes
from api.schemas import HealthResponse

load_dotenv()

# ── Placeholders des services (injectés au démarrage) ────────────────────────
# Ces variables seront initialisées dans le lifespan startup
model_service = None
full_service  = None


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestion du cycle de vie de l'application.

    Pourquoi lifespan et pas @app.on_event("startup") ?
    → on_event est déprécié depuis FastAPI 0.93.
      Le lifespan est l'approche moderne et recommandée.
    """
    # ── STARTUP ──
    global model_service, full_service
    logger.info("Démarrage de l'API Fraude Detection...")

    # Initialiser la base de données auth
    from api.auth import init_db
    init_db()

    try:
        from api.services import FullService, ModelService

        model_service = ModelService.load_default()
        full_service  = FullService(model_service=model_service)
        logger.success("Services chargés ✓")
    except Exception as e:
        logger.warning(f"Impossible de charger les services : {e}")
        logger.warning("→ L'API démarre en mode dégradé (modèle non chargé)")

    yield  # L'application tourne ici

    # ── SHUTDOWN ──
    logger.info("Arrêt de l'API Fraude Detection.")


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="🔍 Fraud Detection API",
    description=(
        "API de détection et d'explication de fraude financière.\n\n"
        "**Stack** : XGBoost · SHAP · LangChain · Ollama (LLM local)\n\n"
        "**Projet PFA** — EMSI 4ème année IA & Data"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — autorise Streamlit (8501) et le futur React (5173) à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monter les routers
app.include_router(auth_routes.router)
app.include_router(predict.router)
app.include_router(explain.router)
app.include_router(batch_routes.router)


# ── Endpoints racine ──────────────────────────────────────────────────────────

@app.get("/", tags=["Root"], summary="Bienvenue")
async def root():
    return {
        "message": "🔍 Fraud Detection API — opérationnelle",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
async def health_check() -> HealthResponse:
    """
    Vérifie l'état de l'API, du modèle ML et du LLM.
    Utilisé par le dashboard Streamlit pour l'indicateur de statut.
    """
    model_loaded = model_service is not None
    llm_online = False

    if full_service:
        try:
            llm_online = full_service.agent.health_check()
        except Exception:
            llm_online = False

    overall_status = (
        "healthy"   if model_loaded and llm_online
        else "degraded"   if model_loaded or llm_online
        else "unhealthy"
    )

    # Métriques de performance du modèle Champion (XGBoost v2 + Sequential Features + Optuna)
    # Calculées sur le Test Set (150k transactions, jamais vues à l'entraînement)
    model_metrics = {
        "accuracy":      0.91,    # 91% d'accuracy globale
        "auc_pr":        0.31,    # AUC-PR sur Test Set (Precision-Recall, métrique principale fraude)
        "f1_macro":      0.49,    # F1-Score Macro
        "precision_fraud": 0.30,  # Précision sur la classe Fraude
        "recall_fraud":  0.01,    # Recall sur la classe Fraude (seuil 80%)
        "version":       "v2.0 (Optuna + Sequential Features)",
        "training_samples": 700000,  # Lignes d'entraînement (après SMOTE)
        "n_features":    27,
    } if model_loaded else None

    return HealthResponse(
        status=overall_status,
        model_loaded=model_loaded,
        llm_online=llm_online,
        model_metrics=model_metrics,
    )



# ── Lancement direct ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
