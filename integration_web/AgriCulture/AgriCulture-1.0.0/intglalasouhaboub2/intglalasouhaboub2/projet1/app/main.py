from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.models.wheat_cnn import load_wheat_model
from app.predictor import WheatPredictor
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.predictor = None
    app.state.model_error = None

    try:
        model = load_wheat_model(settings.model_path)
        app.state.predictor = WheatPredictor(model)
    except Exception as e:  # noqa: BLE001
        # Don't crash the app if model/tensorflow is missing.
        # /predict will return 503 until the model is available.
        app.state.model_error = str(e)
    yield


app = FastAPI(title="Wheat Leaf Disease Classifier", version="1.0.0", lifespan=lifespan)
app.include_router(router)

