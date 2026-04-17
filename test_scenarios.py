import httpx
import itertools

base = {
    "transaction_id": "TX_T", "currency": "MAD", "minute": 0,
    "city": "Casablanca", "country": "Maroc", "selected_model": "xgboost",
}

# Grid search pour trouver les plages
amounts = [500, 5000, 15000, 50000, 200000]
hours = [10, 18, 23, 3]
categories = ["retail", "electronics", "crypto", "gambling"]
kyc_vals = [True, False]
otp_vals = [True, False]

best = {"FAIBLE": None, "MOYEN": None, "ELEVE": None, "CRITIQUE": None}
best_scores = {"FAIBLE": -1, "MOYEN": -1, "ELEVE": -1, "CRITIQUE": -1}

count = 0
for amt, hr, cat, kyc, otp in itertools.product(amounts, hours, categories, kyc_vals, otp_vals):
    data = {
        **base,
        "transaction_amount": amt, "hour": hr,
        "merchant_category": cat, "transaction_type": "transfer",
        "device_type": "Mobile App",
        "kyc_verified": kyc, "otp_used": otp,
        "avg_amount_30d": 1000, "txn_count_today": 2,
    }
    r = httpx.post("http://127.0.0.1:8000/explain/shap", json=data, timeout=30)
    d = r.json()
    prob = d["fraud_probability"]
    risk = d["risk_level"]
    count += 1

    # On cherche le meilleur score dans chaque bande
    if risk == "FAIBLE" and prob > best_scores["FAIBLE"]:
        best_scores["FAIBLE"] = prob
        best["FAIBLE"] = (prob, amt, hr, cat, kyc, otp)
    elif risk == "MOYEN" and prob > best_scores["MOYEN"]:
        best_scores["MOYEN"] = prob
        best["MOYEN"] = (prob, amt, hr, cat, kyc, otp)
    elif risk == "ELEVE" and prob > best_scores["ELEVE"]:
        best_scores["ELEVE"] = prob
        best["ELEVE"] = (prob, amt, hr, cat, kyc, otp)
    elif risk == "CRITIQUE" and prob > best_scores["CRITIQUE"]:
        best_scores["CRITIQUE"] = prob
        best["CRITIQUE"] = (prob, amt, hr, cat, kyc, otp)

print(f"Tested {count} combinations")
for level in ["FAIBLE", "MOYEN", "ELEVE", "CRITIQUE"]:
    if best[level]:
        prob, amt, hr, cat, kyc, otp = best[level]
        print(f"\n{level}: {prob*100:.1f}%")
        print(f"  amount={amt}, hour={hr}, category={cat}, kyc={kyc}, otp={otp}")
    else:
        print(f"\n{level}: NOT FOUND")
