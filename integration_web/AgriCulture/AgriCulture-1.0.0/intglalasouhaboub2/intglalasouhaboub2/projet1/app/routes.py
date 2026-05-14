from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.predictor import WheatPredictor
from app.utils.preprocessing import load_rgb_image, preprocess_image


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/predict")
async def predict(
    request: Request,
    image: UploadFile = File(...),
) -> dict[str, object]:
    if image.content_type is None or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Unsupported file type. Upload an image.")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty upload.")

    try:
        image_array = load_rgb_image(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not decode image: {e}") from e

    batch = preprocess_image(image_array)

    predictor: WheatPredictor | None = getattr(request.app.state, "predictor", None)
    if predictor is None:
        model_error = getattr(request.app.state, "model_error", None)
        if model_error:
            raise HTTPException(status_code=503, detail=f"Model unavailable: {model_error}")
        raise HTTPException(status_code=503, detail="Model not loaded.")

    predictor = request.app.state.wheat_predictor or request.app.state.predictor
    pred = predictor.predict(batch)

    return {"prediction": pred.label, "confidence": pred.confidence}