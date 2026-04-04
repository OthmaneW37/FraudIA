# Système Basé sur un Agent IA pour la Détection d'Anomalies Financières

> **Projet de Fin d'Année (PFA) — EMSI 4ème année IA & Data**  
> Othmane & Ramzi · 2024–2025

---

## 🎯 Objectif

Système hybride de détection de fraude financière qui :
1. **Détecte** les transactions suspectes (ML/DL)
2. **Explique** en langage naturel pourquoi (XAI + LLM)
3. **Minimise** les faux positifs
4. **Résout** le problème de la boîte noire des modèles ML

---

## 🏗️ Architecture — 4 Piliers

| Pilier | Technologie | Rôle |
|--------|-------------|------|
| Détection ML | XGBoost + Isolation Forest | Score d'anomalie |
| XAI | SHAP TreeExplainer | Poids des features |
| Agent LLM | LangChain + Ollama (local) | Explication NL |
| Déploiement | FastAPI + Streamlit | API + Dashboard |

---

## 📁 Structure du projet

```
code/
├── data/
│   ├── raw/            # Dataset original (ignoré par git)
│   └── processed/      # Features engineered
├── notebooks/
│   ├── 00_EDA.ipynb
│   ├── 01_baseline_models.ipynb
│   ├── 02_advanced_models.ipynb
│   └── 03_xai_agent.ipynb
├── src/
│   ├── data/           # Chargement + preprocessing
│   ├── models/         # Entraînement + évaluation
│   ├── xai/            # SHAP wrapper
│   └── agent/          # LLM + prompts
├── api/                # FastAPI backend
├── dashboard/          # Streamlit frontend
├── models/             # Modèles sauvegardés (ignoré par git)
└── tests/
```

---

## 🚀 Installation

### 1. Pré-requis
- Python 3.11+
- [Ollama](https://ollama.ai) installé et lancé localement
- 8 GB RAM minimum (16 GB recommandé)

### 2. Environnement virtuel
```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 3. Configuration Ollama
```bash
ollama pull mistral             # Télécharger le modèle LLM
ollama serve                    # Lancer le serveur (port 11434)
```

### 4. Variables d'environnement
```bash
copy .env.example .env
# Éditer .env si besoin
```

### 5. Placer le dataset
```bash
# Copier improved_fraud_dataset.csv dans :
data/raw/improved_fraud_dataset.csv
```

---

## 🔄 Roadmap

- [x] Phase 0 : Setup & Scaffolding
- [ ] Phase 0 : EDA (Exploratory Data Analysis)
- [ ] Phase 1 : Baselines ML (LR, RF, XGBoost)
- [ ] Phase 2 : XAI (SHAP) + Agent LLM
- [ ] Phase 3 : API FastAPI + Dashboard Streamlit

---

## 📊 Dataset

| Propriété | Valeur |
|-----------|--------|
| Fichier | `improved_fraud_dataset.csv` |
| Volume | 1 000 000 transactions |
| Taille | ~187 MB |
| Label | `is_fraud` (binaire, déséquilibré < 1%) |
| Features | montant, heure, type, KYC, OTP, device, merchant, localisation... |

---

## 📏 Métriques de référence

> ⚠️ **L'Accuracy n'est JAMAIS utilisée** (dataset déséquilibré)

- **F1-Score** (compromis précision/rappel)
- **AUC-PR** (Area Under Precision-Recall Curve)
- **Recall** (minimiser les faux négatifs = frauds manquées)

---

## 🛠️ Stack technique

```
Python 3.11 · XGBoost · scikit-learn · imbalanced-learn
SHAP · LIME · PyTorch (Autoencoder)
LangChain · Ollama (Mistral/LLaMA local)
FastAPI · Pydantic v2 · Streamlit · Plotly
```
