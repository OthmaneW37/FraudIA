import urllib.request
import json

url = "http://127.0.0.1:8000/explain/"
data = {
    "transaction_id": "TX_TEST_123",
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
    "txn_count_today": 5
}

req = urllib.request.Request(
    url,
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print("Error:", e)
    if hasattr(e, "read"):
        print(e.read().decode())
