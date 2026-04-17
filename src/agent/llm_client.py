"""
llm_client.py — Intégration LangChain + Perplexity API (LLM cloud).

Pourquoi Perplexity ?
  → API rapide et fiable (sonar / sonar-pro)
  → Compatible OpenAI (même format de requêtes)
  → Pas besoin de GPU local ni d'Ollama

Architecture de la chaîne LangChain :
  prompt_template | llm | output_parser
  → Chaînage LCEL (LangChain Expression Language) : pythonique et composable
"""

from __future__ import annotations

import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSequence
from loguru import logger

from src.agent.prompt import build_fraud_prompt, build_transaction_payload

load_dotenv()

# ── Constantes ──────────────────────────────────────────────────────────────

DEFAULT_API_KEY      = os.getenv("PERPLEXITY_API_KEY", "")
DEFAULT_MODEL        = os.getenv("PERPLEXITY_MODEL", "sonar")
DEFAULT_BASE_URL     = os.getenv("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")
DEFAULT_TEMPERATURE  = 0.1   # Faible → réponses déterministes et factuelles
DEFAULT_TOP_P        = 0.9
DEFAULT_MAX_TOKENS   = 512


# ── Classe principale ────────────────────────────────────────────────────────

class FraudAgent:
    """
    Agent LLM pour générer des explications de fraude en langage naturel.

    Flux complet :
      transaction + shap_values
        → build_transaction_payload()
        → prompt_template
        → Perplexity API (sonar / sonar-pro)
        → texte d'explication

    Usage :
        agent = FraudAgent()
        explanation = agent.explain(transaction, fraud_proba, top_features)
        print(explanation)
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str = DEFAULT_API_KEY,
        base_url: str = DEFAULT_BASE_URL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens

        self._chain: RunnableSequence | None = None
        self._build_chain()

    # ── Initialisation ────────────────────────────────────────────────────────

    def _build_chain(self) -> None:
        """
        Construit la chaîne LCEL :
          prompt | llm | output_parser

        LCEL (LangChain Expression Language) permet de chaîner les composants
        avec l'opérateur | de manière lisible et composable.
        """
        logger.info(f"Initialisation Perplexity — modèle: {self.model} @ {self.base_url}")

        llm = ChatOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=60,
        )

        prompt = build_fraud_prompt()
        parser = StrOutputParser()

        self._chain = prompt | llm | parser
        logger.success("Agent LLM Perplexity prêt ✓")

    # ── API publique ──────────────────────────────────────────────────────────

    def explain(
        self,
        transaction: dict,
        fraud_probability: float,
        top_features: list[dict],
        threshold: float = 0.5,
    ) -> str:
        """
        Génère une explication en langage naturel pour une transaction.

        Parameters
        ----------
        transaction       : dict avec les métadonnées brutes
        fraud_probability : score de fraude entre 0 et 1
        top_features      : sortie de FraudExplainer.get_top_features()
        threshold         : seuil de decision

        Returns
        -------
        str : explication en langage naturel (3-5 phrases)

        Raises
        ------
        RuntimeError si Ollama n'est pas accessible
        """
        if self._chain is None:
            raise RuntimeError("La chaîne LLM n'est pas initialisée.")

        payload = build_transaction_payload(
            transaction=transaction,
            fraud_probability=fraud_probability,
            top_features=top_features,
            threshold=threshold,
        )

        logger.info(f"Génération d'explication LLM pour TX: {transaction.get('transaction_id', '?')}")

        try:
            response = self._chain.invoke(payload)
            logger.success("Explication LLM générée ✓")
            return response

        except Exception as e:
            logger.error(f"Erreur LLM : {e}")
            # Fallback : explication basée sur les règles (sans LLM)
            return self._rule_based_fallback(transaction, fraud_probability, top_features)

    def health_check(self) -> bool:
        """
        Vérifie rapidement que l'API Perplexity est accessible.

        Important: on évite toute invocation LLM ici pour ne pas bloquer
        l'event loop FastAPI dans /health.
        """
        try:
            # Simple test: envoyer un HEAD/GET vers l'API base URL
            response = httpx.get(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=3.0,
            )
            # Perplexity retourne 405 (Method Not Allowed pour GET) ou 200/401
            # Si on a un code != connection error, l'API est accessible
            return response.status_code in (200, 405, 422)
        except Exception as e:
            logger.warning(f"Perplexity API inaccessible : {e}")
            return False

    # ── Fallback sans LLM ─────────────────────────────────────────────────────

    @staticmethod
    def _rule_based_fallback(
        transaction: dict,
        fraud_probability: float,
        top_features: list[dict],
    ) -> str:
        """
        Génère une explication basée sur des règles si Ollama est indisponible.
        Garantit que l'API reste fonctionnelle même sans LLM.
        """
        risk_level = (
            "CRITIQUE" if fraud_probability >= 0.9
            else "ÉLEVÉ" if fraud_probability >= 0.7
            else "MOYEN" if fraud_probability >= 0.4
            else "FAIBLE"
        )

        top_names = [f["feature"] for f in top_features[:3]]
        motifs = ", ".join(top_names) if top_names else "comportement inhabituel"

        return (
            f"[NIVEAU DE RISQUE] : {risk_level} ({fraud_probability:.1%})\n"
            f"[MOTIFS PRINCIPAUX] : La transaction présente des anomalies sur les indicateurs suivants : {motifs}.\n"
            f"[RECOMMANDATION] : {'Bloquer la transaction et contacter le client.' if fraud_probability > 0.7 else 'Surveiller et valider manuellement.'}\n"
            f"\n⚠️ Note : Explication générée par règles (LLM indisponible)."
        )
