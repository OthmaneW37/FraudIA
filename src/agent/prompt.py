"""
prompt.py — Templates de prompts système pour l'agent LLM.

Architecture des prompts :
  SYSTEM PROMPT  : définit le rôle et le format de réponse attendu
  HUMAN TEMPLATE : payload structuré (transaction + SHAP)
  OUTPUT         : explication en langage naturel (FR ou EN)

Principes de prompt engineering appliqués :
  1. Rôle explicite       → "Tu es un analyste de fraude senior..."
  2. Format de sortie     → Structure JSON ou texte libre selon l'endpoint
  3. Contraintes métier   → Ne pas accuser, donner des raisons factuelles
  4. Contexte SHAP        → Valeurs normalisées + direction (+ fraude / - fraude)
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate


# ── Prompt système ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es un analyste senior en détection de fraude financière.
Tu travailles pour une banque et ton rôle est d'expliquer CLAIREMENT et FACTUELLEMENT
pourquoi une transaction a été signalée comme suspecte par le système d'IA.

RÈGLES IMPÉRATIVES :
1. Ne jamais accuser directement le client — utiliser un langage factuel ("la transaction présente...")
2. Baser ton analyse UNIQUEMENT sur les données fournies (valeurs SHAP + metadata)
3. Être concis : 3 à 5 phrases maximum
4. Mentionner les FEATURES les plus impactantes (SHAP value la plus haute)
5. Donner un niveau de risque : FAIBLE / MOYEN / ÉLEVÉ / CRITIQUE
6. Terminer par une recommandation actionnable (bloquer / surveiller / valider manuellement)

FORMAT DE RÉPONSE :
[NIVEAU DE RISQUE] : XX%
[MOTIFS PRINCIPAUX] : liste des raisons factuelles
[RECOMMANDATION] : action à prendre
"""

# ── Template human ────────────────────────────────────────────────────────────

HUMAN_TEMPLATE = """
=== TRANSACTION À ANALYSER ===
ID Transaction     : {transaction_id}
Montant            : {transaction_amount} {currency}
Heure              : {hour}h{minute}
Type               : {transaction_type}
Marchand           : {merchant_category}
Localisation       : {city}, {country}
Device             : {device_type}
Statut KYC         : {kyc_verified}
Vérification OTP   : {otp_used}

=== SCORE DE FRAUDE ===
Probabilité de fraude : {fraud_probability:.1%}
Seuil de décision     : {threshold:.1%}
Décision              : {decision}

=== FACTEURS EXPLICATIFS (SHAP) ===
Les features suivantes ont le plus influencé la décision,
ordonnées par impact décroissant :

{shap_features_formatted}

=== CONTEXTE HISTORIQUE (si disponible) ===
Moyenne montant client (30j)  : {avg_amount_30d} {currency}
Ratio montant/moyenne          : {amount_ratio:.1f}x
Nombre transactions aujourd'hui: {txn_count_today}

Rédige ton analyse selon le format demandé. Sois précis et factuel.
"""


# ── Fonctions utilitaires ─────────────────────────────────────────────────────

def format_shap_features(top_features: list[dict]) -> str:
    """
    Convertit la liste de top features SHAP en texte lisible pour le LLM.

    Input (depuis FraudExplainer.get_top_features()) :
        [{"feature": "amount", "shap_value": 0.82, "direction": "↑fraude", "impact": "fort"}, ...]

    Output :
        "1. amount          : +0.8200  [↑fraude] [fort]   → pousse vers FRAUDE
         2. device_type     : +0.4100  [↑fraude] [modéré] → pousse vers FRAUDE
         ..."
    """
    lines = []
    for i, feat in enumerate(top_features, 1):
        direction_txt = "pousse vers FRAUDE" if feat["direction"] == "↑fraude" else "pousse vers LÉGIT."
        sign = "+" if feat["shap_value"] > 0 else ""
        lines.append(
            f"{i:>2}. {feat['feature']:<25}: {sign}{feat['shap_value']:.4f}  "
            f"[{feat['direction']}] [{feat['impact']}]  → {direction_txt}"
        )
    return "\n".join(lines)


def build_fraud_prompt() -> ChatPromptTemplate:
    """
    Construit le ChatPromptTemplate LangChain complet.

    Returns
    -------
    ChatPromptTemplate prêt à être chainé avec un LLM.
    """
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
        HumanMessagePromptTemplate.from_template(HUMAN_TEMPLATE),
    ])


def build_transaction_payload(
    transaction: dict,
    fraud_probability: float,
    top_features: list[dict],
    threshold: float = 0.5,
) -> dict:
    """
    Construit le payload complet pour remplir le template de prompt.

    Parameters
    ----------
    transaction      : dict des données brutes de la transaction
    fraud_probability: score de fraude entre 0 et 1
    top_features     : sortie de FraudExplainer.get_top_features()
    threshold        : seuil de décision

    Returns
    -------
    dict prêt à injecter dans ChatPromptTemplate.format_messages()
    """
    decision = "🚨 BLOQUÉE" if fraud_probability >= threshold else "✅ AUTORISÉE"

    return {
        # Données transaction
        "transaction_id":    transaction.get("transaction_id", "TX_INCONNU"),
        "transaction_amount": transaction.get("transaction_amount", "N/A"),
        "currency":          transaction.get("currency", "MAD"),
        "hour":              transaction.get("hour", "N/A"),
        "minute":            transaction.get("minute", "00"),
        "transaction_type":  transaction.get("transaction_type", "N/A"),
        "merchant_category": transaction.get("merchant_category", "N/A"),
        "city":              transaction.get("city", "N/A"),
        "country":           transaction.get("country", "N/A"),
        "device_type":       transaction.get("device_type", "N/A"),
        "kyc_verified":      "Oui" if transaction.get("kyc_verified") else "Non",
        "otp_used":          "Oui" if transaction.get("otp_used") else "Non",
        # Scores
        "fraud_probability":        fraud_probability,
        "threshold":                threshold,
        "decision":                 decision,
        # SHAP
        "shap_features_formatted":  format_shap_features(top_features),
        # Historique (optionnel, valeur par défaut si absent)
        "avg_amount_30d":    transaction.get("avg_amount_30d", "N/A"),
        "amount_ratio":      transaction.get("transaction_amount", 0) / max(transaction.get("avg_amount_30d", 1), 1),
        "txn_count_today":   transaction.get("txn_count_today", "N/A"),
    }
