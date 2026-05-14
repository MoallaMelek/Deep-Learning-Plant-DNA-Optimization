from pathlib import Path
import wave
import numpy as np

SR = 500000
N_SAMPLES = 1001

def load_wav_signal(filepath: str) -> np.ndarray:
    path = Path(filepath)
    print(f"[PREPROC] Loading: {path}")
    print(f"[PREPROC] Exists: {path.exists()}")

    if not path.exists():
        print(f"[PREPROC] File not found — using synthetic signal")
        return _synthetic_signal()

    with wave.open(str(path), "rb") as wav_file:
        raw = wav_file.readframes(wav_file.getnframes())
    signal = np.frombuffer(raw, dtype=np.int16).astype(np.float32)

    if len(signal) < 1001:
        signal = np.pad(signal, (0, 1001 - len(signal)))
    print(f"[PREPROC] Loaded signal shape: {signal[:1001].shape}")
    return signal[:1001]


def denoise_signal(signal: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    if kernel_size < 3 or kernel_size % 2 == 0:
        return signal.astype(np.float32)
    kernel   = np.ones(kernel_size, dtype=np.float32) / float(kernel_size)
    denoised = np.convolve(signal, kernel, mode="same")
    # Normalize to [-1, 1]
    max_val = np.max(np.abs(denoised))
    if max_val > 0:
        denoised = denoised / max_val
    return denoised.astype(np.float32)


def _synthetic_signal() -> np.ndarray:
    """Generate a realistic synthetic cavitation pop for testing."""
    t      = np.linspace(0, 2e-3, N_SAMPLES)
    signal = np.sin(2 * np.pi * 50000 * t) * np.exp(-t / 5e-4)
    noise  = np.random.normal(0, 0.05, N_SAMPLES)
    return (signal + noise).astype(np.float32)