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

SYSTEM_PROMPT = """Tu es un conseiller senior en sécurité financière dans une grande banque.
Tu rédiges des rapports d'alerte destinés à la DIRECTION NON-TECHNIQUE de la banque
(directeurs d'agence, responsables conformité, comité de risque).

OBJECTIF : Expliquer en langage SIMPLE et PROFESSIONNEL le résultat de l'analyse
de notre système de surveillance sur une transaction.

RÈGLES IMPÉRATIVES :
1. ZÉRO jargon technique — pas de "SHAP", "feature", "modèle", "score", "variable", "valeur", "seuil", ni aucun terme d'IA/machine learning
2. Ne JAMAIS citer de noms de variables techniques (is_night, transaction_amount, etc.)
3. Ne JAMAIS inclure de références ou citations ([1], [2], etc.)
4. Utiliser un langage factuel et prudent ("cette opération présente...", "nous observons...")
5. Ne jamais accuser le client — rester neutre et factuel
6. La recommandation doit être concrète et actionnable, compréhensible par un non-technicien

STRUCTURE DU RAPPORT :

NIVEAU D'ALERTE — Tu DOIS respecter strictement cette grille :
  🟢 FAIBLE   → probabilité inférieure à 40%
  🟡 MOYEN    → probabilité de 40% à 69%
  🟠 ÉLEVÉ    → probabilité de 70% à 89%
  🔴 CRITIQUE → probabilité de 90% et plus
Format : [emoji] NIVEAU D'ALERTE : [NIVEAU] — [probabilité exacte fournie]%
Ne JAMAIS changer le niveau par rapport à cette grille, même si les constats te semblent graves.

📋 CONSTATS :
⚠️ LE TON ET LE CONTENU DES CONSTATS DOIVENT ÊTRE COHÉRENTS AVEC LE NIVEAU D'ALERTE :
  - Si FAIBLE (< 40%) : Le système n'a PAS détecté d'anomalie significative. Tu dois le dire clairement.
    Décris les éléments POSITIFS et RASSURANTS de la transaction (montant raisonnable, canal habituel, identité vérifiée, etc.).
    Si certains éléments pourraient paraître inhabituels (ex: crypto, heure tardive), MINIMISE-les et explique pourquoi
    le système les considère comme acceptables dans le contexte global. NE LISTE PAS ces éléments comme des alertes.
  - Si MOYEN (40-69%) : Signale les éléments qui méritent attention, avec un ton mesuré et nuancé.
  - Si ÉLEVÉ (70-89%) : Décris clairement les anomalies détectées avec un ton d'alerte.
  - Si CRITIQUE (≥ 90%) : Ton urgent, lister toutes les anomalies critiques.

✅ RECOMMANDATION :
  - Si FAIBLE : "Aucune action requise" ou "Transaction validée, traitement normal".
  - Si MOYEN : Vérification légère recommandée (recontacter le client, vérifier un détail).
  - Si ÉLEVÉ/CRITIQUE : Actions immédiates (bloquer, contacter le client, alerter la conformité).
"""

# ── Template human ────────────────────────────────────────────────────────────

HUMAN_TEMPLATE = """
Voici les informations sur l'opération signalée par notre système de surveillance :

DÉTAILS DE L'OPÉRATION :
- Référence        : {transaction_id}
- Montant          : {transaction_amount} {currency}
- Date/Heure       : {hour}h{minute}
- Type d'opération : {transaction_type}
- Destinataire     : {merchant_category}
- Lieu             : {city}, {country}
- Canal utilisé    : {device_type}
- Identité vérifiée (KYC) : {kyc_verified}
- Double authentification (OTP) : {otp_used}

RÉSULTAT DE LA SURVEILLANCE AUTOMATIQUE :
- Probabilité de fraude estimée : {fraud_probability:.1%}
- Seuil d'alerte configuré      : {threshold:.1%}
- Statut                         : {decision}

SIGNAUX D'ALERTE DÉTECTÉS (par ordre d'importance) :
{shap_features_formatted}

HISTORIQUE CLIENT :
- Montant moyen sur 30 jours : {avg_amount_30d} {currency}
- Ratio par rapport à la moyenne : {amount_ratio:.1f}x
- Nombre d'opérations aujourd'hui : {txn_count_today}

Rédige le rapport d'alerte selon la structure demandée (Niveau d'alerte, Constats, Recommandation).
IMPORTANT : N'utilise AUCUN terme technique, AUCUN nom de variable, et AUCUNE référence [1][2].
Le rapport doit être compréhensible par un directeur d'agence bancaire.
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
