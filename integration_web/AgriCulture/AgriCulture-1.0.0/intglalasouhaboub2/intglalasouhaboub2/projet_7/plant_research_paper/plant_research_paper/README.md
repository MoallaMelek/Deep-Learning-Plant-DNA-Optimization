# plant_research_paper API (FastAPI)

Backend API autonome pour génération de rapport scientifique multi-agent (PDF/TEX/JSON) à partir d’un sujet et d’une séquence ADN optionnelle.

## Architecture

```text
plant_research_paper/
├── app/
│   ├── main.py
│   ├── routes.py
│   ├── schemas.py
│   ├── predictor.py
│   ├── config.py
│   ├── agents/
│   ├── pipeline/
│   ├── services/
│   ├── utils/
│   └── models/
├── notebooks/
├── artifacts/
├── data/
│   └── chroma/
├── outputs/
├── tests/
├── requirements.txt
├── requirements-dnabert.txt
├── .env.example
├── .gitignore
├── run_api.py
└── test_api.py
```

## Prérequis

- Windows + VS Code
- Python `3.11.x` (ne pas utiliser `3.14`)
- Optionnel: `pdflatex` pour compilation LaTeX native

## Installation (VS Code / PowerShell)

```powershell
cd "c:\Users\Tliba\Documents\Esprit 3ia semestre 2\Integration pi ahmed\plant_research_paper"
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Option DNABERT (si compatible machine):

```powershell
python -m pip install -r requirements-dnabert.txt
```

## Variables d’environnement

Copier `.env.example` vers `.env` puis adapter si besoin.

## Lancer l’API

```powershell
python run_api.py
```

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

## Endpoints

- `GET /health`
- `POST /generate`
- `POST /generate/demo`

### Réponse `/generate`

Renvoie:
- `pdf_path`
- `tex_path`
- `json_path`
- `figure_paths`
- `summary` (résumé structuré)
- `fallbacks` (PubMed/NCBI/UniProt/pdflatex/DNABERT)
- `warnings`
- `report` complet

## Exemples curl (PowerShell)

```powershell
curl.exe -X GET "http://127.0.0.1:8000/health"
```

```powershell
curl.exe -X POST "http://127.0.0.1:8000/generate" `
  -H "Content-Type: application/json" `
  -d "{\"topic\":\"Drought resistance genes in maize\",\"dna_sequence\":\"ATGCGTACGTAGCTAGCTAGCTAGATGCGTACGTAGCTAGCTAGCTAG\",\"max_revision_rounds\":2}"
```

```powershell
curl.exe -X POST "http://127.0.0.1:8000/generate/demo"
```

## Test API rapide

```powershell
python test_api.py
```

Si `test_api.py` est lancé dans un autre terminal, garder `python run_api.py` actif en parallèle.

## Fallbacks robustes inclus

- PubMed indisponible: littérature placeholder locale
- NCBI indisponible: entrée fallback explicite
- UniProt indisponible: entrée fallback explicite
- `pdflatex` absent/erreur: PDF fallback généré automatiquement
- DNABERT absent: embedding déterministe de secours

## Tests unitaires

```powershell
pytest -q
```
