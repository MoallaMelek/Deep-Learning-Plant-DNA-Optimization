# 🌾 API G×E Blé Dur — Modélisation Phénologique LSTM/GRU

Pipeline FastAPI de prédiction des trajectoires génotype × environnement (G×E)
pour les hybrides F1 de blé dur (*Triticum durum*) en Tunisie méridionale.

---

## Structure du projet

```
project/
├── app/
│   ├── main.py              # Point d'entrée FastAPI
│   ├── routes.py            # Tous les endpoints (/predict, /recommend, /charts/…)
│   ├── predictor.py         # Logique centrale (prédiction + graphiques)
│   ├── config.py            # Chemins, constantes, labels
│   ├── models/
│   │   └── wheat.py         # Architectures HybridLSTM / HybridGRU
│   └── utils/
│       └── preprocessing.py # Stress climatique, build_lstm_input, recherche variété
├── models_weights/
│   ├── best_model.pth       # Poids du modèle GRU entraîné
│   └── model_artifacts.pkl  # Scalers, crossings_df, predictions, calibration
├── notebooks/
│   ├── you/
│   └── friend/
├── requirements.txt
└── README.md
```

---

## Installation

```bash
# Cloner / décompresser le projet
cd project

# Installer les dépendances
pip install -r requirements.txt
```

---

## Lancement

```bash
# Depuis la racine du projet
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Documentation interactive :** http://localhost:8000/docs  
**ReDoc :** http://localhost:8000/redoc

---

## Endpoints

### Système
| Méthode | Route | Description |
|---|---|---|
| GET | `/health` | Statut de l'API + modèle chargé |

### Dataset
| Méthode | Route | Description |
|---|---|---|
| GET | `/croisements` | Liste paginée des croisements (`?limit=50&offset=0`) |
| GET | `/varietes` | Toutes les variétés parentales |
| GET | `/stats` | Statistiques globales du dataset |

### Prédiction
| Méthode | Route | Description |
|---|---|---|
| POST | `/predict` | Trajectoire G×E T0→T7 pour un croisement custom |
| POST | `/recommend` | Top-N croisements pour une variété + poids agronomiques |

### Graphiques (HTML/PNG)
| Méthode | Route | Description |
|---|---|---|
| GET | `/charts/top5` | Barres — Top 5 croisements à maturité (T7) |
| GET | `/charts/distribution` | Histogramme rendements (kg/ha) |
| GET | `/charts/top10` | Top 10 croisements par rendement |
| GET | `/charts/trajectoire?croisement=…` | Trajectoire G×E 2×2 d'un croisement |
| GET | `/charts/variete?variete=KARIM&trait=yield` | Série temporelle par variété |

---

## Exemples

### Prédire une trajectoire
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "pred_drought": 0.72,
    "pred_salt": 0.65,
    "pred_yield": 0.80,
    "pred_disease": 0.70,
    "croisement": "KARIM x SIMETO"
  }'
```

### Recommander des croisements
```bash
curl -X POST "http://localhost:8000/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "variete_cible": "KARIM",
    "poids": {"yield": 0.40, "drought": 0.35, "salt": 0.15, "disease": 0.10},
    "top_n": 5
  }'
```

### Voir un graphique dans le navigateur
```
http://localhost:8000/charts/top5
http://localhost:8000/charts/distribution
http://localhost:8000/charts/top10
http://localhost:8000/charts/trajectoire?croisement=KARIM/SIMETO
http://localhost:8000/charts/variete?variete=KARIM&trait=drought
```

---

## Références scientifiques

- Zheng et al. (2012) — stress multiplicatif G×E, *Field Crops Research*
- Ferrise et al. (2010) — stades phénologiques blé dur Méditerranée
- White et al. (2011) — NASA POWER pour modèles agro-climatiques
- Hochreiter & Schmidhuber (1997) — LSTM, *Neural Computation*
- Boogaard et al. (2013) — WOFOST 7.1 User Guide, Wageningen UR
