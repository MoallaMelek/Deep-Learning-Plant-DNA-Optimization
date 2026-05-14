"""Artifact and session-state helpers for the Streamlit frontend."""

from __future__ import annotations

import json
from pathlib import Path
from pickle import PickleError
from typing import Any, Dict, MutableMapping, Optional

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]


def abs_path(path_text: str) -> Path:
    raw_path = Path(path_text)
    if raw_path.is_absolute():
        return raw_path
    return (ROOT_DIR / raw_path).resolve()


def load_json(path: Optional[Path]) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def resolve_manifest_relative_path(
    manifest_path: Optional[Path],
    value: Optional[str],
) -> Optional[Path]:
    if not value:
        return None

    raw_path = Path(str(value))
    if raw_path.is_absolute():
        if raw_path.exists():
            return raw_path
        # When manifests contain stale absolute paths, attempt a local relocation.
        raw_path = Path(raw_path.name)

    candidates = []
    if manifest_path:
        candidates.append((manifest_path.parent / raw_path).resolve())
    candidates.extend(
        [
            (ROOT_DIR / raw_path).resolve(),
            (ROOT_DIR / "app" / raw_path).resolve(),
            (Path.cwd() / raw_path).resolve(),
        ]
    )

    if manifest_path and len(manifest_path.parents) >= 3:
        candidates.append((manifest_path.parents[2] / raw_path).resolve())

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if candidates else None


def resolve_manifest_path(
    output_dir: Optional[str],
    explicit_manifest: Optional[str] = None,
    strict_explicit: bool = False,
) -> Optional[Path]:
    if explicit_manifest:
        explicit_path = abs_path(explicit_manifest)
        if explicit_path.exists():
            return explicit_path
        if strict_explicit:
            return None

    if output_dir:
        output_manifest = (abs_path(output_dir) / "latest_run_manifest.json").resolve()
        if output_manifest.exists():
            return output_manifest

    fallback_candidates = [
        (ROOT_DIR / "outputs" / "datasets" / "latest_run_manifest.json").resolve(),
        (ROOT_DIR / "app" / "outputs" / "datasets" / "latest_run_manifest.json").resolve(),
    ]
    existing = [candidate for candidate in fallback_candidates if candidate.exists()]
    if not existing:
        return None

    # Prefer the most recently updated manifest when multiple fallback locations exist.
    return max(existing, key=lambda path: path.stat().st_mtime)


def load_artifacts_from_manifest(manifest_path: Path) -> Dict[str, Any]:
    manifest = load_json(manifest_path)
    if not manifest:
        raise FileNotFoundError(f"Could not load manifest JSON: {manifest_path}")

    def _from_manifest(key: str) -> Optional[Path]:
        return resolve_manifest_relative_path(manifest_path, manifest.get(key))

    dataset_path = _from_manifest("latest_dataset_path")
    metadata_path = _from_manifest("latest_metadata_path")
    quality_path = _from_manifest("latest_quality_report_path")
    metrics_path = _from_manifest("latest_metrics_path")

    try:
        dataset = pd.read_csv(dataset_path) if dataset_path and dataset_path.exists() else pd.DataFrame()
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        dataset = pd.DataFrame()

    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "dataset": dataset,
        "metadata": load_json(metadata_path),
        "quality": load_json(quality_path),
        "metrics": load_json(metrics_path),
        "paths": {
            "dataset": dataset_path,
            "metadata": metadata_path,
            "quality": quality_path,
            "metrics": metrics_path,
        },
    }


def init_session_state(session_state: MutableMapping[str, Any]) -> None:
    defaults = {
        "pipeline_result": None,
        "active_pipeline_params": {},
        "artifact_load_mode": None,
        "manifest": {},
        "manifest_path": None,
        "dataset": pd.DataFrame(),
        "metadata": {},
        "quality": {},
        "metrics": {},
        "artifact_paths": {},
    }
    for key, value in defaults.items():
        if key not in session_state:
            session_state[key] = value


def store_artifacts(
    session_state: MutableMapping[str, Any],
    payload: Dict[str, Any],
    load_mode: str = "manual_load",
) -> None:
    session_state["manifest"] = payload["manifest"]
    session_state["manifest_path"] = payload["manifest_path"]
    session_state["dataset"] = payload["dataset"]
    session_state["metadata"] = payload["metadata"]
    session_state["quality"] = payload["quality"]
    session_state["metrics"] = payload["metrics"]
    session_state["artifact_paths"] = payload["paths"]
    session_state["artifact_load_mode"] = load_mode


def clear_loaded_artifacts(session_state: MutableMapping[str, Any]) -> None:
    """Clear the current session artifacts so old runs cannot leak into later views."""
    session_state["pipeline_result"] = None
    session_state["active_pipeline_params"] = {}
    session_state["artifact_load_mode"] = None
    session_state["manifest"] = {}
    session_state["manifest_path"] = None
    session_state["dataset"] = pd.DataFrame()
    session_state["metadata"] = {}
    session_state["quality"] = {}
    session_state["metrics"] = {}
    session_state["artifact_paths"] = {}


def get_loaded_metrics(session_state: MutableMapping[str, Any]) -> Dict[str, Any]:
    if not session_state.get("artifact_load_mode") or not session_state.get("manifest_path"):
        return {}
    metrics = session_state.get("metrics", {})
    return metrics if isinstance(metrics, dict) else {}


def get_loaded_dataset(session_state: MutableMapping[str, Any]) -> pd.DataFrame:
    if not session_state.get("artifact_load_mode") or not session_state.get("manifest_path"):
        return pd.DataFrame()
    dataset = session_state.get("dataset", pd.DataFrame())
    if isinstance(dataset, pd.DataFrame) and not dataset.empty:
        return dataset
    return pd.DataFrame()


def load_model_payload(model_path_text: str) -> Dict[str, Any]:
    path = Path(model_path_text) if model_path_text else None
    if path is None or not path.exists():
        return {"payload": None, "model": None, "error": "Model file not found."}

    try:
        import joblib
    except ImportError as exc:
        return {"payload": None, "model": None, "error": str(exc)}

    try:
        payload = joblib.load(path)
        model = payload.get("model") if isinstance(payload, dict) else payload
        return {"payload": payload, "model": model, "error": None}
    except (AttributeError, EOFError, OSError, PickleError, TypeError, ValueError) as exc:
        return {"payload": None, "model": None, "error": str(exc)}
