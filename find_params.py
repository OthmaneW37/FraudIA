import httpx

# Best so far: amt=5000, hour=23 -> 73.8% (ÉLEVÉ!)
# Fine-tune around it
base = dict(transaction_id='TX_V', currency='MAD', minute=0, city='Casablanca', country='Maroc', selected_model='xgboost',
    transaction_amount=5000, hour=23, transaction_type='purchase', merchant_category='electronics',
    device_type='Mobile App', kyc_verified=True, otp_used=False, avg_amount_30d=2000, txn_count_today=3)

print("=== Fine-tune amount around 5000 ===")
for amt in [4000, 4500, 5000, 5500, 6000, 7000]:
    p = dict(base); p['transaction_amount'] = amt
    r = httpx.post('http://127.0.0.1:8000/explain/shap', json=p, timeout=10)
    d = r.json(); print(f"  amt={amt:>6} -> {d['fraud_probability']*100:5.1f}% = {d['risk_level']}")

print("=== Fine-tune hour ===")
for h in [1, 23]:
    for amt in [4000, 5000, 6000]:
        p = dict(base); p['hour'] = h; p['transaction_amount'] = amt
        r = httpx.post('http://127.0.0.1:8000/explain/shap', json=p, timeout=10)
        d = r.json(); print(f"  hour={h} amt={amt} -> {d['fraud_probability']*100:5.1f}% = {d['risk_level']}")

print("=== Confirm MOYEN: amt=15000, hour=2, transfer, crypto ===")
moyen = dict(base); moyen.update(transaction_amount=15000, hour=2, transaction_type='transfer', merchant_category='crypto', avg_amount_30d=1000)
r = httpx.post('http://127.0.0.1:8000/explain/shap', json=moyen, timeout=10)
d = r.json(); print(f"  -> {d['fraud_probability']*100:5.1f}% = {d['risk_level']}")

print("=== Confirm FAIBLE: amt=500, hour=14, purchase, retail ===")
faible = dict(base); faible.update(transaction_amount=500, hour=14, transaction_type='purchase', merchant_category='retail',
    device_type='Desktop', kyc_verified=True, otp_used=True, avg_amount_30d=600, txn_count_today=1)
r = httpx.post('http://127.0.0.1:8000/explain/shap', json=faible, timeout=10)
d = r.json(); print(f"  -> {d['fraud_probability']*100:5.1f}% = {d['risk_level']}")
