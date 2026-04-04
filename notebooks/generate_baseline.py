import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell

nb = new_notebook()

nb.cells = [
    new_markdown_cell("# Phase 1 : Modèles Baselines (LR & RF) 🚀\n\nObjectif : \n1. Préparer les données (Preprocessing + SMOTE)\n2. Entraîner une Régression Logistique (baseline linéaire)\n3. Entraîner un Random Forest (baseline arbre)\n4. Évaluer avec les métriques adaptées à la fraude (AUC-PR, F1-Score, Recall)"),
    
    new_code_cell("""%load_ext autoreload\n%autoreload 2\n\nimport sys\nfrom pathlib import Path\nsys.path.append(str(Path.cwd().parent))\n\nimport pandas as pd\nfrom loguru import logger\nfrom src.data.loader import DataLoader\nfrom src.data.preprocessor import FraudPreprocessor\nfrom src.models.trainer import ModelTrainer\nfrom src.models.evaluator import ModelEvaluator\n\n# Desactiver les warnings sklearn liés aux features names\nimport warnings\nwarnings.filterwarnings('ignore')"""),
    
    new_markdown_cell("## 1. Chargement et Nettoyage des Features"),
    new_code_cell("""loader = DataLoader()\ndf = loader.load()\n\n# On retire les colonnes non prédictives (Identifiants) ou redondantes avec 'hour'/'day_of_week'\ncols_to_drop = ['organization', 'transaction_id', 'user_id', 'transaction_timestamp']\ndf_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])\n\nlogger.info(f"Features utiles : {len(df_clean.columns) - 1}")\ndf_clean.head(3)"""),
    
    new_markdown_cell("## 2. Splits : Train / Val / Test"),
    new_code_cell("""X_train, X_val, X_test, y_train, y_val, y_test = loader.get_splits(df_clean)"""),
    
    new_markdown_cell("## 3. Preprocessing & SMOTE\n**Règle d'or** : SMOTE est appliqué UNIQUEMENT sur le Train Set !"),
    new_code_cell("""# Initialisation du preprocessor avec le ratio SMOTE (20%)\npreprocessor = FraudPreprocessor(smote_sampling_strategy=0.2)\n\n# Fit + Transform sur Train (génère les nouvelles données minoritaires)\nX_train_proc, y_train_proc = preprocessor.fit_transform_train(X_train, y_train)\n\n# Transform (Seulement) sur Val et Test\nX_val_proc = preprocessor.transform(X_val)\nX_test_proc = preprocessor.transform(X_test)\n\n# Sauvegarde du preprocessor pour la Phase 3 (API)\npreprocessor.save()"""),
    
    new_markdown_cell("## 4. Modèle Baseline 1 : Régression Logistique\nUn modèle linéaire simple, rapide, mais souvent limité pour les patterns complexes de fraude."),
    new_code_cell("""# L'evaluator va calculer les métriques et tracer les courbes\nevaluator = ModelEvaluator(threshold=0.5)\n\nlogger.info("Entraînement de la Régression Logistique...")\nlr_trainer = ModelTrainer(model_name="logistic_regression")\nlr_trainer.fit(X_train_proc, y_train_proc)\n\n# Prédictions sur le set de Validation (Pour comparer les modèles entre eux)\ny_val_prob_lr = lr_trainer.predict_proba(X_val_proc)[:, 1]\n\n# Evaluation\nmetrics_lr = evaluator.evaluate(y_val, y_val_prob_lr, model_name="Logistic Regression")\nevaluator.plot_precision_recall_curve(y_val, y_val_prob_lr, model_name="Logistic Regression")"""),
    
    new_markdown_cell("## 5. Modèle Baseline 2 : Random Forest\nContrairement à la régression logistique, ce modèle capture les relations non-linéaires."),
    new_code_cell("""logger.info("Entraînement du Random Forest...")\nrf_trainer = ModelTrainer(model_name="random_forest")\nrf_trainer.fit(X_train_proc, y_train_proc)\n\ny_val_prob_rf = rf_trainer.predict_proba(X_val_proc)[:, 1]\n\n# Evaluation\nmetrics_rf = evaluator.evaluate(y_val, y_val_prob_rf, model_name="Random Forest")\nevaluator.plot_precision_recall_curve(y_val, y_val_prob_rf, model_name="Random Forest")"""),
    
    new_markdown_cell("## 6. Comparatif des Baselines"),
    new_code_cell("""results = {\n    "Logistic Regression": metrics_lr,\n    "Random Forest": metrics_rf\n}\nevaluator.compare_models(results)\n\n# Sauvegarde des modèles (optionnel à ce stade si on préfère XGBoost par la suite)\n# lr_trainer.save()\n# rf_trainer.save()""")
]

with open('c:\\Users\\othma\\Desktop\\Projet Fin Année\\code\\notebooks\\01_baseline_models.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print("Notebook 01_baseline_models.ipynb généré avec succès.")
