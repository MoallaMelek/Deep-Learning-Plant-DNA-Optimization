"""
main.py — Point d'entrée FastAPI
Pipeline G×E Blé Dur (Triticum durum) — Modélisation Phénologique LSTM/GRU
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.predictor import GxEPredictor


# ── Lifecycle : chargement unique du modèle au démarrage ─────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("⏳ Chargement du modèle et des artefacts...")
    app.state.predictor = GxEPredictor()
    print(f"✅ Modèle {app.state.predictor.best_model_name} prêt — "
          f"{len(app.state.predictor.crossings_df)} croisements chargés.")
    yield
    print("🔴 Arrêt de l'API.")


# ── Application FastAPI ───────────────────────────────────────────────────

app = FastAPI(
    title="🌾 API G×E Blé Dur — Modélisation Phénologique",
    description="""
## Pipeline de Modélisation Génotype × Environnement (G×E)

Prédit les **trajectoires phénologiques** des hybrides F1 de blé dur (*Triticum durum*)
en Tunisie méridionale, basé sur un modèle **GRU/LSTM** entraîné sur des données
climatiques **NASA POWER** et des traits génomiques (SNPs).

### Endpoints principaux
| Endpoint | Description |
|---|---|
| `POST /predict` | Prédit la trajectoire G×E T0→T7 d'un croisement |
| `POST /recommend` | Top-N croisements pour une variété donnée |
| `GET /charts/top5` | Graphique Top 5 croisements à maturité |
| `GET /charts/distribution` | Distribution des rendements (kg/ha) |
| `GET /charts/top10` | Top 10 rendements calibrés |
| `GET /charts/trajectoire` | Trajectoire G×E d'un croisement |
| `GET /charts/variete` | Série temporelle par variété |

### Références
- Zheng et al. (2012) — stress multiplicatif G×E, *Field Crops Research*
- Ferrise et al. (2010) — stades phénologiques blé dur Méditerranée
- White et al. (2011) — NASA POWER pour modèles agro-climatiques
- Hochreiter & Schmidhuber (1997) — LSTM, *Neural Computation*
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (dev) ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────
app.include_router(router)


# ── Lancement direct ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
