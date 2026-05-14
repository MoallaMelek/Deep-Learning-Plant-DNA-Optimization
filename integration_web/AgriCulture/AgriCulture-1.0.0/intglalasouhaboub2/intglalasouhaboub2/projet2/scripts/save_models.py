import json
from pathlib import Path

import joblib
import pandas as pd


# Exemple de script d'export depuis un notebook Kaggle vers models_weights/
# Adapter les variables ridge_model, rf_model, xgb_model, lgbm_model, mlp_model,
# scaler, clf_parent, clf_parent_features selon vos objets en mémoire.

OUT = Path("models_weights")
OUT.mkdir(exist_ok=True)


def save_metadata(df_preprocessed: pd.DataFrame):
    snp_cols = [c for c in df_preprocessed.columns if c.startswith("SNP")]
    metadata = {
        "snp_cols": snp_cols,
        "feature_cols": snp_cols + ["snp_activity"],
        "target_cols": ["drought", "salt", "yield", "disease"],
    }
    (OUT / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


# Exemple d'usage (decommenter dans notebook):
# joblib.dump(scaler, OUT / "scaler.pkl")
# joblib.dump(ridge_model, OUT / "ridge.pkl")
# joblib.dump(rf_model, OUT / "rf.pkl")
# joblib.dump(xgb_model, OUT / "xgb.pkl")
# joblib.dump(lgbm_model, OUT / "lgbm.pkl")
# torch.save(mlp_model.state_dict(), OUT / "mlp.pt")
# (OUT / "mlp_config.json").write_text(json.dumps({"input_dim":160,"output_dim":4,"dropout":0.3}))
# joblib.dump(clf_parent, OUT / "clf_parent.pkl")
# (OUT / "clf_parent_features.json").write_text(json.dumps(clf_parent_features))
# df_preprocessed.to_csv(OUT / "df_preprocessed.csv", index=False)
# crossings_df.to_csv(OUT / "crossings_df.csv", index=False)
# save_metadata(df_preprocessed)
