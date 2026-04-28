"""
auth_routes.py — Endpoints d'authentification.

  POST /auth/login        → Connexion (email + password) → JWT
  GET  /auth/me           → Profil de l'utilisateur connecté
  GET  /auth/transactions → Historique cloisonné par analyste
  POST /auth/transactions → Sauvegarder une transaction analysée
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, status

from api.auth import (
    LoginRequest,
    TokenResponse,
    TransactionRecord,
    UserInfo,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_user_analytics,
    get_user_transactions,
    delete_transaction,
    save_transaction,
    update_transaction,
)

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=TokenResponse, summary="Connexion analyste")
def login(req: LoginRequest):
    user = authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    token = create_access_token(user["id"])
    return TokenResponse(
        access_token=token,
        user=UserInfo(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
        ),
    )


@router.get("/me", response_model=UserInfo, summary="Profil utilisateur")
def get_me(user: dict = Depends(get_current_user)):
    return UserInfo(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
    )


@router.get("/transactions", summary="Historique des transactions (cloisonné)")
def list_transactions(user: dict = Depends(get_current_user)):
    return get_user_transactions(user["id"])


@router.get("/analytics", summary="Statistiques d'analyse (cloisonné)")
def analytics(user: dict = Depends(get_current_user)):
    return get_user_analytics(user["id"])


@router.post("/transactions", summary="Sauvegarder une transaction analysée")
def create_transaction(data: dict = Body(...), user: dict = Depends(get_current_user)):
    row_id = save_transaction(user["id"], data)
    return {"status": "saved", "id": row_id}


@router.put("/transactions/{row_id}", summary="Mettre à jour une transaction")
def put_transaction(row_id: str, data: dict = Body(...), user: dict = Depends(get_current_user)):
    update_transaction(user["id"], row_id, data)
    
    # ── HITL : si une annotation est soumise, enregistrer le feedback ────────
    annotation = data.get("annotation")
    if annotation in ("frauduleuse", "valide"):
        try:
            import sqlite3
            from pathlib import Path
            db_path = Path(__file__).resolve().parent.parent.parent / "users.db"
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM transactions WHERE id = ?", (row_id,)).fetchone()
            conn.close()
            if row:
                from api.hitl import extract_feedback_from_annotation
                success = extract_feedback_from_annotation(
                    db_row=dict(row),
                    annotation=annotation,
                    analyst_id=user["id"],
                )
                if not success:
                    logger.warning(f"[HITL] Feedback non enregistré pour {row.get('transaction_id', row_id)} — form_data invalide ou absent")
            else:
                logger.warning(f"[HITL] Transaction {row_id} introuvable en base")
        except Exception as exc:
            logger.error(f"[HITL] Erreur critique d'enregistrement du feedback : {exc}", exc_info=True)
    
    return {"status": "updated"}


@router.delete("/transactions/{row_id}", summary="Supprimer une transaction")
def remove_transaction(row_id: str, user: dict = Depends(get_current_user)):
    delete_transaction(user["id"], row_id)
    return {"status": "deleted"}


@router.get("/admin/users", summary="Admin: Liste des analystes")
def admin_list_users(user: dict = Depends(get_current_user)):
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Accès refusé.")
    from api.auth import get_all_analysts
    return get_all_analysts()


@router.post("/admin/users/{analyst_id}/grade", summary="Admin: Noter un analyste")
def admin_grade_user(analyst_id: str, data: dict = Body(...), user: dict = Depends(get_current_user)):
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Accès refusé.")
    
    rating = data.get("rating")
    comment = data.get("admin_comment", "")
    if rating is None:
        raise HTTPException(status_code=400, detail="La note est requise.")
        
    from api.auth import update_analyst_rating
    update_analyst_rating(analyst_id, float(rating), comment)
    return {"status": "success"}
