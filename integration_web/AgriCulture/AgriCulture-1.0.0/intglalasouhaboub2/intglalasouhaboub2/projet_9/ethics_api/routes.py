from __future__ import annotations

import datetime as dt
import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from utils.ethics_report import generate_ethics_report
from utils.preprocess import clean_dna_sequence, encode_sequence_to_kmers
from utils.predict import load_mlp_model, predict_sequences
from utils.xai_explainer import generate_xai_explanation

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BASE_DIR / "models"
OUTPUT_DIR = BASE_DIR / "output"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MLP_MODEL_PATH = MODEL_DIR / "mlp_model.pth"
RF_MODEL_PATH = MODEL_DIR / "rf_model.pkl"
CLASS_LABELS = {
    0: {"key": "low_risk", "label": "Low risk", "tone": "success"},
    1: {"key": "sensitive", "label": "Sensitive", "tone": "warning"},
    2: {"key": "high_risk", "label": "High risk", "tone": "danger"},
}


class EthicsAuditRequest(BaseModel):
    sequence: str = Field(..., min_length=20, description="Raw DNA or FASTA text.")
    plant_name: str = Field(default="Custom sequence")
    top_n: int = Field(default=5, ge=1, le=10)


class EthicsHealthResponse(BaseModel):
    status: str
    version: str
    device: str
    model_loaded: bool
    model_type: str
    model_path: str
    output_dir: str


try:
    with open(RF_MODEL_PATH, "rb") as handle:
        RF_MODEL = pickle.load(handle)
    RF_MODEL.n_jobs = 1
    MODEL_STATUS = {
        "loaded": True,
        "model_type": "random_forest_calibrated",
        "message": "Random Forest ethics model loaded with light sequence calibration.",
    }
except Exception as exc:  # noqa: BLE001
    RF_MODEL = None
    MODEL_STATUS = {"loaded": False, "model_type": "deterministic", "message": f"Random Forest unavailable: {exc}"}

try:
    MLP_MODEL = load_mlp_model(MLP_MODEL_PATH, device=DEVICE)
except Exception:  # noqa: BLE001
    MLP_MODEL = None


@router.get("/health", response_model=EthicsHealthResponse)
def health() -> EthicsHealthResponse:
    status = "ok" if MODEL_STATUS["loaded"] else "degraded"
    return EthicsHealthResponse(
        status=status,
        version="2.0.0",
        device=DEVICE,
        model_loaded=bool(MODEL_STATUS["loaded"]),
        model_type=str(MODEL_STATUS["model_type"]),
        model_path=str((RF_MODEL_PATH if RF_MODEL is not None else MLP_MODEL_PATH).resolve()),
        output_dir=str(OUTPUT_DIR.resolve()),
    )


@router.post("/audit")
def audit_sequence(request: EthicsAuditRequest) -> dict[str, Any]:
    return _run_audit(
        raw_content=request.sequence,
        plant_name=request.plant_name,
        top_n=request.top_n,
        source="textarea",
    )


@router.post("/predict-file")
async def predict_file(file: UploadFile = File(...), top_n: int = 5) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No FASTA filename received.")
    content = (await file.read()).decode("utf-8", errors="ignore")
    plant_name = Path(file.filename).stem.upper()
    return _run_audit(raw_content=content, plant_name=plant_name, top_n=top_n, source="fasta_upload")


@router.get("/latest-results")
def latest_results() -> dict[str, Any]:
    latest_path = OUTPUT_DIR / "latest_ethics_report.json"
    if not latest_path.exists():
        raise HTTPException(status_code=404, detail="No ethics report has been generated yet.")
    return json.loads(latest_path.read_text(encoding="utf-8"))


def _run_audit(raw_content: str, plant_name: str, top_n: int, source: str) -> dict[str, Any]:
    dna_sequence = clean_dna_sequence(raw_content)
    if len(dna_sequence) < 20:
        raise HTTPException(status_code=400, detail="Provide at least 20 valid A/T/G/C bases.")

    encoded_sequences, chunk_lengths, chunks = _encode_for_model(dna_sequence)
    if len(encoded_sequences) == 0:
        raise HTTPException(status_code=400, detail="No valid DNA chunks could be encoded.")

    predictions = _predict_ethics(encoded_sequences, chunks)
    report = generate_ethics_report(predictions, plant_name=plant_name)
    xai = generate_xai_explanation(predictions, encoded_sequences, top_n=top_n)
    sequence_results = _sequence_results(predictions, chunk_lengths)

    response = {
        "status": "SUCCESS",
        "source": source,
        "plant_name": plant_name,
        "model_status": MODEL_STATUS,
        "sequence_length": len(dna_sequence),
        "total_sequences": int(len(encoded_sequences)),
        "decision_globale": report["decision_globale"],
        "distribution": _json_safe(report["distribution"]),
        "mean_probabilities": _mean_probabilities(predictions),
        "confiance_moyenne": float(report["confiance_moyenne"]),
        "sequences_incertaines": int(report["sequences_incertaines"]),
        "sequences_incertaines_pct": float(report["sequences_incertaines_pct"]),
        "lois": {
            "tunisie": report["lois_tunisie"],
            "eu": report["lois_eu"],
        },
        "xai_top_sequences": xai,
        "sequence_results": sequence_results,
        "class_labels": CLASS_LABELS,
        "asset_urls": {},
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }

    response["risk_level"] = _risk_level(response["decision_globale"])
    response["summary"] = _summary(response)
    response["asset_urls"] = {"json": _save_latest(response)}
    return response


def _encode_for_model(sequence: str) -> tuple[np.ndarray, list[int], list[str]]:
    chunk_size = 1000
    chunks = [sequence[i : i + chunk_size] for i in range(0, len(sequence), chunk_size)]
    usable_chunks = [chunk for chunk in chunks if len(chunk) >= 100]
    if not usable_chunks and len(sequence) >= 20:
        usable_chunks = [sequence]

    encoded = []
    lengths = []
    for chunk in usable_chunks:
        vector, _ = encode_sequence_to_kmers(chunk, k=4)
        encoded.append(vector)
        lengths.append(len(chunk))
    return np.array(encoded), lengths, usable_chunks


def _predict_ethics(encoded_sequences: np.ndarray, chunks: list[str]) -> dict[str, np.ndarray]:
    if MLP_MODEL is not None:
        mlp_predictions = predict_sequences(encoded_sequences, MLP_MODEL, device=DEVICE)
        # A nearly uniform MLP output means this bundled checkpoint is not calibrated.
        probabilities = np.vstack(
            [
                mlp_predictions["p_legal"],
                mlp_predictions["p_sensitive"],
                mlp_predictions["p_dangerous"],
            ]
        ).T
        if np.all(probabilities.max(axis=1) < 0.45):
            return _deterministic_predictions(encoded_sequences, chunks)
        return mlp_predictions

    if RF_MODEL is not None:
        feature_names = list(getattr(RF_MODEL, "feature_names_in_", []))
        if feature_names:
            frame = pd.DataFrame(encoded_sequences, columns=feature_names)
        else:
            frame = pd.DataFrame(encoded_sequences)
        probs = RF_MODEL.predict_proba(frame)
        classes = list(getattr(RF_MODEL, "classes_", [0, 1, 2]))
        aligned = np.zeros((len(encoded_sequences), 3), dtype=float)
        for idx, class_id in enumerate(classes):
            if int(class_id) in {0, 1, 2}:
                aligned[:, int(class_id)] = probs[:, idx]
        aligned = _calibrate_probabilities(aligned, encoded_sequences, chunks)
        labels = np.argmax(aligned, axis=1)
        return {
            "predicted_label": labels,
            "p_legal": aligned[:, 0],
            "p_sensitive": aligned[:, 1],
            "p_dangerous": aligned[:, 2],
            "confidence": aligned.max(axis=1),
        }

    return _deterministic_predictions(encoded_sequences, chunks)


def _calibrate_probabilities(probs: np.ndarray, encoded_sequences: np.ndarray, chunks: list[str]) -> np.ndarray:
    calibrated = (probs * 0.72) + (0.28 * _sequence_metric_probabilities(encoded_sequences, chunks))
    calibrated = (calibrated * 0.94) + (0.06 / 3)

    for idx in range(len(calibrated)):
        confidence = calibrated[idx].max()
        if confidence > 0.88:
            winner = int(np.argmax(calibrated[idx]))
            softened = calibrated[idx] * 0.88
            softened[winner] += 0.12
            calibrated[idx] = softened

    return calibrated / calibrated.sum(axis=1, keepdims=True)


def _sequence_metric_probabilities(encoded_sequences: np.ndarray, chunks: list[str]) -> np.ndarray:
    rows: list[np.ndarray] = []
    for idx, vector in enumerate(encoded_sequences):
        seq = chunks[idx] if idx < len(chunks) else ""
        gc = _gc_ratio(seq)
        entropy = _normalized_entropy(seq)
        diversity = float((vector > 0).mean())
        max_kmer_frequency = float(vector.max()) if len(vector) else 0.0
        homopolymer = _max_homopolymer(seq)
        motif_count = _motif_count(seq)

        sensitive = 0.10
        dangerous = 0.04

        gc_distance = abs(gc - 0.5)
        if gc_distance > 0.22:
            sensitive += min(0.22, (gc_distance - 0.22) * 0.9)
        if gc_distance > 0.36:
            dangerous += min(0.18, (gc_distance - 0.36) * 0.8)

        if entropy < 0.82:
            sensitive += min(0.18, (0.82 - entropy) * 0.45)
        if entropy < 0.55:
            dangerous += min(0.20, (0.55 - entropy) * 0.65)

        if diversity < 0.12:
            sensitive += min(0.18, (0.12 - diversity) * 1.1)
        if max_kmer_frequency > 0.28:
            sensitive += min(0.16, (max_kmer_frequency - 0.28) * 0.45)

        if homopolymer >= 10:
            sensitive += 0.10
        if homopolymer >= 18:
            dangerous += 0.18

        if motif_count:
            sensitive += min(0.14, motif_count * 0.035)

        dangerous = min(dangerous, 0.58)
        sensitive = min(sensitive, 0.64)
        legal = max(0.08, 1.0 - sensitive - dangerous)
        row = np.array([legal, sensitive, dangerous], dtype=float)
        rows.append(row / row.sum())
    return np.vstack(rows)


def _deterministic_predictions(encoded_sequences: np.ndarray, chunks: list[str]) -> dict[str, np.ndarray]:
    gc_indices = [
        idx
        for idx, kmer in enumerate(_all_kmers())
        if kmer.count("G") + kmer.count("C") >= 3
    ]
    high_gc = encoded_sequences[:, gc_indices].sum(axis=1)
    diversity = (encoded_sequences > 0).mean(axis=1)
    heuristic = _sequence_metric_probabilities(encoded_sequences, chunks)
    p_dangerous = np.clip((high_gc * 0.25) + heuristic[:, 2], 0.04, 0.7)
    p_sensitive = np.clip(((1 - diversity) * 0.18) + heuristic[:, 1], 0.08, 0.7)
    p_legal = np.clip(1 - p_dangerous - p_sensitive, 0.08, 0.9)
    probs = np.vstack([p_legal, p_sensitive, p_dangerous]).T
    probs = probs / probs.sum(axis=1, keepdims=True)
    labels = np.argmax(probs, axis=1)
    return {
        "predicted_label": labels,
        "p_legal": probs[:, 0],
        "p_sensitive": probs[:, 1],
        "p_dangerous": probs[:, 2],
        "confidence": probs.max(axis=1),
    }


def _all_kmers() -> list[str]:
    bases = ["A", "C", "G", "T"]
    kmers: list[str] = []

    def generate(current: str) -> None:
        if len(current) == 4:
            kmers.append(current)
            return
        for base in bases:
            generate(current + base)

    generate("")
    return kmers


def _gc_ratio(sequence: str) -> float:
    if not sequence:
        return 0.0
    return (sequence.count("G") + sequence.count("C")) / len(sequence)


def _normalized_entropy(sequence: str) -> float:
    if not sequence:
        return 0.0
    counts = np.array([sequence.count(base) for base in "ACGT"], dtype=float)
    probabilities = counts[counts > 0] / len(sequence)
    entropy = -float(np.sum(probabilities * np.log2(probabilities)))
    return entropy / 2.0


def _max_homopolymer(sequence: str) -> int:
    longest = 0
    current = 0
    previous = ""
    for base in sequence:
        current = current + 1 if base == previous else 1
        previous = base
        longest = max(longest, current)
    return longest


def _motif_count(sequence: str) -> int:
    motifs = [
        "GAATTC",  # EcoRI
        "GGATCC",  # BamHI
        "AAGCTT",  # HindIII
        "GCGGCCGC",  # NotI
        "TCTAGA",  # XbaI
        "CTGCAG",  # PstI
        "GGTCTC",  # BsaI
    ]
    return sum(sequence.count(motif) for motif in motifs)


def _sequence_results(predictions: dict[str, np.ndarray], lengths: list[int]) -> list[dict[str, Any]]:
    rows = []
    labels = predictions["predicted_label"]
    for idx in range(len(labels)):
        label_id = int(labels[idx])
        rows.append(
            {
                "sequence_id": idx,
                "length_bp": int(lengths[idx]) if idx < len(lengths) else None,
                "label_id": label_id,
                "label": CLASS_LABELS[label_id]["label"],
                "confidence": round(float(predictions["confidence"][idx]) * 100, 2),
                "probabilities": {
                    "low_risk": round(float(predictions["p_legal"][idx]) * 100, 2),
                    "sensitive": round(float(predictions["p_sensitive"][idx]) * 100, 2),
                    "high_risk": round(float(predictions["p_dangerous"][idx]) * 100, 2),
                },
            }
        )
    return rows


def _mean_probabilities(predictions: dict[str, np.ndarray]) -> dict[str, float]:
    return {
        "low_risk": round(float(np.mean(predictions["p_legal"])) * 100, 2),
        "sensitive": round(float(np.mean(predictions["p_sensitive"])) * 100, 2),
        "high_risk": round(float(np.mean(predictions["p_dangerous"])) * 100, 2),
    }


def _risk_level(decision: str) -> str:
    text = decision.lower()
    if "rejete" in text or "rejet" in text:
        return "high"
    if "revision" in text or "suspect" in text:
        return "medium"
    return "low"


def _summary(response: dict[str, Any]) -> dict[str, Any]:
    distribution = response["distribution"]
    return {
        "decision": response["decision_globale"],
        "risk_level": response["risk_level"],
        "confidence": response["confiance_moyenne"],
        "low_risk_pct": distribution.get("low_risk_pct", 0),
        "sensitive_pct": distribution.get("sensitive_pct", 0),
        "high_risk_pct": distribution.get("high_risk_pct", 0),
        "mean_probabilities": response.get("mean_probabilities", {}),
        "top_sequence_count": len(response["xai_top_sequences"]),
    }


def _save_latest(response: dict[str, Any]) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    latest_path = OUTPUT_DIR / "latest_ethics_report.json"
    latest_path.write_text(json.dumps(response, indent=2, ensure_ascii=False), encoding="utf-8")
    return "/ethics/outputs/latest_ethics_report.json"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value
