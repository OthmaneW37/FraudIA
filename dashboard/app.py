"""
app.py — Dashboard Streamlit pour la détection de fraude.

Interface interactive permettant :
  1. Saisie manuelle d'une transaction
  2. Visualisation du score de fraude en temps réel
  3. Affichage des SHAP features (graphique waterfall)
  4. Lecture de l'explication LLM
  5. Monitoring global (métriques, statut API)

Architecture : appelle l'API FastAPI (localhost:8000) via httpx.
→ Le dashboard est découplé du backend (bon pour la démo PFA).
"""

from __future__ import annotations

import time

import httpx
import plotly.graph_objects as go
import streamlit as st

# ── Configuration de la page ─────────────────────────────────────────────────

st.set_page_config(
    page_title="🔍 Fraud Detection Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = "http://localhost:8000"

# ── CSS Custom ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Gradient header */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        border: 1px solid #e94560;
    }
    .fraud-score-high   { color: #e74c3c; font-size: 2.5rem; font-weight: bold; }
    .fraud-score-medium { color: #f39c12; font-size: 2.5rem; font-weight: bold; }
    .fraud-score-low    { color: #2ecc71; font-size: 2.5rem; font-weight: bold; }
    .metric-card {
        background: #16213e;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #e94560;
    }
</style>
""", unsafe_allow_html=True)


# ── Fonctions UI helpers ────────────────────────────────────────────────────────

def _show_prediction_result(result: dict, threshold: float) -> None:
    """Affiche le score de fraude avec un jauge colorée."""
    prob  = result.get("fraud_probability", 0)
    risk  = result.get("risk_level", "N/A")
    fraud = result.get("is_fraud", False)

    # Jauge Plotly
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=prob * 100,
        number={"suffix": "%", "font": {"size": 40}},
        title={"text": "Score de Fraude", "font": {"size": 20}},
        gauge={
            "axis": {"range": [0, 100], "ticksuffix": "%"},
            "bar": {"color": "#e74c3c" if fraud else "#2ecc71"},
            "steps": [
                {"range": [0, 40],   "color": "#d5f5e3"},
                {"range": [40, 70],  "color": "#fdebd0"},
                {"range": [70, 100], "color": "#fadbd8"},
            ],
            "threshold": {
                "line": {"color": "black", "width": 3},
                "thickness": 0.75,
                "value": threshold * 100,
            },
        },
    ))
    fig.update_layout(height=280, margin=dict(t=60, b=0, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

    # Bandeau de décision
    if fraud:
        st.error(f"🚨 FRAUDE DÉTECTÉE — Niveau de risque : **{risk}**")
    else:
        st.success(f"✅ Transaction légitime — Niveau de risque : **{risk}**")

    st.caption(f"⏱️ Temps de traitement : {result.get('processing_time_ms', 0):.1f} ms")


def _show_shap_and_explanation(result: dict) -> None:
    """Affiche les features SHAP et l'explication LLM."""
    st.divider()

    # SHAP features
    top_features = result.get("top_features", [])
    if top_features:
        st.subheader("🔬 Facteurs explicatifs (SHAP)")
        for feat in top_features:
            color = "🔴" if feat["shap_value"] > 0 else "🟢"
            st.write(
                f"{color} **{feat['feature']}** → {feat['direction']} "
                f"(impact: {feat['impact']}, SHAP: {feat['shap_value']:+.4f})"
            )

    # Explication LLM
    explanation = result.get("explanation", "")
    if explanation:
        st.divider()
        st.subheader("🧠 Explication de l'Agent IA")
        st.info(explanation)
        st.caption(f"Modèle LLM : {result.get('llm_model', 'N/A')}")


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1 style="color: white; margin: 0;">🔍 Fraud Detection Dashboard</h1>
    <p style="color: #aaa; margin: 0.5rem 0 0 0;">
        Système IA de détection et d'explication des fraudes financières · PFA EMSI 2025
    </p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar — Statut API ──────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuration")

    api_url = st.text_input("URL de l'API", value=API_BASE_URL)

    # Vérification statut
    if st.button("🔄 Vérifier le statut", use_container_width=True):
        with st.spinner("Vérification..."):
            try:
                resp = httpx.get(f"{api_url}/health", timeout=15.0)
                resp.raise_for_status()
                health = resp.json()
                st.success(f"✅ API : {health['status'].upper()}")
                st.write(f"🤖 Modèle : {'✅' if health['model_loaded'] else '❌'}")
                st.write(f"🧠 LLM    : {'✅' if health['llm_online'] else '❌'}")
            except Exception as e:
                st.error(f"❌ API inaccessible\n{str(e)[:100]}")

    st.divider()

    # Seuil de décision
    threshold = st.slider(
        "🎚️ Seuil de décision",
        min_value=0.1,
        max_value=0.9,
        value=0.5,
        step=0.05,
        help="Seuil en dessous duquel la transaction est considérée légitime.",
    )

    st.caption(f"Seuil actuel : **{threshold:.0%}**")


# ── Onglets principaux ────────────────────────────────────────────────────────

tab1, tab2 = st.tabs(["🔍 Analyser une transaction", "📊 Monitoring"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Analyse d'une transaction
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    col_form, col_result = st.columns([1, 1], gap="large")

    # ── Formulaire de saisie ──────────────────────────────────────────────────
    with col_form:
        st.subheader("📝 Saisie de la transaction")

        with st.form("transaction_form"):
            tx_id   = st.text_input("ID Transaction", value="TX_2024_DEMO_001")
            amount  = st.number_input("💰 Montant (MAD)", min_value=1.0, value=15000.0, step=100.0)
            hour    = st.slider("🕐 Heure", 0, 23, 2)
            tx_type = st.selectbox("📂 Type", ["transfer", "payment", "withdrawal", "purchase", "deposit"])

            col_a, col_b = st.columns(2)
            with col_a:
                merchant = st.text_input("🏪 Marchand", value="Virement international")
                location = st.text_input("📍 Localisation", value="Rabat, Maroc")
            with col_b:
                device   = st.text_input("📱 Device", value="device_inconnu_x7")
                kyc      = st.selectbox("🪪 KYC", ["incomplete", "complete", "pending", "rejected"])

            otp       = st.checkbox("✅ OTP vérifié", value=False)
            avg_30d   = st.number_input("📈 Montant moy. 30j (optionnel)", min_value=0.0, value=500.0)
            tx_count  = st.number_input("🔢 Transactions aujourd'hui", min_value=0, value=12)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submit_predict = st.form_submit_button("⚡ Score rapide", use_container_width=True)
            with col_btn2:
                submit_explain = st.form_submit_button("🧠 Score + Explication LLM", use_container_width=True, type="primary")

    # ── Résultats ─────────────────────────────────────────────────────────────
    with col_result:
        st.subheader("📊 Résultats d'analyse")

        payload = {
            "transaction_id": tx_id,
            "transaction_amount": amount,
            "currency": "MAD",
            "hour": hour,
            "minute": 0,
            "transaction_type": tx_type,
            "merchant_category": merchant,
            "city": "Rabat",
            "country": "Maroc",
            "device_type": device,
            "kyc_verified": True if kyc == "complete" else False,
            "otp_used": otp,
            "avg_amount_30d": avg_30d if avg_30d > 0 else None,
            "txn_count_today": tx_count,
        }

        # Score rapide
        if submit_predict:
            with st.spinner("Analyse en cours..."):
                try:
                    resp = httpx.post(f"{api_url}/predict/", json=payload, timeout=10.0)
                    resp.raise_for_status()
                    result = resp.json()
                    _show_prediction_result(result, threshold)
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")

        # Score + Explication LLM
        if submit_explain:
            with st.spinner("Analyse + génération d'explication (peut prendre 5-15s)..."):
                try:
                    resp = httpx.post(f"{api_url}/explain/", json=payload, timeout=120.0)
                    resp.raise_for_status()
                    result = resp.json()
                    _show_prediction_result(result, threshold)
                    _show_shap_and_explanation(result)
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")





# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Monitoring
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.subheader("📊 Monitoring du système")
    st.info("🚧 Cette section sera alimentée avec les métriques en production (Phase 3).")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Transactions 24h", "—", help="À brancher sur la base de données")
    with col2:
        st.metric("Fraudes détectées", "—")
    with col3:
        st.metric("F1-Score (val)", "—")
    with col4:
        st.metric("AUC-PR (val)", "—")
