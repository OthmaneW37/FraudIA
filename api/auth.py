"""
auth.py — Authentification JWT + gestion des utilisateurs (SQLite).

Architecture :
  - SQLite local (users.db) pour stocker les comptes analystes
  - Mots de passe hashés avec bcrypt
  - JWT (JSON Web Token) pour les sessions
  - Cloisonnement des données : chaque analyste a ses propres transactions
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────────

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fraudia-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 12

DB_PATH = Path(__file__).parent.parent / "users.db"

security = HTTPBearer()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BaseModel):
    id: str
    email: str
    full_name: str
    role: str


class TransactionRecord(BaseModel):
    id: Optional[str] = None
    transaction_id: str
    fraud_probability: float
    risk_level: str
    is_fraud: bool
    model_name: str
    created_at: Optional[str] = None
    form_data: Optional[str] = None  # JSON string


# ── Database ──────────────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Crée les tables si elles n'existent pas et insère les utilisateurs par défaut."""
    conn = _get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'analyst',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                fraud_probability REAL NOT NULL,
                risk_level TEXT NOT NULL,
                is_fraud INTEGER NOT NULL DEFAULT 0,
                model_name TEXT NOT NULL DEFAULT 'xgboost',
                form_data TEXT,
                explanation TEXT,
                result_data TEXT,
                annotation TEXT DEFAULT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
        """)

        # Insérer les analystes par défaut (la banque fournit les comptes)
        default_users = [
            ("Othmane Wari", "othmane@fraudia.ma", "analyst123"),
            ("Sara Bennani", "sara@fraudia.ma", "analyst123"),
            ("Youssef Alami", "youssef@fraudia.ma", "analyst123"),
            ("Rayane Ramzi", "rayane.ramzi24@gmail.com", "password"),
            ("Othmane Moussawi", "othmanemoussawi@gmail.com", "password"),
        ]

        for name, email, password in default_users:
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if not existing:
                user_id = str(uuid.uuid4())
                password_hash = _hash_password(password)
                conn.execute(
                    "INSERT INTO users (id, email, full_name, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                    (user_id, email, name, password_hash, "analyst"),
                )
                logger.info(f"Utilisateur créé : {email}")

        conn.commit()
        
        # Migration : ajouter la colonne annotation si elle n'existe pas
        try:
            conn.execute("SELECT annotation FROM transactions LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE transactions ADD COLUMN annotation TEXT DEFAULT NULL")
            conn.commit()
            logger.info("Migration : colonne 'annotation' ajoutée à transactions")
        
        logger.success("Base de données auth initialisée ✓")
    finally:
        conn.close()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Vérifie les identifiants et retourne l'utilisateur ou None."""
    conn = _get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row and _verify_password(password, row["password_hash"]):
            return dict(row)
        return None
    finally:
        conn.close()


def create_access_token(user_id: str) -> str:
    """Crée un JWT avec expiration."""
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dépendance FastAPI : extrait et valide le token JWT."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token invalide")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

    conn = _get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="Utilisateur introuvable")
        return dict(row)
    finally:
        conn.close()


# ── Transaction history (cloisonné par utilisateur) ───────────────────────────

def save_transaction(user_id: str, data: dict) -> str:
    """Enregistre une transaction analysée pour un utilisateur. Retourne l'id."""
    import json
    row_id = str(uuid.uuid4())
    conn = _get_db()
    try:
        conn.execute(
            """INSERT INTO transactions (id, user_id, transaction_id, fraud_probability, risk_level, is_fraud, model_name, form_data, explanation, result_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row_id,
                user_id,
                data.get("transaction_id", ""),
                data.get("fraud_probability", 0),
                data.get("risk_level", ""),
                1 if data.get("is_fraud") else 0,
                data.get("model_name", "xgboost"),
                json.dumps(data.get("form_data", {}), ensure_ascii=False),
                data.get("explanation", ""),
                json.dumps(data.get("result_data", {}), ensure_ascii=False),
            ),
        )
        conn.commit()
        return row_id
    finally:
        conn.close()


def update_transaction(user_id: str, row_id: str, data: dict):
    """Met à jour une transaction existante (ex: ajout de l'explication LLM)."""
    import json
    conn = _get_db()
    try:
        sets, vals = [], []
        if "explanation" in data:
            sets.append("explanation = ?")
            vals.append(data["explanation"])
        if "result_data" in data:
            sets.append("result_data = ?")
            vals.append(json.dumps(data["result_data"], ensure_ascii=False))
        if "annotation" in data:
            sets.append("annotation = ?")
            vals.append(data["annotation"])
        if not sets:
            return
        vals.extend([row_id, user_id])
        conn.execute(
            f"UPDATE transactions SET {', '.join(sets)} WHERE id = ? AND user_id = ?",
            vals,
        )
        conn.commit()
    finally:
        conn.close()


def delete_transaction(user_id: str, row_id: str):
    """Supprime une transaction (cloisonnement par user_id)."""
    conn = _get_db()
    try:
        conn.execute(
            "DELETE FROM transactions WHERE id = ? AND user_id = ?",
            (row_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_user_transactions(user_id: str, limit: int = 50) -> list[dict]:
    """Récupère les transactions d'un analyste (cloisonnement)."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_user_analytics(user_id: str) -> dict:
    """Agrège les statistiques d'analyse pour le dashboard analytique."""
    import json
    from collections import Counter, defaultdict

    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        txs = [dict(r) for r in rows]
    finally:
        conn.close()

    total = len(txs)
    if total == 0:
        return {"total": 0}

    # 1. Répartition par niveau de risque (pie chart)
    risk_counts = Counter(t["risk_level"] for t in txs)
    risk_distribution = [{"name": k, "value": v} for k, v in risk_counts.items()]

    # 2. Top features les plus fréquentes dans les transactions à risque (MOYEN+)
    feature_fraud_freq = Counter()
    feature_all_freq = Counter()
    for t in txs:
        rd = t.get("result_data")
        if not rd or rd == "{}":
            continue
        try:
            result = json.loads(rd) if isinstance(rd, str) else rd
        except (json.JSONDecodeError, TypeError):
            continue
        features = result.get("top_features", [])
        for f in features:
            fname = f.get("feature", "")
            if not fname:
                continue
            feature_all_freq[fname] += abs(f.get("shap_value", 0))
            if t["risk_level"] in ("MOYEN", "ÉLEVÉ", "ELEVÉ", "CRITIQUE"):
                feature_fraud_freq[fname] += abs(f.get("shap_value", 0))

    top_fraud_features = [
        {"feature": k, "total_impact": round(v, 3)}
        for k, v in feature_fraud_freq.most_common(8)
    ]

    # 3. Distribution par type de transaction
    type_counts = Counter()
    type_fraud = Counter()
    for t in txs:
        fd = t.get("form_data")
        if not fd:
            continue
        try:
            form = json.loads(fd) if isinstance(fd, str) else fd
        except (json.JSONDecodeError, TypeError):
            continue
        tt = form.get("transaction_type", "inconnu")
        type_counts[tt] += 1
        if t["risk_level"] in ("MOYEN", "ÉLEVÉ", "ELEVÉ", "CRITIQUE"):
            type_fraud[tt] += 1

    by_type = [
        {"type": k, "total": type_counts[k], "risky": type_fraud.get(k, 0)}
        for k in type_counts
    ]

    # 4. Distribution par catégorie marchand
    cat_counts = Counter()
    cat_fraud = Counter()
    for t in txs:
        fd = t.get("form_data")
        if not fd:
            continue
        try:
            form = json.loads(fd) if isinstance(fd, str) else fd
        except (json.JSONDecodeError, TypeError):
            continue
        mc = form.get("merchant_category", "inconnu")
        cat_counts[mc] += 1
        if t["risk_level"] in ("MOYEN", "ÉLEVÉ", "ELEVÉ", "CRITIQUE"):
            cat_fraud[mc] += 1

    by_category = [
        {"category": k, "total": cat_counts[k], "risky": cat_fraud.get(k, 0)}
        for k in cat_counts
    ]

    # 5. Distribution horaire
    hour_counts = defaultdict(lambda: {"total": 0, "risky": 0})
    for t in txs:
        fd = t.get("form_data")
        if not fd:
            continue
        try:
            form = json.loads(fd) if isinstance(fd, str) else fd
        except (json.JSONDecodeError, TypeError):
            continue
        h = int(form.get("hour", 0))
        hour_counts[h]["total"] += 1
        if t["risk_level"] in ("MOYEN", "ÉLEVÉ", "ELEVÉ", "CRITIQUE"):
            hour_counts[h]["risky"] += 1

    by_hour = [
        {"hour": h, "total": v["total"], "risky": v["risky"]}
        for h, v in sorted(hour_counts.items())
    ]

    # 6. Évolution temporelle des scores
    score_timeline = [
        {
            "date": t["created_at"][:16],
            "score": round(t["fraud_probability"] * 100, 1),
            "risk": t["risk_level"],
            "tx_id": t["transaction_id"],
        }
        for t in reversed(txs)
    ]

    # 7. Stats KPIs
    avg_score = sum(t["fraud_probability"] for t in txs) / total
    high_risk_count = sum(1 for t in txs if t["risk_level"] in ("ÉLEVÉ", "ELEVÉ", "CRITIQUE"))

    return {
        "total": total,
        "avg_score": round(avg_score * 100, 1),
        "high_risk_count": high_risk_count,
        "risk_distribution": risk_distribution,
        "top_fraud_features": top_fraud_features,
        "by_type": by_type,
        "by_category": by_category,
        "by_hour": by_hour,
        "score_timeline": score_timeline,
    }
