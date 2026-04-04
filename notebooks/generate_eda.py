import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell

nb = new_notebook()

nb.cells = [
    new_markdown_cell("# Phase 0 : Exploratory Data Analysis (EDA) 🔍\n\nObjectif : Comprendre le dataset, la distribution de la cible `is_fraud`, et identifier les features les plus discriminantes.\n\n*Note : Ce notebook utilise le DataLoader du projet.*"),
    new_code_cell("""%load_ext autoreload\n%autoreload 2\n\nimport pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nfrom loguru import logger\n\n# Configuration visuelle\nsns.set_theme(style="whitegrid", palette="muted")\nplt.rcParams['figure.figsize'] = (10, 6)\n\n# Suppression des warnings inutiles\nimport warnings\nwarnings.filterwarnings('ignore')"""),
    
    new_markdown_cell("## 1. Chargement des données"),
    new_code_cell("""import sys\nfrom pathlib import Path\nsys.path.append(str(Path.cwd().parent)) # Ajouter le dossier racine au path\n\nfrom src.data.loader import DataLoader\n\nloader = DataLoader()\ndf = loader.load()\n\ndf.head()"""),
    
    new_markdown_cell("## 2. Distribution de la variable cible (`is_fraud`)"),
    new_code_cell("""plt.figure(figsize=(8, 5))\nax = sns.countplot(data=df, x='is_fraud')\nplt.title("Distribution des Transactions (Légitimes vs Fraude)")\n\n# Ajouter les pourcentages\ntotal = len(df)\nfor p in ax.patches:\n    percentage = f'{100 * p.get_height() / total:.2f}%'\n    x = p.get_x() + p.get_width() / 2 - 0.05\n    y = p.get_height() + 100\n    ax.annotate(percentage, (x, y), ha='center')\n\nplt.show()"""),
    
    new_markdown_cell("## 3. Analyse des Features Numériques\nRegardons le `transaction_amount` (montant)."),
    new_code_cell("""plt.figure(figsize=(12, 6))\nsns.boxplot(data=df, x='is_fraud', y='transaction_amount')\nplt.yscale("log") # Log scale car les montants de fraude peuvent être extrêmes\nplt.title("Distribution des Montants par class (Log Scale)")\nplt.show()"""),
    
    new_markdown_cell("## 4. Analyse des Variables Catégorielles"),
    new_code_cell("""fig, axes = plt.subplots(1, 2, figsize=(16, 6))\n\n# Type de transaction\nsns.countplot(data=df, x='transaction_type', hue='is_fraud', ax=axes[0])\naxes[0].set_title("Fraudes par Type de Transaction")\naxes[0].tick_params(axis='x', rotation=45)\n\n# KYC Status\nsns.countplot(data=df, x='kyc_verified', hue='is_fraud', ax=axes[1])\naxes[1].set_title("Fraudes par Statut KYC")\n\nplt.tight_layout()\nplt.show()"""),
    
    new_markdown_cell("## 5. Matrice de Corrélation Numérique"),
    new_code_cell("""num_cols = df.select_dtypes(include=['number', 'bool']).columns\ncorr = df[num_cols].corr()\n\nplt.figure(figsize=(10, 8))\nsns.heatmap(corr, annot=True, cmap='RdBu_r', fmt=".2f", vmin=-1, vmax=1)\nplt.title("Matrice de Corrélation")\nplt.show()"""),
    
    new_markdown_cell("## 6. Vérification des Splits (Train / Val / Test)"),
    new_code_cell("""X_train, X_val, X_test, y_train, y_val, y_test = loader.get_splits(df)\n\nprint(f"Train : {len(X_train)} (Fraudes : {y_train.sum()})")\nprint(f"Val   : {len(X_val)} (Fraudes : {y_val.sum()})")\nprint(f"Test  : {len(X_test)} (Fraudes : {y_test.sum()})")""")
]

with open('c:\\Users\\othma\\Desktop\\Projet Fin Année\\code\\notebooks\\00_EDA.ipynb', 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print("Notebook 00_EDA.ipynb généré avec succès.")
