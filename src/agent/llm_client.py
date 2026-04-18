"""
llm_client.py — Intégration LLM avec support dual-mode :
  - local   : Ollama (Mistral en local, rapide, sans coût)
  - perplexity : Perplexity API via LangChain (cloud, plus puissant)

Le provider est sélectionné dynamiquement à chaque appel via le paramètre
llm_provider passé depuis le frontend.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from loguru import logger

from src.agent.prompt import build_transaction_payload

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("langchain_openai non installé — mode Perplexity indisponible")

load_dotenv()

# ── Constantes ──────────────────────────────────────────────────────────────

PERPLEXITY_API_KEY   = os.getenv("PERPLEXITY_API_KEY", "")
PERPLEXITY_MODEL     = os.getenv("PERPLEXITY_MODEL", "sonar")
PERPLEXITY_BASE_URL  = os.getenv("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")

OLLAMA_BASE_URL      = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL         = os.getenv("OLLAMA_MODEL", "mistral")

DEFAULT_TEMPERATURE  = 0.1
DEFAULT_MAX_TOKENS   = 512


# ── Classe principale ────────────────────────────────────────────────────────

class FraudAgent:
    """
    Agent LLM pour générer des explications de fraude en langage naturel.

    Supporte deux providers :
      - 'local'      → Ollama (Mistral en local via HTTP)
      - 'perplexity' → Perplexity API via LangChain (ChatOpenAI compatible)

    Usage :
        agent = FraudAgent()
        explanation = agent.explain(transaction, fraud_proba, top_features,
                                    llm_provider='local')
    """

    def __init__(
        self,
        model: str = PERPLEXITY_MODEL,
        api_key: str = PERPLEXITY_API_KEY,
        base_url: str = PERPLEXITY_BASE_URL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model       = model
        self.api_key     = api_key
        self.base_url    = base_url
        self.temperature = temperature
        self.max_tokens  = max_tokens

        # Construit la chaîne LangChain pour Perplexity (si dispo)
        self._perplexity_chain = None
        if LANGCHAIN_AVAILABLE and api_key:
            self._build_perplexity_chain()

        logger.info(f"FraudAgent initialisé — Perplexity: {'✓' if self._perplexity_chain else '✗'} | Ollama: ✓")

    # ── Initialisation LangChain Perplexity ──────────────────────────────────

    def _build_perplexity_chain(self) -> None:
        try:
            from src.agent.prompt import build_fraud_prompt
            llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=60,
            )
            parser = StrOutputParser()
            prompt = build_fraud_prompt()
            self._perplexity_chain = prompt | llm | parser
            logger.success("Agent LLM Perplexity prêt ✓")
        except Exception as e:
            logger.warning(f"Impossible d'initialiser Perplexity LangChain: {e}")
            self._perplexity_chain = None

    # ── API publique ─────────────────────────────────────────────────────────

    def explain(
        self,
        transaction: dict,
        fraud_probability: float,
        top_features: list,
        threshold: float = 0.5,
        llm_provider: str = "local",
    ) -> str:
        """
        Génère une explication en langage naturel pour une transaction.

        Parameters
        ----------
        llm_provider : 'local' (Ollama Mistral) ou 'perplexity' (Perplexity API)
        """
        payload = build_transaction_payload(
            transaction=transaction,
            fraud_probability=fraud_probability,
            top_features=top_features,
            threshold=threshold,
        )

        logger.info(f"Génération LLM [{llm_provider}] pour TX: {transaction.get('transaction_id', '?')}")

        if llm_provider == "perplexity":
            return self._explain_perplexity(payload, transaction, fraud_probability, top_features)
        else:
            return self._explain_ollama(payload, transaction, fraud_probability, top_features)

    # ── Provider : Perplexity (LangChain) ────────────────────────────────────

    def _explain_perplexity(self, payload: dict, transaction: dict,
                             fraud_probability: float, top_features: list) -> str:
        if not self._perplexity_chain:
            logger.warning("Perplexity indisponible, fallback Ollama")
            return self._explain_ollama(payload, transaction, fraud_probability, top_features)
        try:
            response = self._perplexity_chain.invoke(payload)
            logger.success("Explication Perplexity générée ✓")
            return response
        except Exception as e:
            logger.error(f"Erreur Perplexity : {e}")
            return self._rule_based_fallback(transaction, fraud_probability, top_features)

    # ── Provider : Ollama local (Mistral) ────────────────────────────────────

    def _explain_ollama(self, payload: dict, transaction: dict,
                         fraud_probability: float, top_features: list) -> str:
        """Appelle Ollama via son API HTTP REST directement (sans LangChain)."""
        # Construire le prompt texte depuis le payload
        prompt_text = self._payload_to_prompt(payload)

        try:
            response = httpx.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt_text,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    }
                },
                timeout=120.0,
            )
            response.raise_for_status()
            result = response.json()
            explanation = result.get("response", "").strip()
            if explanation:
                logger.success(f"Explication Ollama ({OLLAMA_MODEL}) générée ✓")
                return explanation
            raise ValueError("Réponse vide d'Ollama")
        except Exception as e:
            logger.error(f"Erreur Ollama : {e}")
            return self._rule_based_fallback(transaction, fraud_probability, top_features)

    @staticmethod
    def _payload_to_prompt(payload: dict) -> str:
        """Convertit le payload LangChain en texte brut pour Ollama."""
        parts = []
        for key, value in payload.items():
            if isinstance(value, str):
                parts.append(value)
        return "\n\n".join(parts) if parts else str(payload)

    # ── Health Check ─────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Vérifie si au moins un provider est disponible."""
        # Test Ollama
        try:
            r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass

        # Test Perplexity
        if self.api_key:
            try:
                r = httpx.get(
                    f"{PERPLEXITY_BASE_URL.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=3.0,
                )
                return r.status_code in (200, 405, 422)
            except Exception:
                pass

        return False

    # ── Fallback sans LLM ────────────────────────────────────────────────────

    @staticmethod
    def _rule_based_fallback(
        transaction: dict,
        fraud_probability: float,
        top_features: list,
    ) -> str:
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
            f"[MOTIFS PRINCIPAUX] : La transaction présente des anomalies sur : {motifs}.\n"
            f"[RECOMMANDATION] : {'Bloquer immédiatement et contacter le client.' if fraud_probability > 0.7 else 'Surveiller et valider manuellement.'}\n"
            f"\n⚠️ Note : Explication générée par règles (LLM indisponible)."
        )
