"""
auth.py - Authentification JWT + gestion des utilisateurs (SQLite).

Architecture :
  - SQLite local (users.db) pour stocker les comptes analystes
  - Mots de passe hashes avec bcrypt
  - JWT (JSON Web Token) pour les sessions
  - Cloisonnement des donnees : chaque analyste a ses propres transactions
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger
from pydantic import BaseModel


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fraudia-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 12

DB_PATH = Path(__file__).parent.parent / "users.db"

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


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
    form_data: Optional[str] = None


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Cree les tables si elles n'existent pas et insere les utilisateurs par defaut."""
    conn = _get_db()
    try:
        conn.executescript(
            """
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
            """
        )

        default_users = [
            ("Rayane Ramzi", "rayane.ramzi24@gmail.com", "password"),
            ("Othmane Moussawi", "othmanemoussawi@gmail.com", "password"),
        ]

        for name, email, password in default_users:
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                continue

            user_id = str(uuid.uuid4())
            password_hash = _hash_password(password)
            conn.execute(
                "INSERT INTO users (id, email, full_name, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                (user_id, email, name, password_hash, "analyst"),
            )
            logger.info(f"Utilisateur cree : {email}")

        conn.commit()

        try:
            conn.execute("SELECT annotation FROM transactions LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE transactions ADD COLUMN annotation TEXT DEFAULT NULL")
            conn.commit()
            logger.info("Migration : colonne 'annotation' ajoutee a transactions")

        logger.success("Base de donnees auth initialisee")
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Verifie les identifiants et retourne l'utilisateur ou None."""
    conn = _get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row and _verify_password(password, row["password_hash"]):
            return dict(row)
        return None
    finally:
        conn.close()


def create_access_token(user_id: str) -> str:
    """Cree un JWT avec expiration."""
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _get_user_from_token(token: str) -> Optional[dict]:
    """Retourne l'utilisateur associe au token JWT, ou None si le token est invalide."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    conn = _get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependance FastAPI : extrait et valide le token JWT."""
    user = _get_user_from_token(credentials.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Token invalide ou expire")
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
) -> Optional[dict]:
    """Retourne l'utilisateur connecte si le token est present et valide, sinon None."""
    if credentials is None:
        return None

    user = _get_user_from_token(credentials.credentials)
    if user is None:
        logger.warning("Token optionnel invalide recu sur un endpoint public.")
    return user


def save_transaction(user_id: str, data: dict) -> str:
    """Enregistre une transaction analysee pour un utilisateur. Retourne l'id."""
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


def update_transaction(user_id: str, row_id: str, data: dict) -> None:
    """Met a jour une transaction existante (ex: ajout de l'explication LLM)."""
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


def delete_transaction(user_id: str, row_id: str) -> None:
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
    """Recupere les transactions (toutes si superadmin, sinon celles de l'analyste)."""
    conn = _get_db()
    try:
        user_row = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
        is_superadmin = user_row and user_row["role"] == "superadmin"

        if is_superadmin:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_user_analytics(user_id: str) -> dict:
    """Agrege les statistiques d'analyse pour le dashboard analytique."""
    import json
    from collections import Counter, defaultdict

    conn = _get_db()
    try:
        user_row = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
        is_superadmin = user_row and user_row["role"] == "superadmin"

        if is_superadmin:
             rows = conn.execute(
                 "SELECT * FROM transactions ORDER BY created_at DESC"
             ).fetchall()
        else:
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

    risk_counts = Counter(t["risk_level"] for t in txs)
    risk_distribution = [{"name": k, "value": v} for k, v in risk_counts.items()]

    feature_fraud_freq = Counter()
    for tx in txs:
        result_data = tx.get("result_data")
        if not result_data or result_data == "{}":
            continue
        try:
            result = json.loads(result_data) if isinstance(result_data, str) else result_data
        except (json.JSONDecodeError, TypeError):
            continue
        for feature in result.get("top_features", []):
            feature_name = feature.get("feature", "")
            if not feature_name:
                continue
            if tx["risk_level"] in ("MOYEN", "ELEVÉ", "ÉLEVÉ", "CRITIQUE"):
                feature_fraud_freq[feature_name] += abs(feature.get("shap_value", 0))

    top_fraud_features = [
        {"feature": key, "total_impact": round(value, 3)}
        for key, value in feature_fraud_freq.most_common(8)
    ]

    type_counts = Counter()
    type_fraud = Counter()
    for tx in txs:
        form_data = tx.get("form_data")
        if not form_data:
            continue
        try:
            form = json.loads(form_data) if isinstance(form_data, str) else form_data
        except (json.JSONDecodeError, TypeError):
            continue
        tx_type = form.get("transaction_type", "inconnu")
        type_counts[tx_type] += 1
        if tx["risk_level"] in ("MOYEN", "ELEVÉ", "ÉLEVÉ", "CRITIQUE"):
            type_fraud[tx_type] += 1

    by_type = [
        {"type": key, "total": type_counts[key], "risky": type_fraud.get(key, 0)}
        for key in type_counts
    ]

    category_counts = Counter()
    category_fraud = Counter()
    for tx in txs:
        form_data = tx.get("form_data")
        if not form_data:
            continue
        try:
            form = json.loads(form_data) if isinstance(form_data, str) else form_data
        except (json.JSONDecodeError, TypeError):
            continue
        category = form.get("merchant_category", "inconnu")
        category_counts[category] += 1
        if tx["risk_level"] in ("MOYEN", "ELEVÉ", "ÉLEVÉ", "CRITIQUE"):
            category_fraud[category] += 1

    by_category = [
        {"category": key, "total": category_counts[key], "risky": category_fraud.get(key, 0)}
        for key in category_counts
    ]

    hour_counts = defaultdict(lambda: {"total": 0, "risky": 0})
    for tx in txs:
        form_data = tx.get("form_data")
        if not form_data:
            continue
        try:
            form = json.loads(form_data) if isinstance(form_data, str) else form_data
        except (json.JSONDecodeError, TypeError):
            continue
        hour = int(form.get("hour", 0))
        hour_counts[hour]["total"] += 1
        if tx["risk_level"] in ("MOYEN", "ELEVÉ", "ÉLEVÉ", "CRITIQUE"):
            hour_counts[hour]["risky"] += 1

    by_hour = [
        {"hour": hour, "total": values["total"], "risky": values["risky"]}
        for hour, values in sorted(hour_counts.items())
    ]

    score_timeline = [
        {
            "date": tx["created_at"][:16],
            "score": round(tx["fraud_probability"] * 100, 1),
            "risk": tx["risk_level"],
            "tx_id": tx["transaction_id"],
        }
        for tx in reversed(txs)
    ]

    avg_score = sum(tx["fraud_probability"] for tx in txs) / total
    high_risk_count = sum(
        1 for tx in txs if tx["risk_level"] in ("ELEVÉ", "ÉLEVÉ", "CRITIQUE")
    )

    by_analyst = []
    if is_superadmin:
        analyst_counts = Counter()
        for tx in txs:
            # We need to get the name of the analyst.
            # In a real app we might join, but here we can just use the user_id
            # or better, just get all users mapping.
            analyst_counts[tx.get("user_id", "inconnu")] += 1
        
        # Get mapping of UserID -> Name
        conn = _get_db()
        users_rows = conn.execute("SELECT id, full_name FROM users").fetchall()
        user_map = {r["id"]: r["full_name"] for r in users_rows}
        conn.close()

        by_analyst = [
            {"name": user_map.get(uid, uid), "count": count}
            for uid, count in analyst_counts.items()
        ]

    return {
        "total": total,
        "avg_score": round(avg_score * 100, 1),
        "high_risk_count": high_risk_count,
        "risk_distribution": risk_distribution,
        "top_fraud_features": top_fraud_features,
        "by_type": by_type,
        "by_category": by_category,
        "by_hour": by_hour,
        "by_analyst": by_analyst,
        "score_timeline": score_timeline,
    }


def get_all_analysts() -> list[dict]:
    """Recupere la liste des analystes avec leurs statistiques pour le superadmin."""
    conn = _get_db()
    try:
        query = """
        SELECT u.id, u.email, u.full_name, u.rating, u.admin_comment,
               (SELECT COUNT(*) FROM transactions t WHERE t.user_id = u.id) as tx_count,
               (SELECT AVG(fraud_probability) FROM transactions t WHERE t.user_id = u.id) as avg_score
        FROM users u
        WHERE u.role = 'analyst'
        """
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_analyst_rating(user_id: str, rating: float, comment: str) -> None:
    """Met a jour la note et le commentaire de l'admin pour un analyste."""
    conn = _get_db()
    try:
        conn.execute(
            "UPDATE users SET rating = ?, admin_comment = ? WHERE id = ?",
            (rating, comment, user_id)
        )
        conn.commit()
    finally:
        conn.close()
