# Durum Wheat Pipeline API (IRA Medenine)

API FastAPI complète pour classification parentale, recommandations de croisements, XAI SHAP, Monte Carlo et ODM/Base Editing.

## Structure

- `app/main.py` : app FastAPI + lifespan
- `app/routes.py` : endpoints
- `app/predictor.py` : parent + recommandations
- `app/explainer.py` : SHAP global/local
- `app/monte_carlo.py` : simulation + décision
- `app/genomic.py` : ODM/Base Editing + FASTA
- `app/utils/preprocessing.py` : preprocessing
- `app/models/wheat.py` : schémas Pydantic
- `scripts/save_models.py` : export modèles depuis notebook

## Installation

```bash
pip install -r requirements.txt
```

## Lancement

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test pipeline complet

```bash
curl -X POST http://localhost:8000/pipeline/full \
  -H "Content-Type: application/json" \
  -d '{"variety_name":"Khiar","recommendation_mode":"variety","n_simulations":1000}'
```

## Export des modèles depuis notebook Kaggle

Dans le notebook, après entraînement, sauvegarder tous les artefacts:

```python
import joblib, json, torch
from pathlib import Path
OUT = Path("models_weights")
OUT.mkdir(exist_ok=True)

joblib.dump(scaler, OUT / "scaler.pkl")
joblib.dump(ridge_model, OUT / "ridge.pkl")
joblib.dump(rf_model, OUT / "rf.pkl")
joblib.dump(xgb_model, OUT / "xgb.pkl")
joblib.dump(lgbm_model, OUT / "lgbm.pkl")
torch.save(mlp_model.state_dict(), OUT / "mlp.pt")
(OUT / "mlp_config.json").write_text(json.dumps({"input_dim":160,"output_dim":4,"dropout":0.3}))
joblib.dump(clf_parent, OUT / "clf_parent.pkl")
(OUT / "clf_parent_features.json").write_text(json.dumps(clf_parent_features))

df_preprocessed.to_csv(OUT / "df_preprocessed.csv", index=False)
crossings_df.to_csv(OUT / "crossings_df.csv", index=False)
```

Note: l'API est indépendante de Kaggle. Elle lit `models_weights/` et `data/` localement, avec fallback racine si les fichiers sont encore au root.
