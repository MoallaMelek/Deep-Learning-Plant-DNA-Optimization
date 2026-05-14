# Plant DNA Protein Expression ML Project

This repository contains a FastAPI + Streamlit hybrid application for a plant DNA/protein expression ML workflow. It retrieves proteins from UniProt, generates host-optimized DNA, engineers sequence and structure features, builds a deterministic proxy target, and trains grouped regressors for Model Lab comparison.

The original Streamlit app and scientific pipeline are preserved. The `app/` package also exposes a FastAPI backend so a React frontend can integrate through stable JSON endpoints.

## Scientific Scope

The ML target is a simulated proxy score for comparative decision support. It is not wet-lab validated biological expression data, and the models must not be presented as real biological validation. Training uses protein-grouped splits to reduce accession-level leakage, and explainability/limitations notes should remain visible wherever scores or recommendations are shown.

## Project Structure

```text
app/
  main.py              FastAPI entry point
  routes.py            API endpoints
  predictor.py         Adapter to the existing pipeline
  config.py            Paths, defaults, CORS, model labels
  models/              Pydantic schemas and group placeholders
  utils/               Lightweight API helpers
  streamlit_app.py     Existing Streamlit UI, preserved
dataset_builder/       Source of truth for UniProt, DNA generation, features, proxy target, grouped training
src/                   Supporting scientific code
outputs/               Generated datasets, metrics, manifests, saved model artifacts
models_weights/        Optional group integration folder; existing joblib artifacts stay in outputs/
notebooks/you/         Notebook workspace
notebooks/friend/      Teammate notebook workspace
tests/                 Regression tests
```

## Generated Artifacts

The committed `outputs/datasets/` folder is intended to keep representative demo artifacts, latest-run files, metrics JSON, Model Lab JSON, and model-comparison CSV examples. Runtime caches, logs, and temporary test files are not required for integration and are ignored.

To regenerate artifacts:

```bash
python main.py --keyword receptor --protein-limit 180 --train
```

This writes updated files into `outputs/datasets/` and refreshes `latest_run_manifest.json`.

## Install

```bash
pip install -r requirements.txt
```

## Run Streamlit

```bash
streamlit run app/streamlit_app.py
```

## Run FastAPI

```bash
uvicorn app.main:app --reload
```

If `uvicorn` is not on your PATH after installation, run:

```bash
python -m uvicorn app.main:app --reload
```

Open the interactive API docs at `http://127.0.0.1:8000/docs`.

## API Endpoints

- `GET /health` checks that the API is running.
- `GET /models` lists Linear Regression, Ridge, Random Forest, XGBoost, and LightGBM with explanations and dependency availability.
- `GET /suggestions?q=ins` returns local protein keyword suggestions.
- `POST /run-pipeline` runs the existing `DatasetBuilder` pipeline and returns a JSON summary.
- `POST /predict` scores a fully engineered feature row if a compatible saved model exists; otherwise it returns a controlled explanation.
- `GET /latest-results` loads the latest manifest, metrics, quality report, and artifact paths when available.

## Example Requests

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/suggestions?q=ins"
curl http://127.0.0.1:8000/models
```

```bash
curl -X POST http://127.0.0.1:8000/run-pipeline \
  -H "Content-Type: application/json" \
  -d "{\"keyword\":\"insulin\",\"protein_limit\":20,\"model\":\"ridge\",\"priority\":\"balanced\"}"
```

```bash
curl http://127.0.0.1:8000/latest-results
```

## React Integration

React should call the FastAPI backend and consume JSON responses. A typical integration flow is:

1. Check `GET /health`.
2. Populate autocomplete from `GET /suggestions?q=...`.
3. Populate model choices from `GET /models`.
4. Start a run with `POST /run-pipeline`.
5. Display metrics and artifact links from the response or `GET /latest-results`.

Keep the proxy-target warning visible anywhere model scores or recommendations are shown.

## Run Checks

```bash
python -m compileall .
python -m unittest discover -s tests
```
