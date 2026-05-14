import numpy as np
import wave
from tensorflow.keras.models import load_model
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "models" / "plant_stress_detector_IRA.keras"
model      = None

def load_cnn():
    global model
    if model is None:
        model = load_model(str(MODEL_PATH))
        print(f"CNN loaded: {MODEL_PATH}")
    return model

def load_wav(filepath: str) -> np.ndarray:
    with wave.open(filepath, 'r') as w:
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32)

def normalize(signal: np.ndarray) -> np.ndarray:
    return signal / (np.max(np.abs(signal)) + 1e-9)


def prepare_input(signal: np.ndarray) -> np.ndarray:
    sig_norm = normalize(signal)
    if len(sig_norm) < 1001:
        sig_norm = np.pad(sig_norm, (0, 1001 - len(sig_norm)))
    sig_norm = sig_norm[:1001]
    return sig_norm[np.newaxis, ..., np.newaxis].astype(np.float32)


def predict_stress_from_signal(signal: np.ndarray) -> dict:
    cnn = load_cnn()
    X = prepare_input(signal)
    pred = float(cnn.predict(X, verbose=0)[0][0])
    stress_type = "CUT" if pred >= 0.5 else "DRY"
    confidence = pred * 100 if pred >= 0.5 else (1 - pred) * 100
    return {
        "stress_type": stress_type,
        "confidence": round(confidence, 2),
        "raw_pred": round(pred, 4),
        "model_input": X.squeeze(-1).tolist(),
    }

def predict_stress(wav_path: str) -> dict:
    signal = load_wav(wav_path)
    return predict_stress_from_signal(signal)

def predict_from_array(signal: np.ndarray) -> dict:
    return predict_stress_from_signal(signal)