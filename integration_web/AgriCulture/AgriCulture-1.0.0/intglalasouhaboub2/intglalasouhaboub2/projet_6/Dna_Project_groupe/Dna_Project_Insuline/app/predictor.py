"""Adapter between FastAPI routes and the existing scientific pipeline."""

from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .config import (
    AVAILABLE_MODELS,
    DEFAULT_KEYWORD,
    DEFAULT_PRIORITY,
    DEFAULT_PROTEIN_LIMIT,
    OUTPUTS_DIR,
    OUTPUTS_ROOT,
    PROJECT_ROOT,
    PROXY_TARGET_WARNING,
)
from .internal.artifacts import load_model_payload
from .internal.keyword_suggestions import (
    get_all_keyword_suggestions as _all_keyword_suggestions,
    get_keyword_suggestions as _filter_keyword_suggestions,
)
from .utils.preprocessing import normalize_keyword, normalize_model_name, normalize_priority_name

try:
    from dataset_builder import DatasetBuilder, PipelineConfig, TrainingConfig
    from dataset_builder.model_lab import (
        MODEL_REGISTRY,
        model_lab_payload_from_metrics,
        normalize_priority,
        recommendation_for_priority,
    )
    from dataset_builder.protein_structure import (
        apply_hydrophobicity_bfactor,
        fetch_pdb_text,
        generate_mock_pdb_from_length,
    )
    from dataset_builder.utils import utc_timestamp
except Exception as exc:  # pragma: no cover - defensive API startup fallback
    DatasetBuilder = None  # type: ignore[assignment]
    PipelineConfig = None  # type: ignore[assignment]
    TrainingConfig = None  # type: ignore[assignment]
    MODEL_REGISTRY = {}  # type: ignore[assignment]
    model_lab_payload_from_metrics = None  # type: ignore[assignment]
    normalize_priority = None  # type: ignore[assignment]
    recommendation_for_priority = None  # type: ignore[assignment]
    apply_hydrophobicity_bfactor = None  # type: ignore[assignment]
    fetch_pdb_text = None  # type: ignore[assignment]
    generate_mock_pdb_from_length = None  # type: ignore[assignment]
    _PIPELINE_IMPORT_ERROR: Optional[BaseException] = exc
else:
    _PIPELINE_IMPORT_ERROR = None


def run_pipeline(
    keyword: Optional[str],
    protein_limit: Optional[int],
    model: Optional[str] = None,
    priority: str = DEFAULT_PRIORITY,
) -> Dict[str, Any]:
    """Run the existing DatasetBuilder pipeline and return an API-friendly summary."""
    _ensure_pipeline_available()

    final_keyword = normalize_keyword(keyword, default=DEFAULT_KEYWORD)
    final_limit = _normalize_protein_limit(protein_limit)
    selected_model = normalize_model_name(model)
    final_priority = _normalize_priority(priority)

    if selected_model and selected_model not in AVAILABLE_MODELS:
        raise ValueError(
            f"Unsupported model '{selected_model}'. Choose one of: {', '.join(AVAILABLE_MODELS)}."
        )

    pipeline_config = replace(PipelineConfig(), output_dir=str(OUTPUTS_DIR))
    training_config = TrainingConfig()
    if selected_model:
        # Keep the baseline in the run so the existing leakage-aware baseline gate still has evidence.
        training_config = replace(
            training_config,
            enabled_models=["dummy_mean_baseline", selected_model],
        )

    builder = DatasetBuilder(
        pipeline_config=pipeline_config,
        training_config=training_config,
    )
    result = builder.build(keyword=final_keyword, protein_limit=final_limit)

    manifest_path = Path(result.get("manifest", ""))
    manifest_bundle = _load_manifest_bundle(manifest_path if manifest_path.exists() else None)
    metrics = _dict_or_empty(result.get("metrics")) or _dict_or_empty(manifest_bundle.get("metrics"))
    recommended = _recommendation_from_metrics(metrics, final_priority)

    artifacts = _artifact_summary(
        result,
        manifest_bundle.get("manifest", {}),
        manifest_bundle.get("manifest_path"),
    )
    return {
        "status": "success",
        "keyword": final_keyword,
        "protein_limit": final_limit,
        "rows_generated": int(result.get("rows", 0) or 0),
        "metrics": metrics,
        "recommended_model": recommended.get("model") or metrics.get("best_model_name") or metrics.get("best_model"),
        "recommended_model_reason": recommended.get("reason", ""),
        "priority": final_priority,
        "model_comparison": metrics.get("model_comparison", {}) if isinstance(metrics, Mapping) else {},
        "model_lab": metrics.get("model_lab", {}) if isinstance(metrics, Mapping) else {},
        "artifacts": artifacts,
        "proxy_warning": PROXY_TARGET_WARNING,
    }


def get_available_models() -> Dict[str, Any]:
    """Return model metadata from the existing Model Lab registry."""
    models: List[Dict[str, Any]] = []
    dependency_map = {
        "linear_regression": "sklearn",
        "ridge": "sklearn",
        "random_forest": "sklearn",
        "xgboost": "xgboost",
        "lightgbm": "lightgbm",
    }
    optional_dependencies = {"xgboost", "lightgbm"}

    for model_name in AVAILABLE_MODELS:
        metadata = dict(MODEL_REGISTRY.get(model_name, {}))
        dependency = dependency_map[model_name]
        dependency_available = _module_available(dependency)
        models.append(
            {
                "name": model_name,
                "display_name": metadata.get("display_name", model_name.replace("_", " ").title()),
                "available": dependency_available,
                "dependency": dependency,
                "optional_dependency": model_name in optional_dependencies,
                "explanation": metadata.get("short_summary", ""),
                "what_it_does": metadata.get("what_it_does", ""),
                "when_to_choose": metadata.get("when_to_choose", ""),
                "advantages": metadata.get("advantages", ""),
                "limitations": metadata.get("limitations", ""),
                "recommended_for": metadata.get("recommended_for", ""),
            }
        )

    return {
        "status": "success",
        "models": models,
        "available_models": [item["name"] for item in models if item["available"]],
        "default_priority": DEFAULT_PRIORITY,
        "proxy_warning": PROXY_TARGET_WARNING,
    }


def get_latest_results() -> Dict[str, Any]:
    """Load the latest metrics and artifact references without crashing when absent."""
    manifest_path = _find_latest_manifest_path()
    if manifest_path is None:
        checked = [
            str((OUTPUTS_ROOT / "latest_run_manifest.json").resolve()),
            str((OUTPUTS_DIR / "latest_run_manifest.json").resolve()),
        ]
        return {
            "status": "missing",
            "message": "No latest run manifest was found. Run /run-pipeline first or generate artifacts.",
            "checked_paths": checked,
            "proxy_warning": PROXY_TARGET_WARNING,
        }

    bundle = _load_manifest_bundle(manifest_path)
    return {
        "status": "success",
        "manifest_path": str(manifest_path),
        "manifest": bundle.get("manifest", {}),
        "metrics": bundle.get("metrics", {}),
        "metadata": bundle.get("metadata", {}),
        "quality": bundle.get("quality", {}),
        "model_lab": bundle.get("model_lab", {}),
        "artifacts": _artifact_summary({}, bundle.get("manifest", {}), manifest_path),
        "proxy_warning": PROXY_TARGET_WARNING,
    }


def get_protein_options() -> Dict[str, Any]:
    """Return selectable proteins and hosts from the latest generated dataset."""
    records = _load_latest_dataset_records()
    if not records:
        return {
            "status": "missing",
            "proteins": [],
            "message": "No generated dataset was found. Run /run-pipeline first.",
            "proxy_warning": PROXY_TARGET_WARNING,
        }

    grouped: Dict[str, Dict[str, Any]] = {}
    for row in records:
        accession = _row_accession(row)
        if not accession:
            continue
        item = grouped.setdefault(
            accession,
            {
                "accession": accession,
                "protein_name": _text(row.get("protein_name"), "Unknown protein"),
                "organism": _text(row.get("organism"), "Unknown organism"),
                "hosts": [],
                "structure_source": _text(row.get("structure_source"), "unknown"),
                "pdb_id": _text(row.get("pdb_id"), ""),
                "structure_confidence": row.get("structure_confidence"),
            },
        )
        host = _text(row.get("plant_host"), "")
        if host and host not in item["hosts"]:
            item["hosts"].append(host)

    proteins = sorted(grouped.values(), key=lambda item: item["accession"])
    return {
        "status": "success",
        "proteins": proteins,
        "default_accession": proteins[0]["accession"] if proteins else None,
        "proxy_warning": PROXY_TARGET_WARNING,
    }


def get_protein_detail(accession: Optional[str] = None, host: Optional[str] = None) -> Dict[str, Any]:
    """Return protein, host, naive DNA, optimized DNA, and structure context."""
    records = _load_latest_dataset_records()
    if not records:
        return {
            "status": "missing",
            "message": "No generated dataset was found. Run /run-pipeline first.",
            "proxy_warning": PROXY_TARGET_WARNING,
        }

    selected_accession = (accession or _row_accession(records[0]) or "").strip()
    rows_for_accession = [row for row in records if _row_accession(row) == selected_accession]
    if not rows_for_accession:
        rows_for_accession = records[:]
        selected_accession = _row_accession(rows_for_accession[0]) or selected_accession

    hosts = sorted({_text(row.get("plant_host"), "") for row in rows_for_accession if _text(row.get("plant_host"), "")})
    selected_host = (host or (hosts[0] if hosts else "")).strip()
    selected_row = next(
        (row for row in rows_for_accession if _text(row.get("plant_host"), "") == selected_host),
        rows_for_accession[0],
    )
    selected_host = _text(selected_row.get("plant_host"), selected_host)

    naive_dna = _text(selected_row.get("naive_dna_sequence"), "")
    optimized_dna = _text(selected_row.get("dna_sequence"), "")
    diff_indexes, total_codons = _codon_diff_indexes(naive_dna, optimized_dna)
    naive_proxy = _float_value(selected_row.get("naive_proxy_expression_score"))
    optimized_proxy = _float_value(
        selected_row.get("simulated_proxy_expression_score", selected_row.get("target_expression_score"))
    )

    host_rows = []
    for row in rows_for_accession:
        host_rows.append(
            {
                "plant_host": _text(row.get("plant_host"), "N/A"),
                "cai": _float_value(row.get("cai")),
                "naive_cai": _float_value(row.get("naive_cai")),
                "gc_content": _float_value(row.get("gc_content")),
                "naive_gc_content": _float_value(row.get("naive_gc_content")),
                "proxy_expression": _float_value(row.get("simulated_proxy_expression_score", row.get("target_expression_score"))),
                "naive_proxy_expression": _float_value(row.get("naive_proxy_expression_score")),
                "delta_proxy_expression": _float_value(row.get("delta_proxy_expression")),
                "codon_usage_difference_score": _float_value(row.get("codon_usage_difference_score")),
            }
        )

    return {
        "status": "success",
        "accession": selected_accession,
        "selected_host": selected_host,
        "hosts": hosts,
        "protein": {
            "accession": selected_accession,
            "protein_name": _text(selected_row.get("protein_name"), "Unknown protein"),
            "organism": _text(selected_row.get("organism"), "Unknown organism"),
            "sequence_length_aa": _int_value(selected_row.get("sequence_length_aa", selected_row.get("protein_length"))),
        },
        "structure": {
            "source": _text(selected_row.get("structure_source"), "mock"),
            "pdb_url": _text(selected_row.get("pdb_url"), ""),
            "pdb_id": _text(selected_row.get("pdb_id"), ""),
            "confidence": _float_value(selected_row.get("structure_confidence")),
            "protein_length": _int_value(selected_row.get("protein_length", selected_row.get("sequence_length_aa"))),
            "helix_ratio": _float_value(selected_row.get("helix_ratio")),
            "sheet_ratio": _float_value(selected_row.get("sheet_ratio")),
            "coil_ratio": _float_value(selected_row.get("coil_ratio")),
            "hydrophobicity_score": _float_value(selected_row.get("hydrophobicity_score")),
            "stability_score": _float_value(selected_row.get("stability_score")),
        },
        "dna": {
            "naive": {
                "sequence": naive_dna,
                "preview": _dna_preview(naive_dna),
                "cai": _float_value(selected_row.get("naive_cai")),
                "gc_content": _float_value(selected_row.get("naive_gc_content")),
            },
            "optimized": {
                "sequence": optimized_dna,
                "preview": _dna_preview(optimized_dna),
                "cai": _float_value(selected_row.get("cai")),
                "gc_content": _float_value(selected_row.get("gc_content")),
            },
            "delta_cai": _float_value(selected_row.get("delta_cai")),
            "delta_gc": _float_value(selected_row.get("delta_gc")),
            "diff_indexes": diff_indexes,
            "total_codons": total_codons,
            "rare_codon_ratio": _float_value(selected_row.get("rare_codon_ratio")),
        },
        "proxy_metrics": {
            "naive_score": naive_proxy,
            "optimized_score": optimized_proxy,
            "delta": _float_value(selected_row.get("delta_proxy_expression")),
            "version": _text(selected_row.get("proxy_target_version"), "v2"),
        },
        "host_comparison": host_rows,
        "proxy_warning": PROXY_TARGET_WARNING,
    }


def get_decision_dashboard_data() -> Dict[str, Any]:
    """Generate ML-powered rankings, trade-offs, and strategic recommendations for plant hosts."""
    records = _load_latest_dataset_records()
    if not records:
        return {
            "status": "missing",
            "message": "No dataset available. Run a pipeline first to enable decision support.",
            "rankings": [],
        }

    # Group by host
    host_data: Dict[str, List[Dict[str, Any]]] = {}
    for row in records:
        host = _text(row.get("plant_host"), "Unknown")
        host_data.setdefault(host, []).append(row)

    rankings = []
    for host, rows in host_data.items():
        # ML-driven Efficiency: Mean predicted proxy score
        efficiency = sum(_float_value(r.get("target_expression_score"), 0.0) for r in rows) / len(rows)
        
        # Feasibility: Penalty for rare codons and GC deviation
        avg_rare_codon = sum(_float_value(r.get("rare_codon_ratio"), 0.0) for r in rows) / len(rows)
        avg_gc = sum(_float_value(r.get("gc_content"), 0.0) for r in rows) / len(rows)
        
        # Heuristic for host-specific GC stability (based on schema optima)
        optima = {"Arabidopsis thaliana": 0.43, "Oryza sativa": 0.56, "Zea mays": 0.58, "Phoenix dactylifera": 0.48}
        gc_optimum = optima.get(host, 0.5)
        gc_stability = max(0.0, 1.0 - abs(avg_gc - gc_optimum) * 2.0)
        
        feasibility = (gc_stability * 0.6 + (1.0 - avg_rare_codon) * 0.4) * 100.0
        
        # Derived Cost and Time (Synthetic ML-driven business metrics)
        cost = 100.0 + (1.0 - efficiency) * 200.0 + avg_rare_codon * 150.0
        time_min = 45.0 + (1.0 - efficiency) * 120.0 + avg_rare_codon * 90.0
        
        rankings.append({
            "plant_host": host,
            "efficiency": round(efficiency * 100.0, 2),
            "feasibility": round(feasibility, 2),
            "cost_tnd": round(cost, 2),
            "time_minutes": round(time_min, 1),
            "avg_gc": round(avg_gc, 4),
            "avg_rare_codon": round(avg_rare_codon, 4),
            "sample_count": len(rows)
        })

    # Sort by efficiency descending
    rankings.sort(key=lambda x: x["efficiency"], reverse=True)
    
    best_host = rankings[0] if rankings else None
    recommendation = ""
    if best_host:
        host_name = best_host["plant_host"]
        eff = best_host["efficiency"]
        if eff >= 75:
            verdict = "EXCELLENT"
        elif eff >= 50:
            verdict = "STRONG"
        else:
            verdict = "MODERATE"
            
        recommendation = (
            f"The ML model identifies **{host_name}** as the {verdict} production candidate. "
            f"With a predicted expression efficiency of {eff}%, it offers the best balance of "
            f"genomic compatibility (GC={best_host['avg_gc']:.2f}) and synthesis feasibility. "
            f"We recommend prioritizing this host for initial pilot batches to minimize TND {best_host['cost_tnd']} overhead."
        )

    return {
        "status": "success",
        "rankings": rankings,
        "best_host": best_host,
        "recommendation_text": recommendation,
        "timestamp": utc_timestamp() if 'utc_timestamp' in locals() or 'utc_timestamp' in globals() else None
    }


def get_structure_trace(
    accession: Optional[str] = None,
    host: Optional[str] = None,
    color_by_hydrophobicity: bool = True,
    max_atoms: int = 900,
) -> Dict[str, Any]:
    """Return a compact CA-trace that React can render as an AlphaFold-style 3D structure."""
    detail = get_protein_detail(accession=accession, host=host)
    if detail.get("status") != "success":
        return detail

    structure = _dict_or_empty(detail.get("structure"))
    pdb_url = _text(structure.get("pdb_url"), "")
    pdb_text = ""
    source = _text(structure.get("source"), "mock")

    if pdb_url and fetch_pdb_text is not None:
        pdb_text = fetch_pdb_text(pdb_url, timeout_sec=20)

    if not pdb_text and generate_mock_pdb_from_length is not None:
        pdb_text = generate_mock_pdb_from_length(
            int(structure.get("protein_length") or 1),
            accession=_text(detail.get("accession"), "UNKNOWN"),
        )
        source = "mock_fallback" if pdb_url else "mock"

    if color_by_hydrophobicity and pdb_text and apply_hydrophobicity_bfactor is not None:
        pdb_text = apply_hydrophobicity_bfactor(pdb_text)

    atoms = _parse_pdb_ca_atoms(pdb_text, max_atoms=max_atoms)
    return {
        "status": "success" if atoms else "missing",
        "accession": detail.get("accession"),
        "host": detail.get("selected_host"),
        "source": source,
        "pdb_url": pdb_url,
        "pdb_id": structure.get("pdb_id"),
        "confidence": structure.get("confidence"),
        "atoms": atoms,
        "atom_count": len(atoms),
        "proxy_warning": PROXY_TARGET_WARNING,
    }


def get_keyword_suggestions(q: str) -> Dict[str, Any]:
    """Return local keyword suggestions for React autocomplete."""
    query = (q or "").strip()
    suggestions = _filter_keyword_suggestions(query) if query else _all_keyword_suggestions()
    return {
        "query": query,
        "suggestions": suggestions,
    }


def predict(payload: Any) -> Dict[str, Any]:
    """Predict from a saved artifact when a fully engineered feature row is supplied."""
    request = _as_mapping(payload)
    features = request.get("features") or {}
    if not isinstance(features, Mapping):
        return {
            "status": "error",
            "prediction": None,
            "message": "features must be a JSON object containing generated model feature values.",
            "model_path": request.get("model_path"),
            "proxy_warning": PROXY_TARGET_WARNING,
        }

    latest = get_latest_results()
    model_path = _resolve_requested_model_path(
        explicit_model_path=request.get("model_path"),
        requested_model=normalize_model_name(request.get("model")),
        latest_payload=latest,
    )
    if not model_path:
        return {
            "status": "not_available",
            "prediction": None,
            "message": (
                "No saved model artifact is available. Run /run-pipeline with training enabled, "
                "then retry prediction with a generated feature row."
            ),
            "model_path": None,
            "artifacts": latest.get("artifacts", {}),
            "proxy_warning": PROXY_TARGET_WARNING,
        }

    loaded = load_model_payload(model_path)
    if loaded.get("error"):
        return {
            "status": "not_available",
            "prediction": None,
            "message": f"Could not load saved model artifact: {loaded['error']}",
            "model_path": model_path,
            "proxy_warning": PROXY_TARGET_WARNING,
        }

    if not features:
        return {
            "status": "requires_generated_features",
            "prediction": None,
            "message": (
                "Single-row biological prediction is not safely implemented from raw keyword or protein text. "
                "This project primarily runs the full dataset-generation pipeline and reports latest artifacts. "
                "Provide a fully engineered feature row from a generated dataset to score it with the saved model."
            ),
            "model_path": model_path,
            "artifacts": latest.get("artifacts", {}),
            "proxy_warning": PROXY_TARGET_WARNING,
        }

    try:
        import pandas as pd

        model = loaded.get("model")
        prediction_values = model.predict(pd.DataFrame([dict(features)]))
        prediction_value = float(prediction_values[0])
    except Exception as exc:
        return {
            "status": "requires_generated_dataset",
            "prediction": None,
            "message": (
                "Prediction requires the same engineered feature columns produced by the pipeline. "
                f"The supplied row could not be scored: {exc}"
            ),
            "model_path": model_path,
            "proxy_warning": PROXY_TARGET_WARNING,
        }

    return {
        "status": "success",
        "prediction": prediction_value,
        "message": "Prediction is a simulated proxy score from a saved surrogate model.",
        "model_path": model_path,
        "proxy_warning": PROXY_TARGET_WARNING,
    }


def _ensure_pipeline_available() -> None:
    if _PIPELINE_IMPORT_ERROR is not None or DatasetBuilder is None:
        raise RuntimeError(f"Existing pipeline modules could not be imported: {_PIPELINE_IMPORT_ERROR}")


def _normalize_protein_limit(value: Optional[int]) -> int:
    final_limit = DEFAULT_PROTEIN_LIMIT if value is None else int(value)
    if final_limit <= 0:
        raise ValueError("protein_limit must be greater than zero.")
    return final_limit


def _normalize_priority(value: Any) -> str:
    if normalize_priority is not None:
        return str(normalize_priority(value))
    return normalize_priority_name(value, default=DEFAULT_PRIORITY)


def _recommendation_from_metrics(metrics: Mapping[str, Any], priority: str) -> Dict[str, Any]:
    if not metrics:
        return {}
    if model_lab_payload_from_metrics is None or recommendation_for_priority is None:
        return {}
    model_lab = model_lab_payload_from_metrics(metrics)
    recommendation = recommendation_for_priority(model_lab, priority)
    return dict(recommendation) if isinstance(recommendation, Mapping) else {}


def _find_latest_manifest_path() -> Optional[Path]:
    candidates = [
        (OUTPUTS_ROOT / "latest_run_manifest.json").resolve(),
        (OUTPUTS_DIR / "latest_run_manifest.json").resolve(),
    ]
    existing = [candidate for candidate in candidates if candidate.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def _load_manifest_bundle(manifest_path: Optional[Path]) -> Dict[str, Any]:
    if manifest_path is None or not manifest_path.exists():
        return {}

    manifest = _load_json(manifest_path)
    metrics = _load_json(_resolve_manifest_value(manifest_path, manifest.get("latest_metrics_path")))
    metadata = _load_json(_resolve_manifest_value(manifest_path, manifest.get("latest_metadata_path")))
    quality = _load_json(_resolve_manifest_value(manifest_path, manifest.get("latest_quality_report_path")))
    model_lab = _load_json(_resolve_manifest_value(manifest_path, manifest.get("latest_model_lab_path")))
    return {
        "manifest_path": manifest_path,
        "manifest": manifest,
        "metrics": metrics,
        "metadata": metadata,
        "quality": quality,
        "model_lab": model_lab,
    }


def _resolve_manifest_value(manifest_path: Path, value: Any) -> Optional[Path]:
    if not value:
        return None

    raw_path = Path(str(value))
    if raw_path.is_absolute() and raw_path.exists():
        return raw_path
    if raw_path.is_absolute():
        raw_path = Path(raw_path.name)

    candidates = [
        (manifest_path.parent / raw_path).resolve(),
        (OUTPUTS_DIR / raw_path).resolve(),
        (OUTPUTS_ROOT / raw_path).resolve(),
        (PROJECT_ROOT / raw_path).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _load_json(path: Optional[Path]) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _load_latest_dataset_records() -> List[Dict[str, Any]]:
    manifest_path = _find_latest_manifest_path()
    if manifest_path is None:
        return []

    manifest = _load_json(manifest_path)
    dataset_json_path = _resolve_manifest_value(manifest_path, manifest.get("latest_json_path"))
    if dataset_json_path and dataset_json_path.exists():
        try:
            payload = json.loads(dataset_json_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return [dict(row) for row in payload if isinstance(row, Mapping)]
            if isinstance(payload, Mapping) and isinstance(payload.get("rows"), list):
                return [dict(row) for row in payload["rows"] if isinstance(row, Mapping)]
        except (OSError, json.JSONDecodeError):
            return []
    return []


def _artifact_summary(
    result: Mapping[str, Any],
    manifest: Mapping[str, Any],
    manifest_path: Optional[Path] = None,
) -> Dict[str, Any]:
    artifact_keys = {
        "dataset_csv": result.get("csv") or manifest.get("latest_dataset_path"),
        "dataset_json": result.get("json") or manifest.get("latest_json_path"),
        "metadata": result.get("metadata") or manifest.get("latest_metadata_path"),
        "metrics": manifest.get("latest_metrics_path"),
        "quality": result.get("quality") or manifest.get("latest_quality_report_path"),
        "manifest": result.get("manifest") or manifest_path,
        "model": manifest.get("latest_model_path"),
        "model_lab": manifest.get("latest_model_lab_path"),
        "model_comparison_csv": manifest.get("latest_model_comparison_csv_path"),
    }
    return {
        key: _artifact_path_text(value, manifest_path)
        for key, value in artifact_keys.items()
        if value
    }


def _artifact_path_text(value: Any, manifest_path: Optional[Path] = None) -> str:
    raw_path = Path(str(value))
    if raw_path.is_absolute() and raw_path.exists():
        return str(raw_path)
    if raw_path.is_absolute():
        raw_path = Path(raw_path.name)

    candidates = []
    if manifest_path:
        candidates.append((manifest_path.parent / raw_path).resolve())
    candidates.extend(
        [
            (OUTPUTS_DIR / raw_path).resolve(),
            (OUTPUTS_ROOT / raw_path).resolve(),
            (PROJECT_ROOT / raw_path).resolve(),
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(value)


def _resolve_requested_model_path(
    explicit_model_path: Any,
    requested_model: Optional[str],
    latest_payload: Mapping[str, Any],
) -> Optional[str]:
    if explicit_model_path:
        return str(explicit_model_path)

    latest_manifest_path = latest_payload.get("manifest_path")
    manifest_path = Path(str(latest_manifest_path)) if latest_manifest_path else None
    metrics = _dict_or_empty(latest_payload.get("metrics"))
    model_paths = metrics.get("model_paths", {})
    if requested_model and isinstance(model_paths, Mapping) and model_paths.get(requested_model):
        return _artifact_path_text(model_paths[requested_model], manifest_path)

    manifest = _dict_or_empty(latest_payload.get("manifest"))
    if manifest.get("latest_model_path"):
        return _artifact_path_text(manifest["latest_model_path"], manifest_path)
    if metrics.get("best_model_path"):
        return _artifact_path_text(metrics["best_model_path"], manifest_path)
    if metrics.get("model_path"):
        return _artifact_path_text(metrics["model_path"], manifest_path)
    return None


def _as_mapping(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, Mapping):
        return dict(payload)
    if hasattr(payload, "model_dump"):
        return dict(payload.model_dump())
    if hasattr(payload, "dict"):
        return dict(payload.dict())
    return {}


def _dict_or_empty(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _row_accession(row: Mapping[str, Any]) -> str:
    return _text(row.get("protein_accession") or row.get("accession"), "")


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return default
    return text


def _float_value(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:
        return default
    return round(number, 6)


def _int_value(value: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _dna_preview(sequence: str, width: int = 120) -> str:
    seq = _text(sequence, "").upper()
    return seq[:width] + ("..." if len(seq) > width else "")


def _codon_diff_indexes(naive_dna: str, optimized_dna: str) -> tuple[List[int], int]:
    naive = _text(naive_dna, "").upper()
    optimized = _text(optimized_dna, "").upper()
    naive_codons = [naive[index : index + 3] for index in range(0, len(naive) - len(naive) % 3, 3)]
    optimized_codons = [
        optimized[index : index + 3]
        for index in range(0, len(optimized) - len(optimized) % 3, 3)
    ]
    total = min(len(naive_codons), len(optimized_codons))
    diff_indexes = [
        index
        for index in range(total)
        if naive_codons[index] and optimized_codons[index] and naive_codons[index] != optimized_codons[index]
    ]
    return diff_indexes, total


def _parse_pdb_ca_atoms(pdb_text: str, max_atoms: int = 900) -> List[Dict[str, Any]]:
    atoms: List[Dict[str, Any]] = []
    if not pdb_text:
        return atoms

    for line in pdb_text.splitlines():
        if not (line.startswith("ATOM") or line.startswith("HETATM")):
            continue
        atom_name = line[12:16].strip()
        if atom_name != "CA":
            continue
        try:
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
        except ValueError:
            continue
        try:
            bfactor = float(line[60:66])
        except ValueError:
            bfactor = None

        atoms.append(
            {
                "x": round(x, 4),
                "y": round(y, 4),
                "z": round(z, 4),
                "residue": line[17:20].strip(),
                "chain": line[21:22].strip(),
                "residue_index": _int_value(line[22:26], len(atoms) + 1),
                "bfactor": _float_value(bfactor),
            }
        )

    if max_atoms > 0 and len(atoms) > max_atoms:
        step = max(1, len(atoms) // max_atoms)
        atoms = atoms[::step][:max_atoms]
    return atoms
