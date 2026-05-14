"""Priority-aware model comparison metadata and scoring helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


INTERPRETABILITY_SCORE_MAX = 5
DEFAULT_PRIORITY = "balanced"

MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "linear_regression": {
        "display_name": "Linear Regression",
        "interpretability_score": 5,
        "what_it_does": "Fits a straight-line relationship between the features and the proxy target.",
        "when_to_choose": "Choose it when you want a fast baseline or when transparency matters more than squeezing out the last bit of accuracy.",
        "advantages": "Very fast, stable, and easy to explain to technical and business stakeholders.",
        "limitations": "Misses nonlinear interactions and can underperform when the biology-inspired feature patterns are complex.",
        "business_interpretation": "Good for transparent decision support, sanity checks, and explaining which features move the score up or down.",
        "recommended_for": "Transparent baselines, audits, and explainable decision support.",
        "short_summary": (
            "Simple, fast, highly interpretable. Useful as a baseline and when transparency is more important "
            "than predictive power."
        ),
    },
    "ridge": {
        "display_name": "Ridge Regression",
        "interpretability_score": 5,
        "what_it_does": "Adds regularization to linear regression so the model stays more stable when features are correlated.",
        "when_to_choose": "Choose it when you want linear-model transparency but need better robustness to correlated descriptors.",
        "advantages": "Interpretable, regularized, and often more stable than plain linear regression on tabular biological features.",
        "limitations": "Still mostly linear, so it can miss nonlinear patterns that ensemble methods capture better.",
        "business_interpretation": "Useful when the team wants a model that stays explainable while reducing coefficient instability.",
        "recommended_for": "Explainable modeling with extra stability on correlated features.",
        "short_summary": (
            "Similar to linear regression but more stable when features are correlated. Good for interpretable and "
            "regularized modeling."
        ),
    },
    "random_forest": {
        "display_name": "Random Forest",
        "interpretability_score": 3,
        "what_it_does": "Builds many decision trees and averages them to capture nonlinear patterns more robustly.",
        "when_to_choose": "Choose it when you want a strong tabular-data model without moving fully into boosting complexity.",
        "advantages": "Robust, handles nonlinear effects well, and usually gives a good balance between performance and explainability.",
        "limitations": "Slower and less transparent than linear models, and individual tree logic is not easy to communicate directly.",
        "business_interpretation": "Often a practical middle ground for ranking options when both predictive power and reasonable explainability matter.",
        "recommended_for": "Balanced tabular modeling with moderate explainability.",
        "short_summary": (
            "Robust ensemble model. Good balance between performance and explainability. Often useful for tabular "
            "biological features."
        ),
    },
    "xgboost": {
        "display_name": "XGBoost",
        "interpretability_score": 2,
        "what_it_does": "Trains boosted decision trees sequentially so each new tree corrects earlier mistakes.",
        "when_to_choose": "Choose it when accuracy matters most and you are comfortable with a less transparent model.",
        "advantages": "Often very strong on tabular data and can capture subtle nonlinear interactions.",
        "limitations": "Less interpretable, more sensitive to hyperparameters, and may be unavailable if the optional dependency is not installed.",
        "business_interpretation": "Use when forecast quality is the main objective and the team can accept a more opaque decision engine.",
        "recommended_for": "Accuracy-focused experiments on tabular features.",
        "short_summary": (
            "Powerful gradient boosting model. Often strong on tabular data, but less interpretable and more sensitive "
            "to hyperparameters."
        ),
    },
    "lightgbm": {
        "display_name": "LightGBM",
        "interpretability_score": 2,
        "what_it_does": "Uses gradient boosting with a fast tree-learning strategy that scales well as data volume grows.",
        "when_to_choose": "Choose it when you want a boosting model with strong speed characteristics on larger tabular datasets.",
        "advantages": "Fast boosting approach and often efficient when dataset size grows.",
        "limitations": "Less transparent than linear models and may be unavailable if the optional dependency is not installed.",
        "business_interpretation": "Useful when the workflow needs stronger speed-performance tradeoffs than classic boosting setups.",
        "recommended_for": "Fast boosted modeling as data volume grows.",
        "short_summary": (
            "Fast gradient boosting model. Useful when data volume increases and speed becomes important, but less "
            "transparent than linear models."
        ),
    },
}

PRIORITY_WEIGHTS: Dict[str, Dict[str, float]] = {
    "accuracy": {"accuracy_score": 0.7, "speed_score": 0.15, "interpretability_score_normalized": 0.15},
    "speed": {"accuracy_score": 0.15, "speed_score": 0.7, "interpretability_score_normalized": 0.15},
    "interpretability": {"accuracy_score": 0.15, "speed_score": 0.15, "interpretability_score_normalized": 0.7},
    "balanced": {"accuracy_score": 0.4, "speed_score": 0.3, "interpretability_score_normalized": 0.3},
}

PRIORITY_LABELS: Dict[str, str] = {
    "accuracy": "Accuracy",
    "speed": "Speed",
    "interpretability": "Interpretability",
    "balanced": "Balanced",
}


def list_supported_models() -> List[str]:
    return list(MODEL_REGISTRY.keys())


def normalize_priority(priority: Any) -> str:
    value = str(priority or DEFAULT_PRIORITY).strip().lower()
    return value if value in PRIORITY_WEIGHTS else DEFAULT_PRIORITY


def display_priority_name(priority: Any) -> str:
    return PRIORITY_LABELS[normalize_priority(priority)]


def get_model_metadata(model_name: str) -> Dict[str, Any]:
    metadata = MODEL_REGISTRY.get(str(model_name), {})
    if metadata:
        return dict(metadata)
    return {
        "display_name": str(model_name).replace("_", " ").title(),
        "interpretability_score": 1,
        "what_it_does": "Model metadata unavailable for this artifact.",
        "when_to_choose": "Use it only after validating its metrics in the current run.",
        "advantages": "Depends on the saved artifact.",
        "limitations": "No curated explanation is available.",
        "business_interpretation": "Treat as an advanced technical model until reviewed.",
        "recommended_for": "Artifact-specific review.",
        "short_summary": "Model metadata unavailable for this artifact.",
    }


def display_model_name(model_name: str) -> str:
    return str(get_model_metadata(model_name)["display_name"])


def unavailable_model_map(unavailable_models: Optional[Sequence[Any]]) -> Dict[str, str]:
    reasons: Dict[str, str] = {}
    for raw_value in unavailable_models or []:
        text = str(raw_value).strip()
        if not text:
            continue
        if ":" in text:
            model_name, reason = text.split(":", 1)
            reasons[model_name.strip()] = reason.strip() or "unavailable"
        else:
            reasons[text] = "optional dependency missing or model not configured"
    return reasons


def build_model_lab_payload(
    model_comparison: Mapping[str, Mapping[str, Any]],
    unavailable_models: Optional[Sequence[Any]] = None,
) -> Dict[str, Any]:
    comparison_rows: List[Dict[str, Any]] = []
    candidate_names = [model_name for model_name in list_supported_models() if model_name in model_comparison]
    unavailable_map = unavailable_model_map(unavailable_models)

    accuracy_inputs: Dict[str, Dict[str, Optional[float]]] = {}
    for model_name in candidate_names:
        metrics = model_comparison.get(model_name, {})
        accuracy_inputs[model_name] = {
            "rmse": _optional_float(metrics.get("validation_rmse", metrics.get("rmse"))),
            "mae": _optional_float(metrics.get("validation_mae", metrics.get("mae"))),
            "r2": _optional_float(metrics.get("validation_r2", metrics.get("r2"))),
        }

    rmse_scores = _normalize_values(
        {model_name: values.get("rmse") for model_name, values in accuracy_inputs.items()},
        higher_is_better=False,
    )
    mae_scores = _normalize_values(
        {model_name: values.get("mae") for model_name, values in accuracy_inputs.items()},
        higher_is_better=False,
    )
    r2_scores = _normalize_values(
        {model_name: values.get("r2") for model_name, values in accuracy_inputs.items()},
        higher_is_better=True,
    )
    training_time_scores = _normalize_values(
        {
            model_name: _optional_float(model_comparison.get(model_name, {}).get("training_time_seconds"))
            for model_name in candidate_names
        },
        higher_is_better=False,
    )
    prediction_time_scores = _normalize_values(
        {
            model_name: _optional_float(model_comparison.get(model_name, {}).get("prediction_time_seconds"))
            for model_name in candidate_names
        },
        higher_is_better=False,
    )

    for model_name in candidate_names:
        metadata = get_model_metadata(model_name)
        metrics = dict(model_comparison.get(model_name, {}))
        interpretability_score = int(metadata.get("interpretability_score", 1))
        interpretability_score_normalized = round(
            (interpretability_score / INTERPRETABILITY_SCORE_MAX) * 100.0,
            2,
        )
        accuracy_score = _weighted_mean(
            [
                (rmse_scores.get(model_name), 0.45),
                (mae_scores.get(model_name), 0.25),
                (r2_scores.get(model_name), 0.30),
            ]
        )
        speed_score = _weighted_mean(
            [
                (training_time_scores.get(model_name), 0.7),
                (prediction_time_scores.get(model_name), 0.3),
            ]
        )
        overall_scores = {
            priority: _weighted_mean(
                [
                    (accuracy_score, weights["accuracy_score"]),
                    (speed_score, weights["speed_score"]),
                    (interpretability_score_normalized, weights["interpretability_score_normalized"]),
                ]
            )
            for priority, weights in PRIORITY_WEIGHTS.items()
        }

        comparison_rows.append(
            {
                "model": model_name,
                "display_name": metadata["display_name"],
                "mae": _optional_float(metrics.get("mae")),
                "rmse": _optional_float(metrics.get("rmse")),
                "r2": _optional_float(metrics.get("r2")),
                "validation_mae": _optional_float(metrics.get("validation_mae", metrics.get("mae"))),
                "validation_rmse": _optional_float(metrics.get("validation_rmse", metrics.get("rmse"))),
                "validation_r2": _optional_float(metrics.get("validation_r2", metrics.get("r2"))),
                "training_time_seconds": _optional_float(metrics.get("training_time_seconds")),
                "prediction_time_seconds": _optional_float(metrics.get("prediction_time_seconds")),
                "interpretability_score": interpretability_score,
                "interpretability_score_max": INTERPRETABILITY_SCORE_MAX,
                "interpretability_rating": f"{interpretability_score}/{INTERPRETABILITY_SCORE_MAX}",
                "interpretability_score_normalized": interpretability_score_normalized,
                "accuracy_score": round(accuracy_score, 2),
                "speed_score": round(speed_score, 2),
                "overall_scores": {priority: round(score, 2) for priority, score in overall_scores.items()},
                "recommended_for": metadata["recommended_for"],
                "short_summary": metadata["short_summary"],
                "what_it_does": metadata["what_it_does"],
                "when_to_choose": metadata["when_to_choose"],
                "advantages": metadata["advantages"],
                "limitations": metadata["limitations"],
                "business_interpretation": metadata["business_interpretation"],
            }
        )

    priority_recommendations: Dict[str, Dict[str, Any]] = {}
    for priority in PRIORITY_WEIGHTS:
        chosen_row = _best_row_for_priority(comparison_rows, priority)
        if not chosen_row:
            continue
        priority_recommendations[priority] = {
            "priority": priority,
            "priority_label": display_priority_name(priority),
            "model": chosen_row["model"],
            "display_name": chosen_row["display_name"],
            "overall_score": chosen_row["overall_scores"][priority],
            "reason": _recommendation_reason(chosen_row, priority),
            "recommended_for": chosen_row["recommended_for"],
        }

    supported_models = []
    for model_name in list_supported_models():
        supported_models.append(
            {
                "model": model_name,
                "display_name": display_model_name(model_name),
                "available": model_name in candidate_names,
                "unavailable_reason": unavailable_map.get(model_name, ""),
            }
        )

    return {
        "version": "model_lab_v1",
        "default_priority": DEFAULT_PRIORITY,
        "supported_models": supported_models,
        "comparison_rows": comparison_rows,
        "priority_recommendations": priority_recommendations,
        "table_note": (
            "There is no universal winner. The recommended model changes with the selected decision priority: "
            "accuracy, speed, interpretability, or balance."
        ),
        "scoring_method": {
            "accuracy_score": (
                "Normalized grouped-validation performance from RMSE, MAE, and R². Lower errors and higher R² "
                "increase the score."
            ),
            "speed_score": (
                "Normalized practical runtime signal from training time and prediction time. Faster runs score higher."
            ),
            "interpretability_score": (
                "Curated 1-to-5 transparency rating based on how easy the model is to explain to stakeholders."
            ),
            "overall_score": (
                "Decision-support score created by applying the selected priority weights to accuracy, speed, "
                "and interpretability."
            ),
        },
        "priority_weights": {
            priority: dict(weights)
            for priority, weights in PRIORITY_WEIGHTS.items()
        },
        "scoring_note": (
            "Priority weights are business decision-support choices. They can be adjusted when the operational goal "
            "changes, for example from accuracy-first screening to fast iteration or auditability."
        ),
        "speed_warning": (
            "Speed depends on the runtime environment, installed libraries, hardware, dataset size, and current load. "
            "Treat it as a practical indicator for this run, not a universal benchmark."
        ),
        "proxy_warning": (
            "These rankings come from a simulated proxy target evaluated with protein-grouped splits. "
            "They support decision-making, not biological validation."
        ),
    }


def annotate_model_comparison(
    model_comparison: Mapping[str, Mapping[str, Any]],
    unavailable_models: Optional[Sequence[Any]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    annotated: Dict[str, Dict[str, Any]] = {
        model_name: dict(metrics)
        for model_name, metrics in model_comparison.items()
    }
    payload = build_model_lab_payload(model_comparison, unavailable_models=unavailable_models)
    rows_by_model = {row["model"]: row for row in payload.get("comparison_rows", [])}

    for model_name, row in rows_by_model.items():
        annotated.setdefault(model_name, {})
        annotated[model_name].update(
            {
                "display_name": row["display_name"],
                "training_time_seconds": row["training_time_seconds"],
                "prediction_time_seconds": row["prediction_time_seconds"],
                "interpretability_score": row["interpretability_score"],
                "interpretability_score_max": row["interpretability_score_max"],
                "interpretability_rating": row["interpretability_rating"],
                "interpretability_score_normalized": row["interpretability_score_normalized"],
                "accuracy_score": row["accuracy_score"],
                "speed_score": row["speed_score"],
                "overall_scores": dict(row["overall_scores"]),
                "recommended_for": row["recommended_for"],
                "short_summary": row["short_summary"],
                "what_it_does": row["what_it_does"],
                "when_to_choose": row["when_to_choose"],
                "advantages": row["advantages"],
                "limitations": row["limitations"],
                "business_interpretation": row["business_interpretation"],
            }
        )

    return annotated, payload


def recommendation_for_priority(model_lab_payload: Mapping[str, Any], priority: Any) -> Dict[str, Any]:
    normalized_priority = normalize_priority(priority)
    recommendations = model_lab_payload.get("priority_recommendations", {})
    if isinstance(recommendations, Mapping):
        recommendation = recommendations.get(normalized_priority, {})
        if isinstance(recommendation, Mapping):
            return dict(recommendation)
    return {}


def model_lab_payload_from_metrics(metrics: Mapping[str, Any]) -> Dict[str, Any]:
    payload = metrics.get("model_lab", {})
    if isinstance(payload, Mapping) and payload.get("comparison_rows"):
        return dict(payload)
    model_comparison = metrics.get("model_comparison", {})
    if isinstance(model_comparison, Mapping):
        return build_model_lab_payload(
            model_comparison,
            unavailable_models=metrics.get("unavailable_models", []),
        )
    return build_model_lab_payload({}, unavailable_models=metrics.get("unavailable_models", []))


def _best_row_for_priority(rows: Sequence[Mapping[str, Any]], priority: str) -> Optional[Dict[str, Any]]:
    if not rows:
        return None

    normalized_priority = normalize_priority(priority)
    ranked_rows = sorted(
        rows,
        key=lambda row: (
            _optional_float((row.get("overall_scores") or {}).get(normalized_priority), default=-1.0),
            _optional_float(row.get("accuracy_score"), default=-1.0),
            _optional_float(row.get("speed_score"), default=-1.0),
            _optional_float(row.get("interpretability_score_normalized"), default=-1.0),
        ),
        reverse=True,
    )
    return dict(ranked_rows[0]) if ranked_rows else None


def _recommendation_reason(row: Mapping[str, Any], priority: str) -> str:
    label = str(row.get("display_name", row.get("model", "Selected model")))
    if priority == "accuracy":
        return (
            f"{label} is recommended because it produced the strongest grouped-evaluation accuracy profile "
            f"across MAE, RMSE, and R² in this run."
        )
    if priority == "speed":
        return (
            f"{label} is recommended because it offers the strongest speed profile from training and prediction time "
            f"while still remaining competitive on accuracy."
        )
    if priority == "interpretability":
        return (
            f"{label} is recommended because it is easier to explain to stakeholders while still giving usable proxy-model performance."
        )
    return (
        f"{label} is recommended because it offers the most balanced trade-off between accuracy, speed, and interpretability "
        f"for this run."
    )


def _normalize_values(
    values: Mapping[str, Optional[float]],
    *,
    higher_is_better: bool,
) -> Dict[str, Optional[float]]:
    finite_values = [float(value) for value in values.values() if value is not None]
    if not finite_values:
        return {key: None for key in values}

    min_value = min(finite_values)
    max_value = max(finite_values)
    if abs(max_value - min_value) <= 1e-12:
        return {key: (100.0 if value is not None else None) for key, value in values.items()}

    normalized: Dict[str, Optional[float]] = {}
    for key, value in values.items():
        if value is None:
            normalized[key] = None
            continue
        ratio = (float(value) - min_value) / (max_value - min_value)
        score = ratio * 100.0 if higher_is_better else (1.0 - ratio) * 100.0
        normalized[key] = round(score, 2)
    return normalized


def _weighted_mean(values_and_weights: Sequence[Tuple[Optional[float], float]]) -> float:
    numerator = 0.0
    denominator = 0.0
    for value, weight in values_and_weights:
        if value is None:
            continue
        numerator += float(value) * float(weight)
        denominator += float(weight)
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _optional_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
