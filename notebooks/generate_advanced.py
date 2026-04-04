import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell

nb = new_notebook()

nb.cells = [
    new_markdown_cell("# Phase 1 (Suite) : Modèle Avancé (XGBoost) 🚀\n\nObjectif : \n1. Entraîner le vrai modèle Champion : **XGBoost**.\n2. Sauvegarder ce modèle et le Preprocessor pour la production (API).\n\n*Pourquoi XGBoost ? C'est le State-of-the-Art pour les données tabulaires (Excel/CSV), extrêmement rapide, et 100% compatible avec l'explicabilité SHAP.*"),
    
    new_code_cell("""%load_ext autoreload\n%autoreload 2\n\nimport sys\nfrom pathlib import Path\nsys.path.append(str(Path.cwd().parent))\n\nfrom loguru import logger\nfrom src.data.loader import DataLoader\nfrom src.data.preprocessor import FraudPreprocessor\nfrom src.models.trainer import ModelTrainer\nfrom src.models.evaluator import ModelEvaluator"""),
    
    new_markdown_cell("## 1. Préparation des données (Identique aux baselines)"),
    new_code_cell("""loader = DataLoader()\ndf = loader.load()\n\ncols_to_drop = ['organization', 'transaction_id', 'user_id', 'transaction_timestamp']\ndf_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])\n\nX_train, X_val, X_test, y_train, y_val, y_test = loader.get_splits(df_clean)\n\npreprocessor = FraudPreprocessor(smote_sampling_strategy=0.2)\nX_train_proc, y_train_proc = preprocessor.fit_transform_train(X_train, y_train)\nX_val_proc = preprocessor.transform(X_val)\n\n# 🔥 SAUVEGARDE DU PREPROCESSOR POUR LA PRODUCTION 🔥\npreprocessor.save()"""),
    
    new_markdown_cell("## 2. Entraînement de XGBoost\nNotre implémentation dans `trainer.py` calcule automatiquement le paramètre `scale_pos_weight` pour compenser le déséquilibre restant !"),
    new_code_cell("""evaluator = ModelEvaluator()\n\nlogger.info("Entraînement de XGBoost...")\n# On passe X_val pour faire de l'Early Stopping (éviter le sur-apprentissage)\nxgb_trainer = ModelTrainer(model_name="xgboost")\nxgb_trainer.fit(X_train_proc, y_train_proc, X_val=X_val_proc, y_val=y_val)\n\ny_val_prob_xgb = xgb_trainer.predict_proba(X_val_proc)[:, 1]"""),
    
    new_markdown_cell("## 3. Évaluation du Champion"),
    new_code_cell("""metrics_xgb = evaluator.evaluate(y_val, y_val_prob_xgb, model_name="XGBoost")\nfig = evaluator.plot_precision_recall_curve(y_val, y_val_prob_xgb, model_name="XGBoost")\n\n# Cherchons le seuil de décision optimal (qui maximise le compromis Précision/Recall)\nbest_threshold = evaluator.find_best_threshold(y_val, y_val_prob_xgb, metric="f1")"""),
    
    new_markdown_cell("## 4. Matrice de Confusion avec le meilleur seuil"),
    new_code_cell("""evaluator_optimal = ModelEvaluator(threshold=best_threshold)\ncm = evaluator_optimal.confusion_matrix_df(y_val, y_val_prob_xgb)\ndisplay(cm)"""),
    
    new_markdown_cell("## 5. Sauvegarde du Modèle Champion 🏆\nC'est ce fichier qui sera chargé par l'API FastAPI !"),
    new_code_cell("""xgb_trainer.save()""")
]

with open('c:\\Users\\othma\\Desktop\\Projet Fin Année\\code\\notebooks\\02_advanced_models.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print("Notebook 02_advanced_models.ipynb généré avec succès.")
