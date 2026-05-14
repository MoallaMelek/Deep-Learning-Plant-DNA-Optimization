# plant_simulator API (FastAPI)

Backend API autonome pour prédiction de croissance de plante à partir d’ADN + climat (Open-Meteo ou manuel), avec entraînement ML et simulation optionnelle GIF.

## Architecture

```text
plant_simulator/
├── app/
│   ├── main.py
│   ├── routes.py
│   ├── schemas.py
│   ├── predictor.py
│   ├── config.py
│   ├── models/
│   ├── services/
│   └── utils/
├── data/
├── ml/
├── simulation/
├── artifacts/
├── outputs/
├── media/
├── notebooks/
├── legacy/              # ancien Django/Tkinter (si conservé)
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py
└── test_api.py
```

## Prérequis

- Windows + VS Code
- Python `3.11.x` (ne pas utiliser `3.14`)

## Installation (VS Code / PowerShell)

```powershell
cd "c:\Users\Tliba\Documents\Esprit 3ia semestre 2\Integration pi ahmed\plant_simulator"
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Lancer l’API

```powershell
python main.py
```

- API: `http://127.0.0.1:8001`
- Swagger: `http://127.0.0.1:8001/docs`

## Endpoints

- `GET /health`
- `POST /predict-growth`
- `POST /train`
- `POST /simulate`

### Réponse `/predict-growth`

Renvoie:
- prédictions jour par jour
- résumé final (`height`, `leaf_count`, `branch_count`, `health`)
- `dna_source`
- `climate_source`
- `chart_path` et/ou `chart_base64`
- `warnings`

### Fallback modèle

Si `artifacts/growth_model.pt` est absent:
- `auto_train_if_missing=true` => entraînement automatique
- sinon => message d’erreur clair

## Exemples curl (PowerShell)

```powershell
curl.exe -X GET "http://127.0.0.1:8001/health"
```

```powershell
curl.exe -X POST "http://127.0.0.1:8001/train" `
  -H "Content-Type: application/json" `
  -d "{\"epochs\":30,\"batch_size\":256,\"learning_rate\":0.001}"
```

```powershell
curl.exe -X POST "http://127.0.0.1:8001/predict-growth" `
  -H "Content-Type: application/json" `
  -d "{\"days\":60,\"use_open_meteo\":true,\"auto_train_if_missing\":true,\"generate_chart\":true,\"chart_as_base64\":false,\"dna_sequence\":\"ATGGCTTCTTCTTCTGCTTCTCCGTTGCTGCTGCTGTTGATGGTGGTGATGCTGCTGATGATGCTGATGCTGATGTTGCTGATGATGCTGCTGCTGATGCTGATGATGCTGATGATGCTGATGATGCTGATGATGCTGATGATGCTGCTGATGATGCTGATGATGCTGCTGATGATGCTGCTGATGAT\"}"
```

```powershell
curl.exe -X POST "http://127.0.0.1:8001/simulate" `
  -H "Content-Type: application/json" `
  -d "{\"days\":45,\"use_open_meteo\":true,\"auto_train_if_missing\":true,\"generate_chart\":true,\"chart_as_base64\":false,\"generate_gif\":true,\"gif_filename\":\"latest_growth.gif\"}"
```

## Test API rapide

```powershell
python test_api.py
```
