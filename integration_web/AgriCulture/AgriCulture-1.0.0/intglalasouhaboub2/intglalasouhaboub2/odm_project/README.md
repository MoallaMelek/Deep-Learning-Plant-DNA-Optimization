# ODM Wheat FastAPI — v4

Pipeline ODM (Oligonucleotide-Directed Mutagenesis) pour *Triticum aestivum*.

## Structure

```
odm_project/
│
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── routes.py            # /predict  /health  /objectives
│   ├── predictor.py         # logique centrale du pipeline
│   ├── config.py            # paths, labels, defaults
│   │
│   ├── models/
│   │   └── wheat.py         # dataclasses + WHEAT_OBJECTIVES
│   │
│   └── utils/
│       └── preprocessing.py # nettoyage séquence, GC, conservation
│
├── models_weights/          # checkpoints fine-tunés (optionnel)
├── notebooks/
│   ├── you/
│   └── friend/
├── data/
│   └── odm/                 # Luo2020_Kim2019.xlsx ici (optionnel)
├── requirements.txt
└── README.md
```

## Démarrage rapide

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Lancer le serveur
uvicorn app.main:app --reload --port 8000
```

Docs interactives → http://localhost:8000/docs

## Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/health` | Statut + objectifs disponibles |
| GET | `/objectives` | Liste des objectifs agronomiques |
| POST | `/predict` | Pipeline complet → oligos ODM |

## Exemple d'appel

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": "ATGGTCAAGACCTTCATCAACGAGCTGGAGCTGGAGCACATCGACAACATCCAGAGCAAGGACCTGGTCATCGACAAGAAGTTCGGCGAGCAGGTCATCACCAAGCTCAAGGCCAAGCTGGACAAGGTCAAGGACCAGCTCAACAAGGCCATCATCGAGCAGCTCAAGGCCAAGATCGAC",
    "objective": "herbicide_tolerance",
    "top_n": 5
  }'
```

## Objectifs disponibles

| Clé | Trait | Gènes cibles |
|-----|-------|-------------|
| `disease_resistance` | Résistance fongique | TaMLO, TaPR1 |
| `yield_improvement` | Rendement / poids grain | TaGW2, TaGW5 |
| `herbicide_tolerance` | Tolérance herbicides | TaALS, TaACCase |
| `drought_tolerance` | Tolérance sécheresse | TaDREB1, TaABF1 |
| `starch_quality` | Qualité amidon | TaWaxy, TaSSIIa |
