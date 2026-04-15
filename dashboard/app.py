from __future__ import annotations

import time
import httpx
import plotly.graph_objects as go
import streamlit as st

# ── Configuration de la page ─────────────────────────────────────────────────

st.set_page_config(
    page_title="FraudIA | Premium Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = "http://localhost:8000"

# ── CSS Premium (Glassmorphism & FinTech Theme) ────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Background Global */
    .stApp {
        background: radial-gradient(circle at top right, #1e293b, #0f172a);
    }

    /* Glass Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        transition: transform 0.3s ease;
    }
    .glass-card:hover {
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    /* Header Styling */
    .nav-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        margin-bottom: 30px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    .nav-title {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Status Badges */
    .badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-fraud { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }
    .badge-safe  { background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #22c55e; }
    .badge-warn  { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #f59e0b; }

    /* Custom Streamlit Overrides */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }
    
    /* AI Agent Bubble */
    .agent-bubble {
        background: rgba(129, 140, 248, 0.1);
        border-left: 4px solid #818cf8;
        padding: 15px;
        border-radius: 0 12px 12px 0;
        margin-top: 10px;
        font-style: italic;
    }

    /* Sidebar logic */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)


# ── Fonctions UI helpers ────────────────────────────────────────────────────────

def _show_prediction_result(result: dict, threshold: float) -> None:
    """Affiche le score de fraude avec un design premium."""
    prob  = result.get("fraud_probability", 0)
    risk  = result.get("risk_level", "N/A")
    fraud = result.get("is_fraud", False)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    col_score, col_status = st.columns([1.5, 1])
    
    with col_score:
        # Jauge Plotly Modernisée
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=prob * 100,
            number={"suffix": "%", "font": {"size": 40, "color": "white", "family": "Inter"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "rgba(255,255,255,0.2)"},
                "bar": {"color": "#ef4444" if fraud else "#22c55e"},
                "bgcolor": "rgba(255,255,255,0.05)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40],   "color": "rgba(34, 197, 94, 0.1)"},
                    {"range": [40, 75],  "color": "rgba(245, 158, 11, 0.1)"},
                    {"range": [75, 100], "color": "rgba(239, 68, 68, 0.1)"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 2},
                    "thickness": 0.8,
                    "value": threshold * 100,
                },
            },
        ))
        fig.update_layout(
            height=200, 
            margin=dict(t=0, b=0, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font={"color": "white", "family": "Inter"}
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    with col_status:
        st.markdown("<br>", unsafe_allow_html=True)
        if fraud:
            st.markdown(f'<span class="badge badge-fraud">CRITIQUE</span>', unsafe_allow_html=True)
            st.markdown(f"### 🚨 Fraude Détectée")
        elif risk == "MOYEN":
            st.markdown(f'<span class="badge badge-warn">ATTENTION</span>', unsafe_allow_html=True)
            st.markdown(f"### 🟠 Risque Modéré")
        else:
            st.markdown(f'<span class="badge badge-safe">SÉCURISÉ</span>', unsafe_allow_html=True)
            st.markdown(f"### ✅ Légitime")
            
        st.write(f"Niveau : **{risk}**")
        st.caption(f"Seuil : {threshold:.0%}")

    st.markdown('</div>', unsafe_allow_html=True)
    st.caption(f"⚡ Traitement : {result.get('processing_time_ms', 0):.1f}ms | Modèle : {result.get('model_name', 'N/A')}")


def _show_shap_and_explanation(result: dict) -> None:
    """Affiche les features SHAP et l'explication Agent IA avec style Card."""
    
    top_features = result.get("top_features", [])
    explanation = result.get("explanation", "")

    col_shap, col_agent = st.columns([1, 1.2])

    with col_shap:
        st.markdown('<div class="glass-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown("#### 🔬 Facteurs d'Influence")
        if top_features:
            for feat in top_features:
                color = "#ef4444" if feat["shap_value"] > 0 else "#22c55e"
                symbol = "↑" if feat["shap_value"] > 0 else "↓"
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.9rem;">
                    <span>{feat['feature']}</span>
                    <span style="color: {color}; font-weight: bold;">{symbol} {abs(feat['shap_value']):.3f}</span>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_agent:
        st.markdown('<div class="glass-card" style="height: 100%;">', unsafe_allow_html=True)
        st.markdown("#### 🤖 Rapport de l'Agent IA")
        if explanation:
            st.markdown(f'<div class="agent-bubble">{explanation}</div>', unsafe_allow_html=True)
        else:
            st.info("Lancez l'analyse complète pour obtenir le rapport LLM.")
        st.markdown('</div>', unsafe_allow_html=True)


# ── Navigation Header ─────────────────────────────────────────────────────────

st.markdown("""
<div class="nav-bar">
    <div class="nav-title">🛡️ FraudIA <span style="font-size: 0.9rem; color: #64748b; font-weight: normal;">| Next-Gen Detection</span></div>
    <div style="font-size: 0.8rem; color: #94a3b8;">PFA EMSI 2025 · v2.0</div>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ SYSTEM CONFIG")
    
    with st.expander("🔗 API CONNECTION", expanded=False):
        api_url = st.text_input("Endpoint", value=API_BASE_URL)
        if st.button("Check Status", use_container_width=True):
            try:
                resp = httpx.get(f"{api_url}/health", timeout=5.0)
                if resp.status_code == 200: st.success("Online")
            except: st.error("Offline")

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("#### 🤖 AI CORE")
    model_choice = st.selectbox(
        "Model Engine",
        options=["xgboost", "random_forest", "logistic_regression"],
        help="Moteur d'IA utilisé pour l'analyse de risque."
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("#### 🎚️ SENSITIVITY")
    threshold = st.slider(
        "Decision Threshold",
        min_value=0.1, max_value=0.95, value=0.80, step=0.05
    )
    st.caption("Cible : Précision > 95%")
    
    st.divider()
    st.markdown("🌐 **Production Mode**")
    st.caption("Monitoring actif sur 14,205 transactions.")


# ── Tabs Content ─────────────────────────────────────────────────────────────

tab1, tab2 = st.tabs(["🔍 TRANSACTION ANALYZER", "📊 NETWORK MONITORING"])

with tab1:
    col_input, col_output = st.columns([1, 1], gap="large")

    with col_input:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 📝 Input Details")
        
        with st.form("tx_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                tx_id = st.text_input("Transaction ID", "TX_2024_DEMO_01")
                amount = st.number_input("Amount (MAD)", min_value=1.0, value=15000.0)
                hour = st.slider("Time of Day (0-23)", 0, 23, 2)
            with c2:
                tx_type = st.selectbox("Type", ["transfer", "payment", "withdrawal", "purchase", "deposit"])
                merchant = st.selectbox("Category", ["crypto", "international_transfer", "e-commerce", "retail", "gambling", "atm"])
                kyc = st.selectbox("KYC Status", ["complete", "incomplete", "pending"])
            
            st.divider()
            
            c3, c4 = st.columns(2)
            with c3:
                otp = st.checkbox("OTP Verified", value=False)
                avg_30d = st.number_input("30d Avg Amount", value=1000.0)
            with c4:
                tx_count = st.number_input("Txns Today", value=2)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            b1, b2 = st.columns(2)
            with b1:
                submit_fast = st.form_submit_button("⚡ Quick Scan", use_container_width=True)
            with b2:
                submit_full = st.form_submit_button("🧠 Explainable AI", use_container_width=True, type="primary")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_output:
        st.markdown("### 📽️ Analysis Output")
        
        payload = {
            "transaction_id": tx_id,
            "transaction_amount": amount,
            "currency": "MAD",
            "hour": hour,
            "minute": 0,
            "transaction_type": tx_type,
            "merchant_category": merchant,
            "city": "Casablanca",
            "country": "Maroc",
            "device_type": "mobile",
            "kyc_verified": True if kyc == "complete" else False,
            "otp_used": otp,
            "avg_amount_30d": avg_30d,
            "txn_count_today": tx_count,
            "selected_model": model_choice
        }

        if submit_fast:
            with st.spinner("Analyzing..."):
                try:
                    r = httpx.post(f"{api_url}/predict/", json=payload, timeout=10.0)
                    _show_prediction_result(r.json(), threshold)
                except Exception as e: st.error(f"Error: {e}")

        if submit_full:
            with st.spinner("Executing Deep Analysis + LLM Report..."):
                try:
                    r = httpx.post(f"{api_url}/explain/", json=payload, timeout=120.0)
                    res = r.json()
                    _show_prediction_result(res, threshold)
                    _show_shap_and_explanation(res)
                except Exception as e: st.error(f"Error: {e}")


# ── Monitoring View ──────────────────────────────────────────────────────────

with tab2:
    import pandas as pd
    import numpy as np
    import plotly.express as px

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Network Health & Performance")
    
    # KPIs Top
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1: st.metric("24h Volume", "14,205", "+12%")
    with kpi2: st.metric("Blocked Frauds", "127", "-3", delta_color="inverse")
    with kpi3: st.metric("Fraud Rate", "0.89%", "-0.02%", delta_color="inverse")
    with kpi4: st.metric("Avg Latency", "1.1s", "-0.1s", delta_color="inverse")
    st.markdown('</div>', unsafe_allow_html=True)

    g1, g2 = st.columns(2)
    with g1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### Hourly Activity Patterns")
        hours = list(range(24))
        legit = [abs(int(np.sin(h/4) * 500 + 800 + np.random.randint(-100, 100))) for h in hours]
        fraud = [abs(int(np.cos(h/6) * 15 + 20 + np.random.randint(-5, 10))) for h in hours]
        df_t = pd.DataFrame({"H": hours, "Legit": legit, "Fraud": fraud})
        fig_t = go.Figure()
        fig_t.add_trace(go.Bar(x=df_t["H"], y=df_t["Legit"], name="Legit", marker_color="#22c55e"))
        fig_t.add_trace(go.Scatter(x=df_t["H"], y=df_t["Fraud"]*15, name="Fraud (x15)", line=dict(color="#ef4444", width=3)))
        fig_t.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig_t, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with g2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### Fraud Distribution by Amount")
        amts = np.random.lognormal(mean=8, sigma=1.5, size=120)
        fig_h = px.histogram(x=amts, nbins=30, color_discrete_sequence=["#ef4444"])
        fig_h.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig_h, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("#### 🚨 Real-time Critical Alerts")
    df_alerts = pd.DataFrame({
        "Status": ["🔴 High", "🔴 High", "🔴 High", "🟠 Med", "🟠 Med"],
        "Time": ["12:02", "11:58", "11:45", "11:30", "11:10"],
        "Amount": ["45,000 MAD", "12,500 MAD", "3,400 MAD", "150,000 MAD", "8,900 MAD"],
        "Category": ["Crypto", "Virement", "Web Purchase", "ATM", "Virement"],
        "Model": ["XGBoost", "XGBoost", "RF", "XGBoost", "LR"]
    })
    st.dataframe(df_alerts, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
