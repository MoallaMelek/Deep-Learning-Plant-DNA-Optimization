# Wheat Leaf Disease Classification API

REST API for wheat leaf classification:

- healthy
- dry
- diseased

## Project structure

```
app/
  main.py
  routes.py
  predictor.py
  config.py
  models/
    wheat_cnn.py
  utils/
    preprocessing.py
```

## Model file

Place your trained Keras model at:

`models/best_model.h5`

If your model is elsewhere, update `app/config.py` (`settings.model_path`).

## Install

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

## Usage

Health:

```bash
curl http://127.0.0.1:8000/health
```

Predict:

```bash
curl -X POST "http://127.0.0.1:8000/predict" ^
  -H "accept: application/json" ^
  -F "image=@path\to\leaf.jpg"
```

Response:

```json
{ "prediction": "healthy", "confidence": 0.95 }
```

