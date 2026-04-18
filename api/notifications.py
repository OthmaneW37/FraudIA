"""
notifications.py - Envoi d'alertes email pour les transactions frauduleuses.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any

from dotenv import load_dotenv
from loguru import logger

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "oui"}


@dataclass(frozen=True)
class SMTPSettings:
    enabled: bool
    host: str
    port: int
    username: str
    password: str
    from_email: str
    from_name: str
    use_tls: bool
    use_ssl: bool
    reply_to: str | None = None

    @classmethod
    def from_env(cls) -> "SMTPSettings":
        port_raw = os.getenv("SMTP_PORT", "587")
        try:
            port = int(port_raw)
        except ValueError:
            port = 587

        return cls(
            enabled=_as_bool(os.getenv("ALERT_EMAIL_ENABLED"), False),
            host=os.getenv("SMTP_HOST", ""),
            port=port,
            username=os.getenv("SMTP_USERNAME", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            from_email=os.getenv("SMTP_FROM_EMAIL", ""),
            from_name=os.getenv("SMTP_FROM_NAME", "FraudIA"),
            use_tls=_as_bool(os.getenv("SMTP_USE_TLS"), True),
            use_ssl=_as_bool(os.getenv("SMTP_USE_SSL"), False),
            reply_to=os.getenv("SMTP_REPLY_TO") or None,
        )

    @property
    def is_configured(self) -> bool:
        return all(
            [
                self.enabled,
                self.host,
                self.port,
                self.username,
                self.password,
                self.from_email,
            ]
        )


class FraudEmailNotifier:
    """Service SMTP pour envoyer une alerte simple quand une transaction depasse le seuil."""

    def __init__(self, settings: SMTPSettings | None = None) -> None:
        self.settings = settings or SMTPSettings.from_env()

    def send_fraud_alert(
        self,
        *,
        recipient_email: str,
        recipient_name: str | None,
        transaction: dict[str, Any],
        fraud_probability: float,
        threshold: float,
        risk_level: str,
        model_name: str,
        top_features: list[dict[str, Any]] | None = None,
    ) -> bool:
        if not recipient_email:
            return False

        if not self.settings.enabled:
            logger.info("Alerte email desactivee - aucun email envoye.")
            return False

        if not self.settings.is_configured:
            logger.warning("SMTP non configure - impossible d'envoyer l'alerte email.")
            return False

        message = self.build_alert_message(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            transaction=transaction,
            fraud_probability=fraud_probability,
            threshold=threshold,
            risk_level=risk_level,
            model_name=model_name,
            top_features=top_features or [],
        )

        try:
            if self.settings.use_ssl:
                with smtplib.SMTP_SSL(
                    self.settings.host,
                    self.settings.port,
                    timeout=20,
                ) as server:
                    server.login(self.settings.username, self.settings.password)
                    server.send_message(message)
            else:
                with smtplib.SMTP(self.settings.host, self.settings.port, timeout=20) as server:
                    server.ehlo()
                    if self.settings.use_tls:
                        server.starttls(context=ssl.create_default_context())
                        server.ehlo()
                    server.login(self.settings.username, self.settings.password)
                    server.send_message(message)

            logger.success(
                f"Alerte email envoyee a {recipient_email} pour TX {transaction.get('transaction_id', '?')}"
            )
            return True
        except Exception as exc:
            logger.error(f"Echec envoi email pour TX {transaction.get('transaction_id', '?')}: {exc}")
            return False

    def build_alert_message(
        self,
        *,
        recipient_email: str,
        recipient_name: str | None,
        transaction: dict[str, Any],
        fraud_probability: float,
        threshold: float,
        risk_level: str,
        model_name: str,
        top_features: list[dict[str, Any]],
    ) -> EmailMessage:
        transaction_id = transaction.get("transaction_id", "TX_INCONNUE")

        message = EmailMessage()
        message["Subject"] = f"[FraudIA] Alerte fraude - {transaction_id}"
        message["From"] = formataddr((self.settings.from_name, self.settings.from_email))
        message["To"] = recipient_email
        if self.settings.reply_to:
            message["Reply-To"] = self.settings.reply_to

        message.set_content(
            self._render_body(
                recipient_name=recipient_name,
                transaction=transaction,
                fraud_probability=fraud_probability,
                threshold=threshold,
                risk_level=risk_level,
                model_name=model_name,
                top_features=top_features,
            )
        )
        return message

    def _render_body(
        self,
        *,
        recipient_name: str | None,
        transaction: dict[str, Any],
        fraud_probability: float,
        threshold: float,
        risk_level: str,
        model_name: str,
        top_features: list[dict[str, Any]],
    ) -> str:
        greeting = f"Bonjour {recipient_name}," if recipient_name else "Bonjour,"
        transaction_id = transaction.get("transaction_id", "TX_INCONNUE")
        amount = transaction.get("transaction_amount", "N/A")
        currency = transaction.get("currency", "MAD")
        hour = transaction.get("hour", "N/A")
        transaction_type = transaction.get("transaction_type", "N/A")
        city = transaction.get("city", "N/A")
        country = transaction.get("country", "N/A")

        feature_lines = []
        for feature in top_features[:3]:
            name = feature.get("feature", "inconnue")
            direction = feature.get("direction", "")
            impact = feature.get("impact", "")
            feature_lines.append(f"- {name} ({direction}, impact {impact})")

        feature_block = "\n".join(feature_lines) if feature_lines else "- Aucune detail XAI disponible"

        return (
            f"{greeting}\n\n"
            "Une transaction simulee vient de depasser le seuil de fraude configure dans FraudIA.\n\n"
            f"Reference          : {transaction_id}\n"
            f"Montant            : {amount} {currency}\n"
            f"Heure              : {hour}h\n"
            f"Type               : {transaction_type}\n"
            f"Localisation       : {city}, {country}\n"
            f"Modele             : {model_name}\n"
            f"Score fraude       : {fraud_probability:.1%}\n"
            f"Seuil applique     : {threshold:.1%}\n"
            f"Niveau de risque   : {risk_level}\n\n"
            "Principaux facteurs :\n"
            f"{feature_block}\n\n"
            "Action recommandee : verifier la transaction et contacter le client si necessaire.\n\n"
            "Email envoye automatiquement par FraudIA."
        )


def notify_fraud_alert(
    *,
    user: dict[str, Any] | None,
    transaction: dict[str, Any],
    is_fraud: bool,
    fraud_probability: float,
    threshold: float,
    risk_level: str,
    model_name: str,
    top_features: list[dict[str, Any]] | None = None,
) -> bool:
    """Envoie l'alerte a l'utilisateur connecte si la transaction est frauduleuse."""
    if not is_fraud or not user:
        return False

    return fraud_email_notifier.send_fraud_alert(
        recipient_email=user.get("email", ""),
        recipient_name=user.get("full_name"),
        transaction=transaction,
        fraud_probability=fraud_probability,
        threshold=threshold,
        risk_level=risk_level,
        model_name=model_name,
        top_features=top_features or [],
    )


fraud_email_notifier = FraudEmailNotifier()
