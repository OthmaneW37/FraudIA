"""
hitl_routes.py — Endpoints de la boucle Human-in-the-Loop.

  GET  /hitl/status    → État du pipeline HITL (stats annotations, dernier retrain)
  POST /hitl/retrain   → Déclenche le fine-tuning incrémental (superadmin only)
  GET  /hitl/history   → Historique des cycles de retrain
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import get_current_user

router = APIRouter(prefix="/hitl", tags=["Human-in-the-Loop"])


@router.get("/status", summary="État du pipeline HITL")
def hitl_status(user: dict = Depends(get_current_user)):
    """Retourne les statistiques HITL : feedbacks collectés, en attente, historique."""
    from api.hitl import get_hitl_stats
    return get_hitl_stats()


@router.post("/retrain", summary="Déclencher le fine-tuning (superadmin)")
def hitl_retrain(request: Request, user: dict = Depends(get_current_user)):
    """
    Déclenche un fine-tuning incrémental XGBoost sur les feedbacks humains en attente.
    Réservé au superadmin. Recharge le modèle à chaud dans le service API.
    """
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Accès réservé au superadmin.")

    from api.hitl import incremental_retrain

    app_state = request.app.state
    result = incremental_retrain(model_name="xgboost", app_state=app_state)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/history", summary="Historique des cycles de fine-tuning")
def hitl_history(user: dict = Depends(get_current_user)):
    """Retourne l'historique complet des cycles de fine-tuning HITL."""
    from api.hitl import _load_history
    return _load_history()
