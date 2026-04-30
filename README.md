# FraudIA - Systeme de Detection de Fraude Financiere par IA

> Projet de Fin d'Annee (PFA) - EMSI 4eme annee IA & Data  
> Othmane Moussawi & Rayane Ramzi - 2024-2025

---

## Objectif

Systeme hybride de detection de fraude financiere qui :
1. Detecte les transactions suspectes (XGBoost, RF, LR, Voting Ensemble)
2. Explique en langage naturel pourquoi (SHAP + LLM Perplexity/Ollama)
3. Minimise les faux positifs via calibration F0.5 des seuils
4. Apprend des retours humains (Human-in-the-Loop incremental)

---

## Diagrammes du projet

Voir le dossier ` + "`diagrams/`" + @` pour les diagrammes UML au format Mermaid :

| Diagramme | Fichier |
|---|---|
| Architecture du systeme | ` + "`01-architecture-systeme.mmd`" + @` |
| Sequence — Analyse transaction | ` + "`02-sequence-analyse.mmd`" + @` |
| Cas d'utilisation | ` + "`03-use-cases.mmd`" + @` |
| Classes — Pipeline ML | ` + "`04-classes-ml.mmd`" + @` |
| Deploiement | ` + "`05-deploiement.mmd`" + @` |
| Flux de donnees | ` + "`06-flux-donnees.mmd`" + @` |

---

## Installation

### Pre-requis
- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.ai) (optionnel, pour le LLM local)

### Backend
` + "`" + @`
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
` + "`" + @`

### Frontend
` + "`" + @`
cd frontend
npm install
` + "`" + @`

### Configuration
` + "`" + @`
copy .env.example .env
` + "`" + @`

### Dataset
Placer le fichier improved_fraud_dataset.csv dans data/raw/

---

## Entrainement des modeles (OBLIGATOIRE)

Les modeles ne sont PAS inclus dans le repo (.gitignore).

` + "`" + @`
venv\Scripts\python.exe train.py --n-trials 50
` + "`" + @`

Options:
- --skip-optuna : parametres par defaut (plus rapide)
- --n-features 20 : garder les 20 features les plus importantes
- --no-ensemble : ne pas creer le VotingClassifier

Genere dans models/ : preprocessor.joblib, xgboost.joblib, random_forest.joblib, logistic_regression.joblib, ensemble.joblib, thresholds.json, metrics.json

---

## Lancement

### API Backend (port 8000)
` + "`" + @`
venv\Scripts\python.exe -m uvicorn api.main:app --reload
` + "`" + @`
Swagger: http://localhost:8000/docs

### Frontend (port 5173)
` + "`" + @`
cd frontend
npm run dev
` + "`" + @`

---

## Comptes par defaut

| Email | Mot de passe | Role |
|---|---|---|
| superadmin@gmail.com | password | Superadmin |
| rayane.ramzi24@gmail.com | password | Analyste |
| othmanemoussawi@gmail.com | password | Analyste |

---

## Fonctionnalites

### Analyste
- Formulaire de transaction -> score + SHAP + explication LLM
- Upload CSV batch (max 100 transactions)
- Historique cloisonne avec filtres (risque, modele, recherche)
- Annotation (Fraude Confirmee / Transaction Valide)
- Export PDF / CSV

### Superadmin
- Vue globale de toutes les transactions
- Gestion des analystes (evaluation, notes)
- Panneau HITL (feedbacks, fine-tuning)
- Page analytique (risques, tendances, facteurs)

### Human-in-the-Loop
1. L'analyste annote une transaction comme frauduleuse ou valide
2. Les donnees sont sauvegardees dans data/human_feedback.parquet
3. Des 5 annotations, le superadmin peut declencher un fine-tuning
4. XGBoost ajoute 50 arbres sur les exemples humains (warm-start)
5. Le modele est recharge a chaud sans interruption

---

## Metriques

L'Accuracy n'est jamais utilisee (dataset desequilibre <1% fraudes).

- AUC-PR : metrique principale (Precision-Recall)
- F1-Score : compromis precision/rappel
- F0.5 : F-beta privilegiant 2x la precision (seuils de decision)

Les metriques reelles sont lues depuis models/metrics.json dans le dashboard.

---

## Structure

` + "`" + @`
code/
├── api/               # Backend FastAPI (JWT, SHAP, LLM, HITL, SMTP)
│   └── routes/        # Endpoints REST
├── frontend/          # React SPA (Vite + TailwindCSS)
│   └── src/components/
├── src/               # Package ML/XAI/LLM
│   ├── data/          # DataLoader, FraudPreprocessor (SMOTE)
│   ├── models/        # ModelTrainer, XGBoostTuner (Optuna), evaluator
│   ├── xai/           # FraudExplainer (SHAP wrapper)
│   └── agent/         # FraudAgent (LLM dual Perplexity/Ollama), prompts
├── diagrams/          # Diagrammes UML Mermaid
├── models/            # Modeles sauvegardes (gitignored)
├── data/              # Dataset + feedbacks (gitignored)
├── notebooks/         # Jupyter EDA
├── tests/             # Tests unitaires
├── train.py           # Pipeline d'entrainement (CV + feature selection + ensemble)
├── calibrate_thresholds.py  # Calibration F0.5 sans filtre arbitraire
└── requirements.txt   # Dependances Python
` + "`" + @`
