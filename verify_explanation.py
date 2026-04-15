import urllib.request
import json
import time

url = "http://127.0.0.1:8000/explain/"

model = "random_forest"
data = {
    "transaction_id": f"TX_EXPLAIN_{model}",
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

print(f"Testing explanation for model: {model}...")
start = time.time()
try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print(f"  Success in {time.time() - start:.1f}s")
        print(f"  Proba: {result['fraud_probability']:.4f}")
        print(f"  Top Features: {[f['feature'] for f in result['top_features']]}")
        print(f"  Explanation (preview): {result['explanation'][:100]}...")
except Exception as e:
    print(f"  Error: {e}")
    if hasattr(e, "read"):
        print(e.read().decode())
