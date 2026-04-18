from api.notifications import FraudEmailNotifier, SMTPSettings


def build_notifier(enabled: bool = True) -> FraudEmailNotifier:
    settings = SMTPSettings(
        enabled=enabled,
        host="smtp.example.com",
        port=587,
        username="demo@example.com",
        password="secret",
        from_email="fraudia@example.com",
        from_name="FraudIA",
        use_tls=True,
        use_ssl=False,
        reply_to=None,
    )
    return FraudEmailNotifier(settings=settings)


def test_build_alert_message_contains_transaction_details():
    notifier = build_notifier()

    message = notifier.build_alert_message(
        recipient_email="admin@example.com",
        recipient_name="Othmane",
        transaction={
            "transaction_id": "TX_001",
            "transaction_amount": 12000,
            "currency": "MAD",
            "hour": 3,
            "transaction_type": "transfer",
            "city": "Casablanca",
            "country": "Maroc",
        },
        fraud_probability=0.92,
        threshold=0.8,
        risk_level="CRITIQUE",
        model_name="xgboost",
        top_features=[
            {"feature": "amount_ratio", "direction": "↑fraude", "impact": "fort"},
        ],
    )

    body = message.get_content()

    assert message["To"] == "admin@example.com"
    assert "TX_001" in message["Subject"]
    assert "92.0%" in body
    assert "Casablanca, Maroc" in body
    assert "amount_ratio" in body


def test_send_fraud_alert_returns_false_when_disabled():
    notifier = build_notifier(enabled=False)

    sent = notifier.send_fraud_alert(
        recipient_email="admin@example.com",
        recipient_name="Othmane",
        transaction={"transaction_id": "TX_002"},
        fraud_probability=0.91,
        threshold=0.8,
        risk_level="CRITIQUE",
        model_name="xgboost",
        top_features=[],
    )

    assert sent is False
