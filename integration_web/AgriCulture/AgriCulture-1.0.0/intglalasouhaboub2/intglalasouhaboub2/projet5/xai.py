"""
xai.py
IRA Greenhouse — Explainable AI Module
Computes signal importance maps for plant stress predictions.

Two approaches:
  1. Energy-based (fast, no model needed) — default
  2. GradCAM 1D (accurate, requires CNN model) — optional

Used in main.py when action is IRRIGATE_NOW or DRAINAGE_NEEDED.
"""

from pathlib import Path
from datetime import datetime
import numpy as np
import os

# ── Constants ─────────────────────────────────────────────────────────────────
SR        = 500000   # 500 kHz sample rate
N_SAMPLES = 1001     # signal length
XAI_DIR   = Path("artifacts") / "xai"

# ── Public API ────────────────────────────────────────────────────────────────

def compute_signal_importance_map(
    signal: np.ndarray,
    method: str = "energy",
    window: int = 32,
) -> np.ndarray:
    """
    Compute importance map for a plant sound signal.

    Parameters
    ----------
    signal : np.ndarray
        Normalized 1D signal (N_SAMPLES,)
    method : str
        "energy"  — fast, no model needed (default)
        "gradcam" — uses CNN model (more accurate)
    window : int
        Window size for energy method

    Returns
    -------
    np.ndarray
        Importance scores in [0, 1], shape (N_SAMPLES,)
    """
    if signal is None or signal.size == 0:
        return np.zeros(N_SAMPLES, dtype=np.float32)

    # Ensure correct length
    signal = _ensure_length(signal)

    if method == "gradcam":
        try:
            return _gradcam_importance(signal)
        except Exception as e:
            print(f"[XAI] GradCAM failed ({e}), falling back to energy method")

    return _energy_importance(signal, window)


def save_importance_map(
    importance_map: np.ndarray,
    plant_id: str,
    timestamp: str,
) -> str:
    """
    Save importance map as .npy file in artifacts/xai/.

    Parameters
    ----------
    importance_map : np.ndarray
        Importance scores from compute_signal_importance_map()
    plant_id : str
        Plant identifier (e.g. "plant_042")
    timestamp : str
        ISO timestamp string

    Returns
    -------
    str
        Path to saved file
    """
    if importance_map is None or importance_map.size == 0:
        print("[XAI] Empty importance map — not saving")
        return ""

    # Create output directory
    XAI_DIR.mkdir(parents=True, exist_ok=True)

    # Safe filename
    safe_ts     = timestamp.replace(":", "-").replace(" ", "T")
    filename    = f"{plant_id}_{safe_ts}_importance.npy"
    output_path = XAI_DIR / filename

    np.save(str(output_path), importance_map)
    print(f"[XAI] Saved importance map: {output_path}")
    return str(output_path)


def load_importance_map(filepath: str) -> np.ndarray:
    """Load a previously saved importance map."""
    path = Path(filepath)
    if not path.exists():
        print(f"[XAI] File not found: {filepath}")
        return np.array([], dtype=np.float32)
    return np.load(str(path))


def get_peak_time_ms(importance_map: np.ndarray) -> float:
    """
    Return the time (in ms) of the most important region.

    Useful for biological interpretation:
      DRY → peak near end (1.5-2.0ms)
      CUT → peak in middle (0.7-1.0ms)
    """
    if importance_map.size == 0:
        return 0.0
    peak_idx  = int(np.argmax(importance_map))
    peak_time = peak_idx / SR * 1000   # convert to ms
    return round(peak_time, 3)


def get_importance_summary(importance_map: np.ndarray) -> dict:
    """
    Compute summary statistics of the importance map.

    Returns
    -------
    dict with keys:
      peak_time_ms    — where the CNN focused most
      spread          — "concentrated" | "distributed"
      early_importance — mean importance in first 0.5ms
      late_importance  — mean importance in last 0.5ms
      biological_hint  — what the pattern suggests
    """
    if importance_map.size == 0:
        return {
            "peak_time_ms":     0.0,
            "spread":           "unknown",
            "early_importance": 0.0,
            "late_importance":  0.0,
            "biological_hint":  "No signal available",
        }

    peak_time_ms = get_peak_time_ms(importance_map)

    # Split signal at 0.5ms
    mid_idx = int(0.5 / 2.0 * N_SAMPLES)  # 0.5ms out of 2ms total
    early   = float(np.mean(importance_map[:mid_idx]))
    late    = float(np.mean(importance_map[mid_idx:]))

    # Determine spread
    std = float(np.std(importance_map))
    spread = "concentrated" if std < 0.2 else "distributed"

    # Biological interpretation
    if spread == "distributed":
        hint = (
            "Distributed cavitation pattern — consistent with "
            "gradual drought stress (DRY). Multiple small bubbles "
            "collapsing over time across the xylem."
        )
    else:
        hint = (
            "Concentrated burst pattern — consistent with "
            "physical cutting (CUT). Sudden air entry through "
            "all severed xylem tubes simultaneously."
        )

    return {
        "peak_time_ms":     peak_time_ms,
        "spread":           spread,
        "early_importance": round(early, 4),
        "late_importance":  round(late, 4),
        "biological_hint":  hint,
    }


# ── FastAPI-friendly wrapper ──────────────────────────────────────────────────

def run_xai_pipeline(
    signal: np.ndarray,
    plant_id: str,
    timestamp: str,
    method: str = "energy",
) -> dict:
    """
    Full XAI pipeline: compute + save + summarize.

    Called from main.py for urgent events.

    Returns
    -------
    dict with keys:
      gradcam_path   — path to saved .npy file
      peak_time_ms   — most important time point
      spread         — "concentrated" | "distributed"
      biological_hint — interpretation string
    """
    importance_map = compute_signal_importance_map(
        signal, method=method
    )
    gradcam_path = save_importance_map(
        importance_map, plant_id, timestamp
    )
    summary = get_importance_summary(importance_map)

    return {
        "gradcam_path":    gradcam_path,
        "peak_time_ms":    summary["peak_time_ms"],
        "spread":          summary["spread"],
        "biological_hint": summary["biological_hint"],
    }


# ── Private methods ───────────────────────────────────────────────────────────

def _energy_importance(
    signal: np.ndarray,
    window: int = 32,
) -> np.ndarray:
    """
    Energy-based importance map.

    Computes local energy (squared amplitude) in a sliding window.
    Fast, no model needed.

    Physics justification:
      High energy regions = cavitation events
      → important for stress classification
    """
    window  = max(1, min(window, signal.size))
    kernel  = np.ones(window, dtype=np.float32)

    # Squared signal = energy
    energy  = np.convolve(signal ** 2, kernel, mode="same")

    # Add first derivative (captures sharp transitions)
    diff    = np.abs(np.gradient(signal.astype(np.float64))).astype(np.float32)
    diff_e  = np.convolve(diff, kernel, mode="same")

    # Combine: 70% energy + 30% gradient
    combined = 0.7 * energy + 0.3 * diff_e

    # Normalize to [0, 1]
    max_val = float(np.max(combined))
    if max_val <= 0.0:
        return np.zeros_like(signal, dtype=np.float32)

    return (combined / max_val).astype(np.float32)


def _gradcam_importance(signal: np.ndarray) -> np.ndarray:
    """
    GradCAM-based importance map using the NB4 CNN model.

    Requires plant_stress_detector_IRA.keras to be loaded.
    Falls back to energy method if model unavailable.

    Based on:
      Selvaraju et al. (2017) — "Grad-CAM: Visual Explanations
      from Deep Networks via Gradient-based Localization"
    """
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    from tensorflow.keras.layers import Conv1D

    model_path = os.getenv(
        "MODEL_PATH", "models/plant_stress_detector_IRA.keras"
    )
    if not Path(model_path).exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    model = load_model(model_path)

    # Find last Conv1D layer
    last_conv_name = None
    for layer in reversed(model.layers):
        if isinstance(layer, Conv1D):
            last_conv_name = layer.name
            break

    if last_conv_name is None:
        raise ValueError("No Conv1D layer found in model")

    # Prepare input
    X = tf.cast(
        signal[np.newaxis, :N_SAMPLES, np.newaxis],
        tf.float32
    )

    # Forward pass with gradient tape
    with tf.GradientTape() as tape:
        current = X
        conv_watched = None
        for layer in model.layers:
            current = layer(current)
            if layer.name == last_conv_name:
                conv_watched = current
                tape.watch(conv_watched)

        prediction  = current
        pred_value  = float(prediction[0][0])
        # Use predicted class for gradient
        loss = prediction[0][0] if pred_value >= 0.5 \
               else 1.0 - prediction[0][0]

    # Compute gradients
    grads        = tape.gradient(loss, conv_watched)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 2))

    conv_out_np  = conv_watched.numpy()[0]   # (time, filters)
    pooled_np    = pooled_grads.numpy()      # (time,)

    # Weighted combination
    heatmap_conv = np.mean(
        conv_out_np * pooled_np[:, np.newaxis], axis=-1
    )
    heatmap_conv = np.maximum(heatmap_conv, 0)  # ReLU

    # Upsample to N_SAMPLES
    heatmap = np.interp(
        np.linspace(0, 1, N_SAMPLES),
        np.linspace(0, 1, len(heatmap_conv)),
        heatmap_conv,
    )

    # Normalize
    max_val = float(np.max(heatmap))
    if max_val > 0:
        heatmap = heatmap / max_val

    return heatmap.astype(np.float32)


def _ensure_length(signal: np.ndarray) -> np.ndarray:
    """Ensure signal has exactly N_SAMPLES points."""
    if len(signal) < N_SAMPLES:
        signal = np.pad(signal, (0, N_SAMPLES - len(signal)))
    return signal[:N_SAMPLES].astype(np.float32)