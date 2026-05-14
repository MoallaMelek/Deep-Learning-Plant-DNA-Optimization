from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:
    raise RuntimeError("Pillow manquant — lance : pip install Pillow") from exc

from app.config import MODELS_DIR

CNN_MODEL_FILE = "wheat_classifier.h5"
CNN_CLASSES = ["disease", "healthy", "stress"]
CNN_IMG_SIZE = (224, 224)


def load_cnn_model_if_available():
    try:
        import tensorflow as tf
    except Exception:
        return None, "tensorflow_not_installed"

    model_path = MODELS_DIR / CNN_MODEL_FILE
    if not model_path.exists():
        alt = MODELS_DIR.parent / CNN_MODEL_FILE
        model_path = alt if alt.exists() else model_path
    if not model_path.exists():
        return None, f"model_not_found:{model_path}"

    try:
        model = tf.keras.models.load_model(str(model_path))
        return model, "ok"
    except Exception as exc:
        return None, f"load_failed:{exc}"


def predict_cnn_from_bytes(image_bytes: bytes, cnn_model):
    import numpy as np

    img = Image.open(__import__('io').BytesIO(image_bytes)).convert("RGB")
    img = img.resize(CNN_IMG_SIZE)
    arr = np.array(img, dtype=np.float32) / 255.0
    x = np.expand_dims(arr, axis=0)
    probs = cnn_model.predict(x, verbose=0)[0]
    probs = probs.tolist()
    idx = int(np.argmax(probs))
    return {
        "predicted_class": CNN_CLASSES[idx],
        "confidence": float(probs[idx]),
        "probabilities": {c: float(p) for c, p in zip(CNN_CLASSES, probs)},
        "image_size": {"width": CNN_IMG_SIZE[0], "height": CNN_IMG_SIZE[1]},
    }
