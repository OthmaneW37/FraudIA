import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell

nb = new_notebook()

nb.cells = [
    new_markdown_cell("# Phase 2 : XAI (SHAP) & Agent LLM 🧠\n\nObjectif :\n1. **Ouvrir la boîte noire** de notre modèle XGBoost grâce à SHAP (Values de Shapley).\n2. **Générer une explication en langage naturel** avec l'Agent LLM (Ollama / Mistral).\n\n*Pré-requis : avoir lancé `ollama serve` et téléchargé le modèle (`ollama pull mistral`) en arrière-plan.*"),
    
    new_code_cell("""%load_ext autoreload\n%autoreload 2\n\nimport sys\nfrom pathlib import Path\nsys.path.append(str(Path.cwd().parent))\n\nimport pandas as pd\nfrom loguru import logger\nfrom src.data.loader import DataLoader\nfrom src.data.preprocessor import FraudPreprocessor\nfrom src.models.trainer import ModelTrainer\nfrom src.xai.explainer import FraudExplainer\nfrom src.agent.llm_client import FraudAgent"""),
    
    new_markdown_cell("## 1. Chargement du dataset et des modèles entraînés"),
    new_code_cell("""# Le Test Set n'a jamais été vu par le modèle pendant le SMOTE ni pendant l'entraînement\nloader = DataLoader()\ndf = loader.load()\n\ncols_to_drop = ['organization', 'transaction_id', 'user_id', 'transaction_timestamp']\ndf_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])\n\nX_train, X_val, X_test, y_train, y_val, y_test = loader.get_splits(df_clean)\n\n# Re-chargement des modèles depuis le HD\npreprocessor = FraudPreprocessor.load(Path("../models/preprocessor.joblib"))\nxgb_trainer = ModelTrainer.load(Path("../models/xgboost.joblib"), model_name="xgboost")"""),
    
    new_markdown_cell("## 2. Instantiation de l'Explainer SHAP"),
    new_code_cell("""# On lui donne le modèle Scikit-learn brut et le nom des features transformées par le preprocessor\nexplainer = FraudExplainer(\n    model=xgb_trainer.model,\n    feature_names=preprocessor.feature_names,\n    model_type=\"tree\"\n)\nlogger.info("Explainer SHAP Prêt !")"""),
    
    new_markdown_cell("## 3. Sélection de deux transactions pour l'analyse\nOn prend une Transaction Légitime et une Transaction Frauduleuse du **Test Set**."),
    new_code_cell("""# 1. Légitime\nidx_legit = y_test[y_test == 0].index[0]\nx_legit_raw = df.loc[idx_legit]   # Avec metadata (id, date etc.)\nx_legit_features = X_test.loc[[idx_legit]]\n\n# 2. Fraude\nidx_fraud = y_test[y_test == 1].index[0]\nx_fraud_raw = df.loc[idx_fraud]\nx_fraud_features = X_test.loc[[idx_fraud]]\n\n# Application du preprocessing pour le modèle\nx_legit_proc = preprocessor.transform(x_legit_features)\nx_fraud_proc = preprocessor.transform(x_fraud_features)"""),
    
    new_markdown_cell("## 4. SHAP Waterfall & Top Features (Exemple = Fraude)"),
    new_code_cell("""# Prédiction\nproba_fraud = xgb_trainer.predict_proba(x_fraud_proc)[0, 1]\nprint(f"Probabilité de fraude prédite : {proba_fraud:.1%}")\n\n# SHAP Waterfall\nfig = explainer.plot_waterfall(x_fraud_proc, transaction_id=x_fraud_raw[\"transaction_id\"])\n\n# Extraction des Top Features (formattées pour le LLM)\nshap_values = explainer.explain_instance(x_fraud_proc)\ntop_features = explainer.get_top_features(shap_values, n=5)\n\nprint("\\n📌 Top Features pour le LLM :")\nfor f in top_features:\n    print(f)\n"""),
    
    new_markdown_cell("## 5. Explication NLP par l'Agent IA\nIci, l'IA (Mistral via Ollama) va recevoir les données et les valeurs SHAP pour rédiger une analyse."),
    new_code_cell("""# Vérification de l'état d'Ollama\nllm_agent = FraudAgent(model="mistral")\n\nif llm_agent.health_check():\n    print("Agent LLM en ligne ! Génération en cours...\\n")\n    \n    explication = llm_agent.explain(\n        transaction=x_fraud_raw.to_dict(),\n        fraud_probability=proba_fraud,\n        top_features=top_features,\n        threshold=0.35 # Le seuil optimal qu'on a vu en Phase 1\n    )\n    \n    print(\"=\"*50)\n    print(\"🤖 EXPLICATION GÉNÉRÉE :\\n\")\n    print(explication)\n    print(\"=\"*50)\nelse:\n    print("⚠️ Ollama n'est pas lancé. Fallback sur les règles métiers basiques utilisé.")\n    \n    # Fallback si pas de LLM\n    explication = llm_agent.explain(\n        transaction=x_fraud_raw.to_dict(),\n        fraud_probability=proba_fraud,\n        top_features=top_features\n    )\n    print(explication)""")
]

with open('c:\\Users\\othma\\Desktop\\Projet Fin Année\\code\\notebooks\\03_xai_agent.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print("Notebook 03_xai_agent.ipynb généré avec succès.")
