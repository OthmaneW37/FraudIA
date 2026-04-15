import urllib.request
import json

url = "http://127.0.0.1:8000/predict/"

for model in ["xgboost", "random_forest", "logistic_regression"]:
    data = {
        "transaction_id": f"TX_TEST_{model}",
        "transaction_amount": 50000.0,
        "currency": "MAD",
        "hour": 3,
        "minute": 15,
        "transaction_type": "transfer",
        "merchant_category": "crypto",
        "city": "Unknown",
        "country": "XX",
        "device_type": "mobile",
        "kyc_verified": False,
        "otp_used": False,
        "avg_amount_30d": 1000.0,
        "txn_count_today": 5,
        "selected_model": model
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    print(f"Testing model: {model}...")
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f"  Proba: {result['fraud_probability']:.4f} | Model used: {result['model_name']}")
    except Exception as e:
        print(f"  Error testing {model}: {e}")
