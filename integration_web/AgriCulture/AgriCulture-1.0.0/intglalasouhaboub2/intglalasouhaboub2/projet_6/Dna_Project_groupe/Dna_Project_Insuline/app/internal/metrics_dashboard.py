"""Metrics dashboard helpers extracted from the Streamlit entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dataset_builder.model_lab import (
    DEFAULT_PRIORITY,
    annotate_model_comparison,
    display_model_name,
    display_priority_name,
    get_model_metadata,
    list_supported_models,
    model_lab_payload_from_metrics,
    normalize_priority,
    recommendation_for_priority,
)
from dataset_builder.config import TrainingConfig
from dataset_builder.grouped_training import train_model_grouped_impl

from .artifacts import (
    get_loaded_dataset,
    get_loaded_metrics,
    load_model_payload,
    resolve_manifest_relative_path,
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_text(value: Any, default: str = "N/A") -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else default


def _to_percent(value: Any, default: float = 0.0) -> float:
    numeric = _safe_float(value, default=default)
    return numeric * 100.0 if numeric <= 1.5 else numeric


def _fmt_dashboard_metric(value: Any, ndigits: int = 4) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "N/A"
    return f"{float(numeric):.{ndigits}f}"


def _fmt_dashboard_pct(value: Any, ndigits: int = 2) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "N/A"
    return f"{float(numeric):.{ndigits}f}%"


def _fmt_duration_seconds(value: Any) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "N/A"
    return f"{float(numeric):.4f}s"


def load_metrics() -> Dict[str, Any]:
    """Load only the metrics explicitly loaded in the current Streamlit session."""
    return get_loaded_metrics(st.session_state)


def load_metrics_dataset() -> pd.DataFrame:
    """Return the dataset explicitly loaded in the current Streamlit session."""
    return get_loaded_dataset(st.session_state)


def _model_lab_payload(metrics: Dict[str, Any]) -> Dict[str, Any]:
    return model_lab_payload_from_metrics(metrics)


def _model_payload_from_session(model_name: str) -> Dict[str, Any]:
    payloads = st.session_state.get("metrics_lab_model_payloads", {}) or {}
    payload = payloads.get(str(model_name)) if isinstance(payloads, dict) else None
    if not isinstance(payload, dict):
        return {"payload": None, "model": None, "error": "No in-session model payload."}
    return {"payload": payload, "model": payload.get("model"), "error": None}


def _merge_single_model_training_run(
    base_metrics: Dict[str, Any],
    run_metrics: Dict[str, Any],
    selected_model: str,
    models_to_merge: Optional[List[str]] = None,
) -> Dict[str, Any]:
    merged = dict(base_metrics)
    base_comparison = base_metrics.get("model_comparison", {})
    run_comparison = run_metrics.get("model_comparison", {})
    merged_comparison: Dict[str, Dict[str, Any]] = {
        str(model_name): dict(model_metrics)
        for model_name, model_metrics in (base_comparison.items() if isinstance(base_comparison, dict) else [])
        if isinstance(model_metrics, dict)
    }
    if isinstance(run_comparison, dict):
        merge_models = models_to_merge or ["dummy_mean_baseline", selected_model]
        for model_name in merge_models:
            model_metrics = run_comparison.get(model_name)
            if isinstance(model_metrics, dict):
                merged_comparison[str(model_name)] = dict(model_metrics)

    annotated_comparison, model_lab_payload = annotate_model_comparison(
        merged_comparison,
        unavailable_models=run_metrics.get("unavailable_models", base_metrics.get("unavailable_models", [])),
    )
    merged["model_comparison"] = annotated_comparison
    merged["model_lab"] = model_lab_payload
    merged["priority_recommendations"] = model_lab_payload.get("priority_recommendations", {})
    merged["recommended_model_by_default_priority"] = (
        recommendation_for_priority(model_lab_payload, DEFAULT_PRIORITY).get("model")
    )
    merged["single_model_training"] = {
        "active": True,
        "selected_model": selected_model,
        "models_trained": run_metrics.get("models_trained", []),
        "evaluation_protocol": run_metrics.get("evaluation_protocol"),
        "train_test_group_overlap_count": run_metrics.get("train_test_group_overlap_count"),
        "fit_validation_group_overlap_count": run_metrics.get("fit_validation_group_overlap_count"),
        "note": (
            "Only the selected model and dummy baseline were retrained from the currently loaded dataset. "
            "Other comparison rows remain from the loaded artifact set."
        ),
    }
    for key in (
        "evaluation_protocol",
        "group_column",
        "target_column",
        "train_test_group_overlap_count",
        "fit_validation_group_overlap_count",
        "credibility_checks",
        "feature_selection",
        "feature_roles",
        "feature_names",
        "numeric_feature_names",
        "categorical_feature_names",
        "encoded_feature_names",
    ):
        if key in run_metrics:
            merged[key] = run_metrics[key]
    return merged


def _train_selected_model_for_lab(
    dataset: pd.DataFrame,
    metrics: Dict[str, Any],
    selected_model: str,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Dict[str, Any]], str]:
    if dataset.empty:
        return None, {}, "The current dataset is not loaded."
    if selected_model not in list_supported_models():
        return None, {}, f"{_display_name_for_ui(selected_model)} is not a supported classical model."

    metadata = st.session_state.get("metadata", {}) or {}
    random_state = _safe_int(
        metadata.get("random_seed", metrics.get("random_seed")),
        default=42,
    )
    training_config = TrainingConfig(
        enabled=True,
        enabled_models=["dummy_mean_baseline", selected_model],
        random_state=random_state,
        hyperparameter_search=True,
        save_model=False,
    )
    run_metrics, model_payloads = train_model_grouped_impl(
        dataset.replace({np.nan: None}).to_dict(orient="records"),
        training_config,
    )
    if run_metrics.get("skipped") or run_metrics.get("error"):
        return None, {}, str(run_metrics.get("reason") or run_metrics.get("error") or "Training did not produce metrics.")
    if selected_model not in run_metrics.get("model_comparison", {}):
        return None, {}, f"{_display_name_for_ui(selected_model)} could not be trained in this environment."
    return _merge_single_model_training_run(metrics, run_metrics, selected_model), model_payloads, ""


def _train_selected_model_now(
    dataset: pd.DataFrame,
    metrics: Dict[str, Any],
    selected_model: str,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Dict[str, Any]], str]:
    if dataset.empty:
        return None, {}, "The current dataset is not loaded."
    if selected_model not in list_supported_models():
        return None, {}, f"{_display_name_for_ui(selected_model)} is not a supported classical model."

    metadata = st.session_state.get("metadata", {}) or {}
    random_state = _safe_int(
        metadata.get("random_seed", metrics.get("random_seed")),
        default=42,
    )
    training_config = TrainingConfig(
        enabled=True,
        enabled_models=[selected_model],
        random_state=random_state,
        hyperparameter_search=True,
        save_model=False,
    )
    run_metrics, model_payloads = train_model_grouped_impl(
        dataset.replace({np.nan: None}).to_dict(orient="records"),
        training_config,
    )
    if run_metrics.get("skipped") or run_metrics.get("error"):
        return None, {}, str(run_metrics.get("reason") or run_metrics.get("error") or "Training did not produce metrics.")
    if selected_model not in run_metrics.get("model_comparison", {}):
        return None, {}, f"{_display_name_for_ui(selected_model)} could not be trained in this environment."
    merged = _merge_single_model_training_run(
        metrics,
        run_metrics,
        selected_model,
        models_to_merge=[selected_model],
    )
    return merged, model_payloads, ""


def _unavailable_models_for_ui(model_lab: Dict[str, Any]) -> Dict[str, str]:
    unavailable: Dict[str, str] = {}
    for row in model_lab.get("supported_models", []):
        if not isinstance(row, dict):
            continue
        model_name = str(row.get("model", "")).strip()
        if not model_name or row.get("available"):
            continue
        unavailable[model_name] = str(row.get("unavailable_reason", "")).strip()
    return unavailable


def _display_name_for_ui(model_name: str) -> str:
    return "Dummy Mean Baseline" if model_name == "dummy_mean_baseline" else display_model_name(model_name)


def _model_metrics_from_metrics(metrics: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    model_comparison = metrics.get("model_comparison", {})
    if isinstance(model_comparison, dict):
        payload = model_comparison.get(model_name)
        if isinstance(payload, dict):
            return dict(payload)
    return dict(metrics if model_name == str(metrics.get("best_model_name") or metrics.get("best_model") or "") else {})


def _metrics_with_prediction_vectors(selected_metrics: Dict[str, Any], fallback_metrics: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("test_actual_values", "actual_values", "validation_actual_values"):
        values = selected_metrics.get(key)
        if isinstance(values, list) and values:
            return selected_metrics
    return fallback_metrics


def _resolve_active_model_for_diagnostics(
    available_models: List[str],
    requested_model: str,
    recommended_model: str,
    fallback_model: str,
) -> str:
    if requested_model in available_models:
        return requested_model
    if recommended_model in available_models:
        return recommended_model
    if fallback_model in available_models:
        return fallback_model
    return available_models[0] if available_models else ""


def model_comparison_dataframe(metrics: Dict[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    model_lab = _model_lab_payload(metrics)
    lab_rows = {
        str(row.get("model")): row
        for row in model_lab.get("comparison_rows", [])
        if isinstance(row, dict) and row.get("model")
    }
    model_comparison = metrics.get("model_comparison", {})
    if isinstance(model_comparison, dict) and model_comparison:
        for model_name, model_metrics in model_comparison.items():
            if not isinstance(model_metrics, dict):
                continue
            lab_row = lab_rows.get(str(model_name), {})
            rows.append(
                {
                    "model": str(model_name),
                    "model_label": _display_name_for_ui(str(model_name)),
                    "rmse": model_metrics.get("rmse"),
                    "mae": model_metrics.get("mae"),
                    "r2": model_metrics.get("r2"),
                    "validation_rmse": model_metrics.get("validation_rmse"),
                    "validation_mae": model_metrics.get("validation_mae"),
                    "validation_r2": model_metrics.get("validation_r2"),
                    "cv_rmse_mean": model_metrics.get("cv_rmse_mean"),
                    "cv_rmse_std": model_metrics.get("cv_rmse_std"),
                    "training_time_seconds": model_metrics.get("training_time_seconds", lab_row.get("training_time_seconds")),
                    "prediction_time_seconds": model_metrics.get("prediction_time_seconds", lab_row.get("prediction_time_seconds")),
                    "accuracy_score": model_metrics.get("accuracy_score", lab_row.get("accuracy_score")),
                    "speed_score": model_metrics.get("speed_score", lab_row.get("speed_score")),
                    "interpretability_score": model_metrics.get("interpretability_score", lab_row.get("interpretability_score")),
                    "interpretability_rating": model_metrics.get("interpretability_rating", lab_row.get("interpretability_rating")),
                    "recommended_for": model_metrics.get("recommended_for", lab_row.get("recommended_for")),
                    "role": model_metrics.get("model_role", "model"),
                }
            )
    elif metrics:
        rows.append(
            {
                "model": str(metrics.get("best_model_name") or metrics.get("best_model") or "model"),
                "model_label": _display_name_for_ui(str(metrics.get("best_model_name") or metrics.get("best_model") or "model")),
                "rmse": metrics.get("rmse"),
                "mae": metrics.get("mae"),
                "r2": metrics.get("r2"),
                "validation_rmse": metrics.get("validation_rmse"),
                "validation_mae": metrics.get("validation_mae"),
                "validation_r2": metrics.get("validation_r2"),
                "cv_rmse_mean": metrics.get("cv_rmse_mean"),
                "cv_rmse_std": metrics.get("cv_rmse_std"),
                "training_time_seconds": metrics.get("training_time_seconds"),
                "prediction_time_seconds": metrics.get("prediction_time_seconds"),
                "accuracy_score": metrics.get("accuracy_score"),
                "speed_score": metrics.get("speed_score"),
                "interpretability_score": metrics.get("interpretability_score"),
                "interpretability_rating": metrics.get("interpretability_rating"),
                "recommended_for": metrics.get("recommended_for"),
                "role": "model",
            }
        )

    model_df = pd.DataFrame(rows)
    for col in [
        "rmse",
        "mae",
        "r2",
        "validation_rmse",
        "validation_mae",
        "validation_r2",
        "cv_rmse_mean",
        "cv_rmse_std",
        "training_time_seconds",
        "prediction_time_seconds",
        "accuracy_score",
        "speed_score",
        "interpretability_score",
    ]:
        if col in model_df.columns:
            model_df[col] = pd.to_numeric(model_df[col], errors="coerce")
    return model_df


def best_model_name(metrics: Dict[str, Any], model_df: pd.DataFrame) -> str:
    best_name = str(metrics.get("best_model_name") or metrics.get("best_model") or "")
    if best_name and not model_df.empty and best_name in model_df["model"].astype(str).tolist():
        return best_name
    if not model_df.empty and "validation_rmse" in model_df.columns and model_df["validation_rmse"].notna().any():
        return str(model_df.sort_values("validation_rmse").iloc[0]["model"])
    if not model_df.empty:
        return str(model_df.iloc[0]["model"])
    return "N/A"


def baseline_model_name(metrics: Dict[str, Any], model_df: pd.DataFrame) -> str:
    baseline_name = str(metrics.get("baseline_model") or "dummy_mean_baseline")
    if not model_df.empty and baseline_name in model_df["model"].astype(str).tolist():
        return baseline_name
    baseline_rows = model_df[model_df.get("role", pd.Series(dtype=str)).astype(str).eq("baseline")]
    if not baseline_rows.empty:
        return str(baseline_rows.iloc[0]["model"])
    return baseline_name


def recommended_model_name(metrics: Dict[str, Any], priority: Any, model_df: pd.DataFrame) -> str:
    recommendation = recommendation_for_priority(_model_lab_payload(metrics), priority)
    model_name = str(recommendation.get("model", "")).strip()
    if model_name and not model_df.empty and model_name in model_df["model"].astype(str).tolist():
        return model_name
    return best_model_name(metrics, model_df)


def _model_row(model_df: pd.DataFrame, model_name: str) -> Dict[str, Any]:
    if model_df.empty or "model" not in model_df.columns:
        return {}
    row = model_df[model_df["model"].astype(str) == str(model_name)]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


def _model_lab_dataframe(metrics: Dict[str, Any], priority: Any) -> pd.DataFrame:
    priority_key = normalize_priority(priority)
    model_lab = _model_lab_payload(metrics)
    rows = []
    for row in model_lab.get("comparison_rows", []):
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "model": row.get("model"),
                "Model": row.get("display_name"),
                "MAE": row.get("mae"),
                "RMSE": row.get("rmse"),
                "R²": row.get("r2"),
                "Training Time": row.get("training_time_seconds"),
                "Prediction Time": row.get("prediction_time_seconds"),
                "Accuracy": row.get("accuracy_score"),
                "Speed": row.get("speed_score"),
                "Interpretability": row.get("interpretability_rating"),
                "Interpretability Raw": row.get("interpretability_score"),
                "Overall Score": (row.get("overall_scores") or {}).get(priority_key),
                "Recommended for": row.get("recommended_for"),
            }
        )
    comparison_df = pd.DataFrame(rows)
    if comparison_df.empty:
        return comparison_df
    comparison_df["Overall Score"] = pd.to_numeric(comparison_df["Overall Score"], errors="coerce")
    comparison_df = comparison_df.sort_values(["Overall Score", "Accuracy", "Speed"], ascending=[False, False, False])
    return comparison_df.reset_index(drop=True)


def _single_model_metrics_table(metrics: Dict[str, Any], model_name: str, priority: Any) -> pd.DataFrame:
    comparison_df = _model_lab_dataframe(metrics, priority)
    if comparison_df.empty:
        return comparison_df
    row = comparison_df[comparison_df["model"].astype(str) == str(model_name)]
    if row.empty:
        return pd.DataFrame()
    return row.drop(columns=["model"]).reset_index(drop=True)


def _render_model_explanation_box(model_name: str, unavailable_reason: str = "") -> None:
    metadata = get_model_metadata(model_name)
    st.markdown(f"### {metadata['display_name']}")
    if unavailable_reason:
        st.warning(
            f"{metadata['display_name']} is unavailable in this run: "
            f"{unavailable_reason.replace('_', ' ')}."
        )
    st.markdown(
        "\n".join(
            [
                f"**Simple view:** {metadata['short_summary']}",
                f"- What it does: {metadata['what_it_does']}",
                f"- When to choose it: {metadata['when_to_choose']}",
                f"- Advantages: {metadata['advantages']}",
                f"- Limitations: {metadata['limitations']}",
                f"- Business interpretation: {metadata['business_interpretation']}",
            ]
        )
    )


def _render_scoring_explanation(model_lab: Dict[str, Any]) -> None:
    scoring_method = model_lab.get("scoring_method", {}) if isinstance(model_lab, dict) else {}
    priority_weights = model_lab.get("priority_weights", {}) if isinstance(model_lab, dict) else {}
    with st.expander("How the recommendation score works", expanded=False):
        st.markdown(
            "\n".join(
                [
                    f"- Accuracy score: {scoring_method.get('accuracy_score', 'Normalized grouped-validation performance.')}",
                    f"- Speed score: {scoring_method.get('speed_score', 'Normalized training and prediction runtime.')}",
                    f"- Interpretability score: {scoring_method.get('interpretability_score', 'Curated transparency rating.')}",
                    f"- Overall score: {scoring_method.get('overall_score', 'Priority-weighted decision-support score.')}",
                ]
            )
        )
        if isinstance(priority_weights, dict) and priority_weights:
            weight_rows = []
            for priority, weights in priority_weights.items():
                if not isinstance(weights, dict):
                    continue
                weight_rows.append(
                    {
                        "Priority": display_priority_name(priority),
                        "Accuracy weight": weights.get("accuracy_score"),
                        "Speed weight": weights.get("speed_score"),
                        "Interpretability weight": weights.get("interpretability_score_normalized"),
                    }
                )
            if weight_rows:
                st.dataframe(pd.DataFrame(weight_rows), use_container_width=True, hide_index=True)
        st.info(
            str(
                model_lab.get("scoring_note")
                or "Weights are decision-support choices and can be adjusted when business priorities change."
            )
        )
        st.warning(
            str(
                model_lab.get("speed_warning")
                or "Speed depends on the runtime environment and should be interpreted as a practical indicator."
            )
        )


def resolve_model_path_for_metrics(
    metrics: Dict[str, Any],
    manifest: Dict[str, Any],
    manifest_path: Optional[Path],
    preferred_model: Optional[str] = None,
) -> Optional[Path]:
    raw_path = None
    if preferred_model:
        model_paths = metrics.get("model_paths", {})
        if isinstance(model_paths, dict):
            raw_path = model_paths.get(preferred_model)
    if not raw_path:
        raw_path = (
            metrics.get("best_model_path")
            or metrics.get("model_path")
            or manifest.get("latest_model_path")
        )
    if not raw_path:
        return None
    return resolve_manifest_relative_path(manifest_path, str(raw_path))


@st.cache_resource(show_spinner=False)
def load_best_model(model_path_text: str) -> Dict[str, Any]:
    """Load the saved joblib payload. The dashboard still works if loading fails."""
    return load_model_payload(model_path_text)


def _feature_names_from_payload(model_payload: Dict[str, Any], metrics: Dict[str, Any]) -> List[str]:
    payload = model_payload.get("payload")
    if isinstance(payload, dict):
        feature_names = payload.get("feature_names") or payload.get("numeric_feature_names")
        if isinstance(feature_names, list) and feature_names:
            return [str(name) for name in feature_names]
    feature_names = metrics.get("feature_names", [])
    return [str(name) for name in feature_names] if isinstance(feature_names, list) else []


def _prepare_model_features(dataset: pd.DataFrame, feature_names: List[str]) -> pd.DataFrame:
    """Build the exact feature frame expected by the saved sklearn pipeline."""
    if dataset.empty or not feature_names:
        return pd.DataFrame()
    feature_frame = pd.DataFrame(index=dataset.index)
    for feature in feature_names:
        if feature in dataset.columns:
            feature_frame[feature] = dataset[feature]
        elif feature == "gc_deviation" and "gc_content" in dataset.columns:
            gc_percent = pd.to_numeric(dataset["gc_content"], errors="coerce").apply(_to_percent)
            feature_frame[feature] = (gc_percent - 52.5).abs()
        elif feature == "codon_efficiency" and {"cai", "rare_codon_ratio"}.issubset(dataset.columns):
            cai = pd.to_numeric(dataset["cai"], errors="coerce")
            rare_ratio = pd.to_numeric(dataset["rare_codon_ratio"], errors="coerce").apply(
                lambda value: max(0.0, min(1.0, value / 100.0 if value > 1.5 else value))
            )
            feature_frame[feature] = cai * (1.0 - rare_ratio)
        elif feature == "stability_index" and {"gc_content", "rare_codon_ratio"}.issubset(dataset.columns):
            gc_percent = pd.to_numeric(dataset["gc_content"], errors="coerce").apply(_to_percent)
            rare_ratio = pd.to_numeric(dataset["rare_codon_ratio"], errors="coerce").apply(
                lambda value: max(0.0, min(1.0, value / 100.0 if value > 1.5 else value))
            )
            feature_frame[feature] = gc_percent * (1.0 - rare_ratio)
        else:
            feature_frame[feature] = np.nan
    return feature_frame


def _extract_vector_from_metrics(metrics: Dict[str, Any], keys: List[str]) -> Optional[pd.Series]:
    for key in keys:
        values = metrics.get(key)
        if isinstance(values, list) and values:
            series = pd.to_numeric(pd.Series(values), errors="coerce").dropna().reset_index(drop=True)
            if len(series) >= 3:
                return series
    return None


def importance_dataframe_from_metrics(metrics: Dict[str, Any], model_name: Optional[str] = None) -> pd.DataFrame:
    if model_name:
        model_metrics = _model_metrics_from_metrics(metrics, model_name)
        model_table = model_metrics.get("feature_importance_table", [])
        if isinstance(model_table, list) and model_table:
            df = pd.DataFrame(model_table)
            if "feature" in df.columns and "importance" in df.columns:
                df["importance"] = pd.to_numeric(df["importance"], errors="coerce")
                return df.dropna(subset=["importance"]).sort_values("importance", ascending=False)
        model_names = model_metrics.get("feature_names", [])
        model_values = model_metrics.get("feature_importances", [])
        if isinstance(model_names, list) and isinstance(model_values, list) and len(model_names) == len(model_values):
            df = pd.DataFrame({"feature": model_names, "importance": model_values})
            df["importance"] = pd.to_numeric(df["importance"], errors="coerce")
            return df.dropna(subset=["importance"]).sort_values("importance", ascending=False)

    table = metrics.get("feature_importance_table", [])
    if isinstance(table, list) and table:
        df = pd.DataFrame(table)
        if "feature" in df.columns and "importance" in df.columns:
            df["importance"] = pd.to_numeric(df["importance"], errors="coerce")
            return df.dropna(subset=["importance"]).sort_values("importance", ascending=False)

    names = metrics.get("feature_names", [])
    values = metrics.get("feature_importances", [])
    if isinstance(names, list) and isinstance(values, list) and len(names) == len(values):
        df = pd.DataFrame({"feature": names, "importance": values})
        df["importance"] = pd.to_numeric(df["importance"], errors="coerce")
        return df.dropna(subset=["importance"]).sort_values("importance", ascending=False)
    return pd.DataFrame()


def extract_importance_from_model(model_payload: Dict[str, Any], metrics: Dict[str, Any]) -> pd.DataFrame:
    """Fallback when metrics JSON does not contain permutation importance."""
    model = model_payload.get("model")
    payload = model_payload.get("payload")
    if model is None:
        return pd.DataFrame()

    final_model = model
    encoded_names: List[str] = []
    if hasattr(model, "named_steps"):
        final_model = model.named_steps.get("model", model)
        preprocessor = model.named_steps.get("preprocessor")
        if preprocessor is not None and hasattr(preprocessor, "get_feature_names_out"):
            try:
                encoded_names = [str(name) for name in preprocessor.get_feature_names_out()]
            except (AttributeError, TypeError, ValueError):
                encoded_names = []

    if not encoded_names and isinstance(payload, dict):
        encoded_names = [str(name) for name in payload.get("encoded_feature_names", [])]
    if not encoded_names:
        encoded_names = [str(name) for name in metrics.get("feature_names", [])]

    raw_values = None
    source = "model_artifact"
    if hasattr(final_model, "feature_importances_"):
        raw_values = np.asarray(final_model.feature_importances_, dtype=float)
        source = "model_feature_importances"
    elif hasattr(final_model, "coef_"):
        raw_values = np.abs(np.asarray(final_model.coef_, dtype=float).ravel())
        source = "model_coefficients"

    if raw_values is None or not encoded_names:
        return pd.DataFrame()
    limit = min(len(encoded_names), raw_values.size)
    df = pd.DataFrame(
        {
            "feature": encoded_names[:limit],
            "importance": raw_values[:limit],
            "source": source,
        }
    )
    total = float(df["importance"].sum())
    if total > 0:
        df["importance"] = df["importance"] / total
    return df.sort_values("importance", ascending=False)


def plot_model_vs_baseline(model_df: pd.DataFrame, metric: str, active_model: str, baseline_model: str) -> go.Figure:
    label_map = {
        "validation_rmse": "Validation RMSE",
        "rmse": "Test RMSE",
        "mae": "MAE",
        "r2": "R²",
        "validation_r2": "Validation R²",
    }
    plot_df = model_df.dropna(subset=[metric]).copy()
    ascending = metric not in {"r2", "validation_r2"}
    plot_df = plot_df.sort_values(metric, ascending=ascending)
    plot_df["model_label"] = plot_df["model"].astype(str).apply(_display_name_for_ui)
    plot_df["kind"] = "Other model"
    plot_df.loc[plot_df["model"].astype(str) == baseline_model, "kind"] = "Dummy baseline"
    plot_df.loc[plot_df["model"].astype(str) == active_model, "kind"] = "Active model"

    colors = {
        "Active model": "#16a34a",
        "Dummy baseline": "#ef4444",
        "Other model": "#64748b",
    }
    fig = px.bar(
        plot_df,
        x=metric,
        y="model_label",
        color="kind",
        orientation="h",
        color_discrete_map=colors,
        title=f"Model comparison by {label_map.get(metric, metric)}",
        labels={metric: label_map.get(metric, metric), "model_label": "Model", "kind": ""},
    )
    fig.update_layout(height=360, yaxis_title="", legend_orientation="h", legend_y=-0.25)
    return fig


def plot_feature_importance(importance_df: pd.DataFrame) -> go.Figure:
    top_df = importance_df.head(10).sort_values("importance", ascending=True)
    fig = px.bar(
        top_df,
        x="importance",
        y="feature",
        orientation="h",
        color="importance",
        color_continuous_scale=["#dbeafe", "#22c55e"],
        title="Top 10 global feature importances",
        labels={"importance": "Importance", "feature": "Feature"},
    )
    fig.update_layout(height=430, coloraxis_showscale=False, yaxis_title="")
    return fig


def _automatic_feature_interpretation(features: List[str]) -> List[str]:
    messages: List[str] = []
    lowered = [feature.lower() for feature in features]
    if any("cai" in feature or "codon" in feature for feature in lowered):
        messages.append("Codon-related variables appear important, so codon adaptation contributes to the proxy score.")
    if any("gc" in feature for feature in lowered):
        messages.append("GC-related variables also matter, which means nucleotide composition helps the model.")
    if any("host" in feature for feature in lowered):
        messages.append("The plant host has influence, so the same protein can behave differently under host assumptions.")
    if any("length" in feature for feature in lowered):
        messages.append("Protein length or length penalty contributes to the prediction, but this remains a proxy signal.")
    if not messages:
        messages.append("The top variables influence the model globally, but they should not be read as experimental causes.")
    return messages


def _encoded_model_matrix(model: Any, x_frame: pd.DataFrame) -> Tuple[Optional[Any], np.ndarray, List[str]]:
    if model is None or x_frame.empty:
        return None, np.empty((0, 0)), []
    if hasattr(model, "named_steps") and "preprocessor" in model.named_steps:
        preprocessor = model.named_steps.get("preprocessor")
        estimator = model.named_steps.get("model")
        transformed = preprocessor.transform(x_frame)
        if hasattr(transformed, "toarray"):
            transformed = transformed.toarray()
        try:
            encoded_names = [str(name) for name in preprocessor.get_feature_names_out()]
        except (AttributeError, TypeError, ValueError):
            encoded_names = [str(name) for name in x_frame.columns]
        return estimator, np.asarray(transformed, dtype=float), encoded_names

    numeric_frame = x_frame.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return model, numeric_frame.to_numpy(dtype=float), [str(name) for name in numeric_frame.columns]


def compute_shap_values(
    model_payload: Dict[str, Any],
    dataset: pd.DataFrame,
    metrics: Dict[str, Any],
    max_rows: int = 24,
) -> Dict[str, Any]:
    """Compute SHAP when available, otherwise produce a transparent contribution fallback."""
    model = model_payload.get("model")
    feature_names = _feature_names_from_payload(model_payload, metrics)
    x_frame = _prepare_model_features(dataset, feature_names)
    if model is None or x_frame.empty:
        return {"available": False, "reason": "Model or feature matrix unavailable."}

    x_explain = x_frame.sample(n=min(max_rows, len(x_frame)), random_state=42)
    x_background = x_frame.sample(n=min(48, len(x_frame)), random_state=7)
    estimator, encoded_explain, encoded_names = _encoded_model_matrix(model, x_explain)
    _, encoded_background, _ = _encoded_model_matrix(model, x_background)
    if estimator is None or encoded_explain.size == 0:
        return {"available": False, "reason": "Could not encode model features for explanation."}

    shap_values = None
    base_values = None
    method = "SHAP"
    warning = ""
    try:
        import shap  # type: ignore[import-not-found]

        if hasattr(estimator, "coef_"):
            explainer = shap.LinearExplainer(estimator, encoded_background)
        elif hasattr(estimator, "feature_importances_"):
            explainer = shap.TreeExplainer(estimator, data=encoded_background)
        else:
            explainer = shap.Explainer(estimator.predict, encoded_background)
        explanation = explainer(encoded_explain)
        shap_values = np.asarray(explanation.values, dtype=float)
        if shap_values.ndim == 3:
            shap_values = shap_values[:, :, 0]
        base_values = np.asarray(getattr(explanation, "base_values", []), dtype=float)
        if base_values.ndim > 1:
            base_values = base_values[:, 0]
    except (ImportError, AttributeError, NotImplementedError, RuntimeError, TypeError, ValueError) as exc:
        warning = str(exc)

    if shap_values is None and hasattr(estimator, "coef_"):
        # Linear fallback: centered coefficient contributions, close to SHAP for linear models.
        coef = np.asarray(estimator.coef_, dtype=float).ravel()
        center = np.asarray(encoded_background, dtype=float).mean(axis=0)
        limit = min(len(coef), encoded_explain.shape[1])
        shap_values = (encoded_explain[:, :limit] - center[:limit]) * coef[:limit]
        encoded_names = encoded_names[:limit]
        method = "Linear contribution fallback"

    if shap_values is None:
        return {
            "available": False,
            "reason": "SHAP is unavailable for this model. Install shap or use a linear/tree model artifact.",
            "warning": warning,
        }

    predictions = np.asarray(model.predict(x_explain), dtype=float)
    contribution_sums = np.asarray(shap_values, dtype=float).sum(axis=1)
    if base_values is None or len(base_values) != len(predictions):
        base_values = predictions - contribution_sums
    target_column = str(metrics.get("target_column") or "target_expression_score")
    actual_values = (
        pd.to_numeric(dataset.loc[x_explain.index, target_column], errors="coerce")
        if target_column in dataset.columns
        else pd.Series([np.nan] * len(x_explain), index=x_explain.index)
    )

    labels = []
    for idx in x_explain.index:
        row = dataset.loc[idx]
        accession = _safe_text(row.get("protein_accession", row.get("accession", idx)), default=str(idx))
        host = _safe_text(row.get("plant_host"), default="host")
        labels.append(f"Row {idx} | {accession} | {host}")

    global_df = pd.DataFrame(
        {
            "feature": encoded_names[: shap_values.shape[1]],
            "mean_abs_contribution": np.abs(shap_values).mean(axis=0),
        }
    ).sort_values("mean_abs_contribution", ascending=False)

    return {
        "available": True,
        "method": method,
        "warning": warning,
        "feature_names": encoded_names[: shap_values.shape[1]],
        "values": shap_values,
        "global_df": global_df,
        "sample_indices": list(x_explain.index),
        "sample_labels": labels,
        "sample_rule": f"Reproducible sample of {len(x_explain)} dataset rows, selected with random_state=42.",
        "predictions": predictions,
        "base_values": base_values,
        "contribution_sums": contribution_sums,
        "actual_values": actual_values.to_numpy(dtype=float),
    }


def plot_shap_global_summary(shap_payload: Dict[str, Any]) -> go.Figure:
    global_df = shap_payload.get("global_df", pd.DataFrame())
    top_df = global_df.head(10).sort_values("mean_abs_contribution", ascending=True)
    fig = px.bar(
        top_df,
        x="mean_abs_contribution",
        y="feature",
        orientation="h",
        color="mean_abs_contribution",
        color_continuous_scale=["#e0f2fe", "#2563eb"],
        title="SHAP global summary: average impact of each feature",
        labels={"mean_abs_contribution": "Average |SHAP value| (global impact)", "feature": "Feature"},
    )
    fig.update_layout(
        height=480,
        coloraxis_showscale=False,
        yaxis_title="",
        margin=dict(l=190, r=30, t=70, b=55),
    )
    return fig


def plot_shap_local_explanation(
    shap_payload: Dict[str, Any],
    sample_position: int,
    selected_label: str = "",
) -> go.Figure:
    values = np.asarray(shap_payload.get("values"), dtype=float)
    feature_names = shap_payload.get("feature_names", [])
    if values.size == 0 or not feature_names:
        return go.Figure()
    sample_position = max(0, min(sample_position, values.shape[0] - 1))
    local_df = pd.DataFrame(
        {
            "feature": feature_names[: values.shape[1]],
            "contribution": values[sample_position, :],
        }
    )
    local_df["abs_contribution"] = local_df["contribution"].abs()
    local_df = local_df.sort_values("abs_contribution", ascending=False).head(12)
    local_df = local_df.sort_values("contribution")
    local_df["direction"] = np.where(local_df["contribution"] >= 0, "Pushes prediction up", "Pushes prediction down")

    fig = px.bar(
        local_df,
        x="contribution",
        y="feature",
        color="direction",
        orientation="h",
        color_discrete_map={
            "Pushes prediction up": "#16a34a",
            "Pushes prediction down": "#ef4444",
        },
        title=(
            "SHAP local explanation: what pushes this prediction up or down"
            + (f"<br><sup>{selected_label}</sup>" if selected_label else "")
        ),
        labels={"contribution": "Contribution to prediction", "feature": "Feature", "direction": ""},
    )
    fig.add_vline(x=0, line_dash="dash", line_color="#475569")
    fig.update_traces(hovertemplate="<b>%{y}</b><br>Contribution: %{x:.5f}<extra></extra>")
    fig.update_layout(
        height=480,
        yaxis_title="",
        legend_orientation="h",
        legend_y=-0.22,
        margin=dict(l=190, r=35, t=70, b=85),
    )
    return fig


def _summarize_local_contributions(shap_payload: Dict[str, Any], sample_position: int) -> str:
    """Return a short student-friendly explanation for one local SHAP chart."""
    values = np.asarray(shap_payload.get("values"), dtype=float)
    feature_names = shap_payload.get("feature_names", [])
    if values.size == 0 or not feature_names:
        return "No local contribution details are available for this example."

    sample_position = max(0, min(sample_position, values.shape[0] - 1))
    local_df = pd.DataFrame(
        {
            "feature": feature_names[: values.shape[1]],
            "contribution": values[sample_position, :],
        }
    )
    positive = local_df[local_df["contribution"] > 0].sort_values("contribution", ascending=False).head(3)
    negative = local_df[local_df["contribution"] < 0].sort_values("contribution", ascending=True).head(3)

    up_text = ", ".join(positive["feature"].astype(str).tolist()) if not positive.empty else "no strong positive feature"
    down_text = ", ".join(negative["feature"].astype(str).tolist()) if not negative.empty else "no strong negative feature"
    return (
        f"For this example, {up_text} push the prediction upward, while {down_text} push it downward. "
        "This explains this one row only; it is not a general biological rule."
    )


def _local_shap_equation_text(shap_payload: Dict[str, Any], sample_position: int) -> str:
    predictions = np.asarray(shap_payload.get("predictions", []), dtype=float)
    base_values = np.asarray(shap_payload.get("base_values", []), dtype=float)
    contribution_sums = np.asarray(shap_payload.get("contribution_sums", []), dtype=float)
    if sample_position >= len(predictions) or sample_position >= len(base_values) or sample_position >= len(contribution_sums):
        return "SHAP decomposes the model prediction into a reference value plus feature contributions."

    return (
        "SHAP calculation for this row: "
        f"reference prediction {_fmt_dashboard_metric(base_values[sample_position])} "
        f"+ feature contributions {_fmt_dashboard_metric(contribution_sums[sample_position])} "
        f"= model prediction {_fmt_dashboard_metric(predictions[sample_position])}."
    )


def plot_predictions_vs_real(metrics: Dict[str, Any]) -> Optional[go.Figure]:
    y_true = _extract_vector_from_metrics(metrics, ["test_actual_values", "actual_values", "validation_actual_values"])
    y_pred = _extract_vector_from_metrics(metrics, ["test_predicted_values", "predicted_values", "validation_predicted_values"])
    if y_true is None or y_pred is None:
        return None
    n = min(len(y_true), len(y_pred))
    diag_df = pd.DataFrame({"Proxy target": y_true.iloc[:n], "Prediction": y_pred.iloc[:n]})
    fig = px.scatter(
        diag_df,
        x="Proxy target",
        y="Prediction",
        title="Prediction quality: model vs proxy target",
        color_discrete_sequence=["#2563eb"],
    )
    min_val = float(min(diag_df["Proxy target"].min(), diag_df["Prediction"].min()))
    max_val = float(max(diag_df["Proxy target"].max(), diag_df["Prediction"].max()))
    fig.add_shape(
        type="line",
        x0=min_val,
        y0=min_val,
        x1=max_val,
        y1=max_val,
        line=dict(color="#64748b", dash="dash"),
    )
    fig.update_layout(height=420)
    return fig


def plot_residuals(metrics: Dict[str, Any]) -> Optional[go.Figure]:
    residuals = _extract_vector_from_metrics(metrics, ["test_residual_values", "residual_values", "validation_residual_values"])
    if residuals is None:
        y_true = _extract_vector_from_metrics(metrics, ["test_actual_values", "actual_values"])
        y_pred = _extract_vector_from_metrics(metrics, ["test_predicted_values", "predicted_values"])
        if y_true is None or y_pred is None:
            return None
        n = min(len(y_true), len(y_pred))
        residuals = y_true.iloc[:n].reset_index(drop=True) - y_pred.iloc[:n].reset_index(drop=True)
    fig = px.histogram(
        pd.DataFrame({"Residual": residuals}),
        x="Residual",
        nbins=24,
        title="Residual distribution: actual proxy - prediction",
        color_discrete_sequence=["#0f766e"],
    )
    fig.add_vline(x=0, line_dash="dash", line_color="#475569")
    fig.update_layout(height=420)
    return fig


def _plot_pipeline_schema(training_features: List[str], target_column: str) -> go.Figure:
    fig = go.Figure()

    boxes = [
        {
            "key": "training",
            "x0": 0.04,
            "x1": 0.30,
            "y0": 0.62,
            "y1": 0.86,
            "fill": "#dbeafe",
            "line": "#2563eb",
            "title": f"Training features ({len(training_features)})",
            "body": "Used directly by the ML model",
        },
        {
            "key": "model",
            "x0": 0.39,
            "x1": 0.61,
            "y0": 0.62,
            "y1": 0.86,
            "fill": "#dcfce7",
            "line": "#16a34a",
            "title": "ML model",
            "body": "Learns patterns from features",
        },
        {
            "key": "target",
            "x0": 0.70,
            "x1": 0.96,
            "y0": 0.62,
            "y1": 0.86,
            "fill": "#fef3c7",
            "line": "#d97706",
            "title": "Predicted proxy target",
            "body": target_column,
        },
        {
            "key": "descriptive",
            "x0": 0.04,
            "x1": 0.30,
            "y0": 0.18,
            "y1": 0.40,
            "fill": "#f1f5f9",
            "line": "#64748b",
            "title": "Descriptive features",
            "body": "Kept for context, not training",
        },
        {
            "key": "context",
            "x0": 0.70,
            "x1": 0.96,
            "y0": 0.18,
            "y1": 0.40,
            "fill": "#ede9fe",
            "line": "#7c3aed",
            "title": "Biological context",
            "body": "Helps interpret the result",
        },
    ]

    centers = {}
    for box in boxes:
        centers[box["key"]] = ((box["x0"] + box["x1"]) / 2, (box["y0"] + box["y1"]) / 2)
        fig.add_shape(
            type="rect",
            xref="x",
            yref="y",
            x0=box["x0"],
            x1=box["x1"],
            y0=box["y0"],
            y1=box["y1"],
            fillcolor=box["fill"],
            line=dict(color=box["line"], width=2),
            layer="below",
        )
        fig.add_annotation(
            x=centers[box["key"]][0],
            y=centers[box["key"]][1] + 0.045,
            xref="x",
            yref="y",
            text=f"<b>{box['title']}</b>",
            showarrow=False,
            font=dict(size=15, color="#0f172a"),
        )
        fig.add_annotation(
            x=centers[box["key"]][0],
            y=centers[box["key"]][1] - 0.045,
            xref="x",
            yref="y",
            text=str(box["body"]),
            showarrow=False,
            font=dict(size=12, color="#334155"),
        )

    arrow_style = dict(arrowhead=3, arrowsize=1.2, arrowwidth=2.5)
    fig.add_annotation(
        x=0.385,
        y=centers["training"][1],
        ax=0.305,
        ay=centers["training"][1],
        xref="x",
        yref="y",
        axref="x",
        ayref="y",
        showarrow=True,
        arrowcolor="#2563eb",
        **arrow_style,
    )
    fig.add_annotation(
        x=0.695,
        y=centers["model"][1],
        ax=0.615,
        ay=centers["model"][1],
        xref="x",
        yref="y",
        axref="x",
        ayref="y",
        showarrow=True,
        arrowcolor="#16a34a",
        **arrow_style,
    )
    fig.add_annotation(
        x=0.695,
        y=centers["descriptive"][1],
        ax=0.305,
        ay=centers["descriptive"][1],
        xref="x",
        yref="y",
        axref="x",
        ayref="y",
        showarrow=True,
        arrowcolor="#64748b",
        **arrow_style,
    )
    fig.add_annotation(
        x=0.50,
        y=0.93,
        xref="x",
        yref="y",
        text="<b>Pipeline logic: what trains the model, and what only gives context</b>",
        showarrow=False,
        font=dict(size=18, color="#0f172a"),
    )
    fig.add_annotation(
        x=0.50,
        y=0.50,
        xref="x",
        yref="y",
        text="Blue path = training and prediction. Gray path = interpretation only.",
        showarrow=False,
        font=dict(size=13, color="#475569"),
    )
    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False, range=[0, 1])
    fig.update_layout(
        height=430,
        margin=dict(l=20, r=20, t=25, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
    )
    return fig


def display_feature_types(metrics: Dict[str, Any]) -> None:
    feature_roles = metrics.get("feature_roles") or (metrics.get("feature_selection") or {}).get("feature_roles") or {}
    training_features = feature_roles.get("used_by_model") or metrics.get("feature_names") or []
    descriptive_features = feature_roles.get("descriptive_only") or []
    target_features = feature_roles.get("target_derived_excluded") or [metrics.get("target_column", "target_expression_score")]
    target_column = str(metrics.get("target_column") or "target_expression_score")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### Training Features")
        st.info("These variables are used directly by the model to learn.")
        st.caption(", ".join(str(v) for v in training_features[:14]) if training_features else "N/A")
        if len(training_features) > 14:
            with st.expander("Show all training features", expanded=False):
                st.write(", ".join(str(v) for v in training_features))
    with col2:
        st.markdown("#### Descriptive Features")
        st.info("These variables describe the sequence or context but are not used as model inputs.")
        st.caption(", ".join(str(v) for v in descriptive_features[:14]) if descriptive_features else "N/A")
        if len(descriptive_features) > 14:
            with st.expander("Show all descriptive features", expanded=False):
                st.write(", ".join(str(v) for v in descriptive_features))
    with col3:
        st.markdown("#### Proxy Target")
        st.warning("This is not a real experimental measurement. It is a simulated target used for learning.")
        st.caption(", ".join(str(v) for v in target_features) if target_features else target_column)

    st.markdown("#### Visual map of the pipeline")
    st.caption(
        "The upper path shows what the model actually uses to learn and predict. "
        "The lower path shows variables kept for explanation and biological context."
    )
    st.plotly_chart(_plot_pipeline_schema([str(v) for v in training_features], target_column), use_container_width=True)


def generate_metrics_conclusion(
    metrics: Dict[str, Any],
    model_df: pd.DataFrame,
    importance_df: pd.DataFrame,
    active_model: str,
    recommended_model: str,
    priority: Any,
    baseline_model: str,
) -> List[str]:
    active_row = _model_row(model_df, active_model)
    baseline_row = _model_row(model_df, baseline_model)
    active_rmse = active_row.get("validation_rmse", active_row.get("rmse"))
    baseline_rmse = baseline_row.get("validation_rmse", baseline_row.get("rmse"))
    top_features = importance_df["feature"].head(3).astype(str).tolist() if not importance_df.empty else []

    conclusions: List[str] = []
    if active_rmse is not None and baseline_rmse is not None and pd.notna(active_rmse) and pd.notna(baseline_rmse):
        if float(active_rmse) < float(baseline_rmse):
            conclusions.append(
                f"{_display_name_for_ui(active_model)} beats the dummy baseline, so the model learns more than a simple average prediction."
            )
        else:
            conclusions.append(
                "The selected model does not clearly beat the dummy baseline, so its usefulness should be treated carefully."
            )
    conclusions.append(
        f"For the current priority ({display_priority_name(priority)}), the recommended model is {_display_name_for_ui(recommended_model)}."
    )
    if top_features:
        conclusions.append(f"The strongest global signals are {', '.join(top_features)}.")
    conclusions.append("Feature importance and local contributions make the model explainable enough for a proxy-based dashboard.")
    conclusions.append("The target remains a simulated proxy, not direct experimental expression data.")
    return conclusions


def _render_metric_cards(
    metrics: Dict[str, Any],
    model_df: pd.DataFrame,
    active_model: str,
    recommended_model: str,
    baseline_model: str,
    priority: Any,
) -> None:
    active_row = _model_row(model_df, active_model)
    baseline_row = _model_row(model_df, baseline_model)
    baseline_rmse = baseline_row.get("validation_rmse", baseline_row.get("rmse"))
    active_rmse = active_row.get("validation_rmse", active_row.get("rmse"))
    gain = active_row.get("accuracy_score")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Active model", _display_name_for_ui(active_model))
    c2.metric("Recommended", _display_name_for_ui(recommended_model))
    c3.metric("RMSE", _fmt_dashboard_metric(active_row.get("rmse")))
    c4.metric("MAE", _fmt_dashboard_metric(active_row.get("mae")))
    c5.metric("R²", _fmt_dashboard_metric(active_row.get("r2")))
    c6.metric("Accuracy score", _fmt_dashboard_pct(gain))

    st.caption(
        f"Priority focus: {display_priority_name(priority)} | "
        f"Training time: {_fmt_duration_seconds(active_row.get('training_time_seconds'))} | "
        f"Prediction time: {_fmt_duration_seconds(active_row.get('prediction_time_seconds'))} | "
        f"Baseline validation RMSE: {_fmt_dashboard_metric(baseline_rmse)}"
    )

    if active_rmse is not None and baseline_rmse is not None and pd.notna(active_rmse) and pd.notna(baseline_rmse):
        if float(active_rmse) < float(baseline_rmse):
            st.success(
                f"{_display_name_for_ui(active_model)} adds value: it reduces the error compared with the dummy baseline."
            )
        else:
            st.warning("The selected model does not improve over the dummy baseline on the main error metric.")
    if active_model != recommended_model:
        st.info(
            f"You are inspecting {_display_name_for_ui(active_model)} manually. "
            f"For {display_priority_name(priority)}, {_display_name_for_ui(recommended_model)} is the current recommendation."
        )


def _render_active_run_context(metrics: Dict[str, Any]) -> None:
    metadata = st.session_state.get("metadata", {}) or {}
    manifest = st.session_state.get("manifest", {}) or {}
    requested_params = st.session_state.get("active_pipeline_params", {}) or {}
    load_mode = st.session_state.get("artifact_load_mode") or "not loaded"

    st.markdown("### Active backend run")
    st.caption(
        "Metrics below are shown only for the artifact set loaded in this Streamlit session. "
        "Run the backend pipeline or explicitly load a manifest to update this context."
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Load mode", str(load_mode).replace("_", " "))
    c2.metric("Keyword", str(metadata.get("keyword", requested_params.get("keyword", "N/A"))))
    c3.metric("Protein limit", str(metadata.get("protein_limit", requested_params.get("protein_limit", "N/A"))))
    c4.metric("Random seed", str(metadata.get("random_seed", requested_params.get("random_seed", "N/A"))))
    c5.metric("Rows", str(metadata.get("rows_generated", manifest.get("rows_generated", "N/A"))))

    st.caption(f"Manifest: {st.session_state.get('manifest_path') or 'N/A'}")
    st.caption(f"Metrics target: {metrics.get('target_column', metadata.get('model_target_column', 'N/A'))}")

    if requested_params and metadata:
        mismatches = []
        for key in ("keyword", "protein_limit", "random_seed"):
            requested = requested_params.get(key)
            actual = metadata.get(key)
            if requested not in (None, "N/A") and actual not in (None, "N/A") and str(requested) != str(actual):
                mismatches.append(f"{key}: requested={requested}, loaded={actual}")
        if mismatches:
            st.warning(
                "The loaded artifacts do not match the last requested backend parameters: "
                + "; ".join(mismatches)
            )


def render_metrics_tab() -> None:
    st.subheader("📊 Metrics & Model Understanding")
    st.caption("A visual story for checking whether the proxy-expression model learns, generalizes, and stays explainable.")

    metrics = load_metrics()
    dataset = load_metrics_dataset()
    manifest = st.session_state.get("manifest", {}) or {}
    manifest_path = st.session_state.get("manifest_path")

    if not metrics:
        st.info(
            "No metrics are loaded for this session yet. Go to Pipeline Execution and run the backend pipeline, "
            "or click Load Manifest for the output directory you want to inspect."
        )
        return
    if metrics.get("training_enabled") is False:
        st.info("Training was disabled for this run, so no model dashboard is available.")
        return
    if metrics.get("skipped"):
        st.warning(f"Training was skipped: {metrics.get('reason', 'No reason provided.')}")
        return
    if metrics.get("error"):
        st.error(f"Training failed: {metrics.get('error')}")
        return

    model_df = model_comparison_dataframe(metrics)
    if model_df.empty:
        st.warning("No model comparison data was found in the metrics JSON.")
        return

    model_lab = _model_lab_payload(metrics)
    baseline_model = baseline_model_name(metrics, model_df)
    fallback_best_model = best_model_name(metrics, model_df)
    supported_models = list_supported_models()
    unavailable_models = _unavailable_models_for_ui(model_lab)
    available_models = [
        str(row.get("model"))
        for row in model_lab.get("supported_models", [])
        if isinstance(row, dict) and row.get("available")
    ]
    default_priority = normalize_priority(model_lab.get("default_priority", DEFAULT_PRIORITY))
    if "metrics_lab_priority" not in st.session_state:
        st.session_state["metrics_lab_priority"] = default_priority
    if st.session_state["metrics_lab_priority"] not in {"accuracy", "speed", "interpretability", "balanced"}:
        st.session_state["metrics_lab_priority"] = default_priority

    initial_recommended_model = recommended_model_name(metrics, st.session_state["metrics_lab_priority"], model_df)
    if "metrics_lab_model_choice" not in st.session_state or st.session_state["metrics_lab_model_choice"] not in supported_models:
        st.session_state["metrics_lab_model_choice"] = initial_recommended_model if initial_recommended_model in supported_models else supported_models[0]
    if "metrics_lab_active_model" not in st.session_state or st.session_state["metrics_lab_active_model"] not in available_models:
        st.session_state["metrics_lab_active_model"] = initial_recommended_model if initial_recommended_model in available_models else fallback_best_model
    if "metrics_lab_show_comparison" not in st.session_state:
        st.session_state["metrics_lab_show_comparison"] = True
    if "metrics_lab_model_payloads" not in st.session_state:
        st.session_state["metrics_lab_model_payloads"] = {}

    _render_active_run_context(metrics)

    st.markdown("### Model Lab")
    st.caption(
        "Choose a model manually, compare alternatives, and let the recommendation change with your decision priority."
    )
    st.warning(
        str(
            model_lab.get("proxy_warning")
            or "This ranking comes from a simulated proxy target. It supports decision-making, not biological validation."
        )
    )
    control_col1, control_col2 = st.columns(2)
    with control_col1:
        st.selectbox(
            "Select model",
            options=supported_models,
            key="metrics_lab_model_choice",
            format_func=_display_name_for_ui,
        )
    with control_col2:
        st.selectbox(
            "Select decision priority",
            options=["accuracy", "speed", "interpretability", "balanced"],
            key="metrics_lab_priority",
            format_func=display_priority_name,
        )

    selected_priority = normalize_priority(st.session_state.get("metrics_lab_priority", default_priority))
    recommended_model = recommended_model_name(metrics, selected_priority, model_df)
    selected_model = str(st.session_state.get("metrics_lab_model_choice") or recommended_model)
    selected_model_unavailable_reason = unavailable_models.get(selected_model, "")
    if not selected_model_unavailable_reason and selected_model not in available_models:
        selected_model_unavailable_reason = "not evaluated in this run"

    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    with action_col1:
        run_selected_model = st.button("Run selected model", type="primary", use_container_width=True)
    with action_col2:
        run_comparison = st.button("Run comparison", use_container_width=True)
    with action_col3:
        train_selected_model = st.button("Train only selected model", use_container_width=True)
    with action_col4:
        train_selected_model_now = st.button("Train selected model now", use_container_width=True)
    st.caption(
        "'Run selected model' activates diagnostics for the selected trained model in the current artifact set. "
        "'Train only selected model' retrains the selected classical model plus the dummy baseline from the loaded "
        "dataset using the same grouped split protocol. "
        "'Train selected model now' retrains only the selected model with the grouped split protocol."
    )

    if run_selected_model:
        if selected_model in available_models:
            st.session_state["metrics_lab_active_model"] = selected_model
            st.success(f"Diagnostics activated for {_display_name_for_ui(selected_model)}.")
        else:
            st.warning(
                f"{_display_name_for_ui(selected_model)} is not available in this artifact set. "
                "Train it first if the dependency is installed, or choose an available model."
            )
    if run_comparison:
        st.session_state["metrics_lab_show_comparison"] = True
    if train_selected_model:
        with st.spinner(f"Training {_display_name_for_ui(selected_model)} with grouped splits..."):
            updated_metrics, model_payloads, error = _train_selected_model_for_lab(dataset, metrics, selected_model)
        if updated_metrics is None:
            st.error(error)
        else:
            existing_payloads = st.session_state.get("metrics_lab_model_payloads", {}) or {}
            if isinstance(existing_payloads, dict):
                existing_payloads.update(model_payloads)
                st.session_state["metrics_lab_model_payloads"] = existing_payloads
            st.session_state["metrics"] = updated_metrics
            st.session_state["metrics_lab_active_model"] = selected_model
            st.session_state["metrics_lab_show_comparison"] = True
            st.success(
                f"Retrained {_display_name_for_ui(selected_model)} only. "
                "Refreshing diagnostics with the updated selected-model run."
            )
            st.rerun()
    if train_selected_model_now:
        with st.spinner(f"Training {_display_name_for_ui(selected_model)} with grouped splits..."):
            updated_metrics, model_payloads, error = _train_selected_model_now(dataset, metrics, selected_model)
        if updated_metrics is None:
            st.error(error)
        else:
            existing_payloads = st.session_state.get("metrics_lab_model_payloads", {}) or {}
            if isinstance(existing_payloads, dict):
                existing_payloads.update(model_payloads)
                st.session_state["metrics_lab_model_payloads"] = existing_payloads
            st.session_state["metrics"] = updated_metrics
            st.session_state["metrics_lab_active_model"] = selected_model
            st.session_state["metrics_lab_show_comparison"] = True
            st.success(
                f"Retrained {_display_name_for_ui(selected_model)}. "
                "Refreshing diagnostics with the updated selected-model run."
            )
            st.rerun()

    available_models = model_df["model"].astype(str).tolist()
    active_model = _resolve_active_model_for_diagnostics(
        available_models,
        str(st.session_state.get("metrics_lab_active_model") or recommended_model or fallback_best_model),
        recommended_model,
        fallback_best_model,
    )
    st.session_state["metrics_lab_active_model"] = active_model

    selected_metrics = _model_metrics_from_metrics(metrics, active_model)
    diagnostic_metrics = _metrics_with_prediction_vectors(selected_metrics, metrics)
    recommendation = recommendation_for_priority(model_lab, selected_priority)
    model_path = resolve_model_path_for_metrics(metrics, manifest, manifest_path, preferred_model=active_model)
    session_model_payload = _model_payload_from_session(active_model)
    model_payload = (
        session_model_payload
        if session_model_payload.get("model") is not None
        else load_best_model(str(model_path)) if model_path else {"payload": None, "model": None, "error": "No path"}
    )

    _render_model_explanation_box(selected_model, unavailable_reason=selected_model_unavailable_reason)
    if selected_model_unavailable_reason:
        st.info(
            f"{_display_name_for_ui(selected_model)} is not available in this artifact set, so the detailed diagnostics "
            f"below use {_display_name_for_ui(active_model)} instead."
        )
    if recommendation:
        st.success(
            f"Recommended model according to selected priority: {recommendation.get('display_name')}. "
            f"{recommendation.get('reason')}"
        )
    else:
        st.info("No priority-aware recommendation could be computed for this artifact.")
    _render_scoring_explanation(model_lab)

    st.markdown("### Active model metrics")
    st.caption(
        f"Active model in this session: {_display_name_for_ui(active_model)}. "
        "Use 'Run selected model' after changing the dropdown to switch the detailed diagnostics."
    )
    selected_table = _single_model_metrics_table(metrics, active_model, selected_priority)
    if selected_table.empty:
        st.warning("Selected model metrics are unavailable for this artifact.")
    else:
        st.dataframe(selected_table, use_container_width=True, hide_index=True)

    if st.session_state.get("metrics_lab_show_comparison"):
        st.markdown("### Comparison table")
        comparison_table = _model_lab_dataframe(metrics, selected_priority)
        if comparison_table.empty:
            st.warning("No supported model comparison rows were available for the Model Lab.")
        else:
            st.dataframe(
                comparison_table.drop(columns=["model", "Interpretability Raw"], errors="ignore"),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                str(
                    model_lab.get("table_note")
                    or "There is no universal winner. The recommended model changes with accuracy, speed, interpretability, or balance priorities."
                )
            )

    st.markdown("### Step 1 - What the model is trying to do")
    st.info(
        "The model predicts a simulated expression score from biological sequence features. "
        "Because the target is a proxy and not a direct lab measurement, we check whether the model "
        "beats a simple baseline and whether its decisions can be explained."
    )
    _render_metric_cards(metrics, model_df, active_model, recommended_model, baseline_model, selected_priority)

    st.markdown("### Step 2 - Is it better than a trivial prediction?")
    st.write(
        "The dummy baseline simply predicts the average score. If a real model has lower RMSE, "
        "it has learned useful structure from the features."
    )
    metric_choice = st.radio(
        "Metric to visualize",
        options=["validation_rmse", "rmse", "r2"],
        format_func=lambda value: {"validation_rmse": "Validation RMSE", "rmse": "Test RMSE", "r2": "R²"}[value],
        horizontal=True,
    )
    st.plotly_chart(plot_model_vs_baseline(model_df, metric_choice, active_model, baseline_model), use_container_width=True)
    with st.expander("Full model comparison table", expanded=False):
        st.dataframe(model_df, use_container_width=True, hide_index=True)

    st.markdown("### Step 3 - What variables drive the model globally?")
    st.write(
        "Feature importance shows which variables influence predictions the most across the whole dataset. "
        "This is a global explanation, not a proof of biological causality."
    )
    importance_df = importance_dataframe_from_metrics(metrics, active_model)
    importance_source = str(selected_metrics.get("feature_importance_source") or metrics.get("feature_importance_source") or "metrics_json")
    if importance_df.empty:
        importance_df = extract_importance_from_model(model_payload, metrics)
        importance_source = "model_artifact_fallback"
    if importance_df.empty:
        st.warning("No feature importance could be extracted from metrics or the saved model.")
    else:
        st.plotly_chart(plot_feature_importance(importance_df), use_container_width=True)
        st.caption(f"Importance source: {importance_source}")
        for line in _automatic_feature_interpretation(importance_df["feature"].head(3).astype(str).tolist()):
            st.markdown(f"- {line}")

    st.markdown("### Step 4 - Why does the model make a specific prediction?")
    st.write(
        "Feature importance explains the model globally. SHAP values explain one prediction at a time: "
        "positive contributions push the prediction up, negative contributions push it down."
    )
    if model_payload.get("error") and model_payload.get("model") is None:
        st.warning(f"Model artifact could not be loaded: {model_payload.get('error')}")
    elif dataset.empty:
        st.warning("Dataset is not loaded, so local explanations cannot be computed.")
    else:
        shap_payload = compute_shap_values(model_payload, dataset, metrics)
        if shap_payload.get("available"):
            if shap_payload.get("method") != "SHAP":
                st.info(
                    "The SHAP package was not available or could not explain this model directly. "
                    "A linear contribution fallback is shown instead."
                )
            else:
                st.success("SHAP explanations are available below as two Plotly charts: one global and one local.")
            st.caption(f"Explanation method: {shap_payload.get('method')}")

            st.markdown("#### SHAP chart 1 - Global explanation")
            st.caption(
                "This is the SHAP global summary. A longer bar means the feature changes model predictions more often "
                "or more strongly across the sampled dataset."
            )
            st.plotly_chart(plot_shap_global_summary(shap_payload), use_container_width=True)

            labels = shap_payload.get("sample_labels", [])
            st.markdown("#### SHAP chart 2 - Local explanation for one selected prediction")
            st.caption(
                "Choose one row below. The menu shows a small reproducible sample from the loaded backend dataset, "
                "so SHAP stays fast in Streamlit. Green bars push this specific prediction upward; red bars push it downward."
            )
            st.caption(str(shap_payload.get("sample_rule", "")))
            selected_position = st.selectbox(
                "Choose one prediction to explain",
                options=list(range(len(labels))),
                format_func=lambda idx: labels[idx],
            )
            pred = shap_payload.get("predictions", [np.nan])[selected_position]
            actual = shap_payload.get("actual_values", [np.nan])[selected_position]
            base_values = shap_payload.get("base_values", [np.nan])
            contribution_sums = shap_payload.get("contribution_sums", [np.nan])
            base_value = base_values[selected_position] if selected_position < len(base_values) else np.nan
            contribution_sum = contribution_sums[selected_position] if selected_position < len(contribution_sums) else np.nan
            sample_indices = shap_payload.get("sample_indices", [])
            selected_dataset_row = sample_indices[selected_position] if selected_position < len(sample_indices) else "N/A"
            selected_label = labels[selected_position] if selected_position < len(labels) else ""
            lc1, lc2, lc3, lc4 = st.columns(4)
            lc1.metric("Dataset row", str(selected_dataset_row))
            lc2.metric("Model prediction", _fmt_dashboard_metric(pred))
            lc3.metric("Proxy target", _fmt_dashboard_metric(actual))
            lc4.metric("Explanation method", str(shap_payload.get("method", "N/A")))
            eq1, eq2, eq3 = st.columns(3)
            eq1.metric("Reference prediction", _fmt_dashboard_metric(base_value))
            eq2.metric("Sum of SHAP effects", _fmt_dashboard_metric(contribution_sum))
            eq3.metric("Prediction error", _fmt_dashboard_metric(float(actual) - float(pred)))
            st.caption(_local_shap_equation_text(shap_payload, selected_position))
            st.info(_summarize_local_contributions(shap_payload, selected_position))
            st.plotly_chart(
                plot_shap_local_explanation(shap_payload, selected_position, selected_label),
                use_container_width=True,
            )
        else:
            st.warning(shap_payload.get("reason", "Local explanation unavailable."))
            if shap_payload.get("warning"):
                st.caption(str(shap_payload.get("warning")))

    st.markdown("### Step 5 - Understanding the data used by the model")
    st.write(
        "This separates model inputs from contextual fields and from the target. "
        "That distinction is important because target-derived columns must not be used as training features."
    )
    display_feature_types(metrics)

    st.markdown("### Bonus - Prediction quality and residuals")
    p1, p2 = st.columns(2)
    with p1:
        pred_fig = plot_predictions_vs_real(diagnostic_metrics)
        if pred_fig is not None:
            st.plotly_chart(pred_fig, use_container_width=True)
        else:
            st.caption("Predicted-vs-real vectors are not available in this metrics file.")
    with p2:
        residual_fig = plot_residuals(diagnostic_metrics)
        if residual_fig is not None:
            st.plotly_chart(residual_fig, use_container_width=True)
        else:
            st.caption("Residual vectors are not available in this metrics file.")

    st.markdown("### ✅ Key takeaways")
    conclusions = generate_metrics_conclusion(
        metrics,
        model_df,
        importance_df,
        active_model,
        recommended_model,
        selected_priority,
        baseline_model,
    )
    for line in conclusions:
        st.markdown(f"- {line}")

    with st.expander("Raw metrics JSON", expanded=False):
        st.json(metrics)
