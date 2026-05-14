"""Grouped, leakage-controlled training helpers."""

from __future__ import annotations

import importlib
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, RandomizedSearchCV, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import TrainingConfig
from .model_lab import (
    DEFAULT_PRIORITY,
    annotate_model_comparison,
    display_priority_name,
    recommendation_for_priority,
)
from .schema import (
    CATEGORICAL_MODEL_FEATURES,
    DESCRIPTIVE_ONLY_COLUMNS,
    FEATURE_BLOCKS,
    FEATURE_PRIORITY,
    GENERATED_MODEL_FEATURES,
    GROUP_COLUMN,
    LEGACY_TARGET_COLUMN,
    PROXY_TARGET_COLUMN,
    PROXY_TARGET_VERSION,
    TARGET_DERIVED_COLUMNS,
    UNIFIED_MODEL_FEATURES,
)


@dataclass(frozen=True)
class _FeatureSelectionArtifacts:
    frame: pd.DataFrame
    feature_names: List[str]
    numeric_features: List[str]
    categorical_features: List[str]
    feature_selection_payload: Dict[str, Any]
    feature_roles_payload: Dict[str, Any]
    constant_feature_warnings: List[Dict[str, Any]]


@dataclass(frozen=True)
class _PreparedTrainingData:
    x: pd.DataFrame
    y: np.ndarray
    groups: np.ndarray
    target_column: str
    group_column: str
    unique_group_count: int
    feature_names: List[str]
    numeric_features: List[str]
    categorical_features: List[str]
    feature_selection_payload: Dict[str, Any]
    feature_roles_payload: Dict[str, Any]
    constant_feature_warnings: List[Dict[str, Any]]
    target_dependency_diagnostics: Dict[str, Any]
    base_meta: Dict[str, Any]


@dataclass(frozen=True)
class _GroupedSplitArtifacts:
    x_train: pd.DataFrame
    x_test: pd.DataFrame
    x_fit: pd.DataFrame
    x_val: pd.DataFrame
    y_train: np.ndarray
    y_test: np.ndarray
    y_fit: np.ndarray
    y_val: np.ndarray
    train_groups: np.ndarray
    test_groups: np.ndarray
    fit_groups: np.ndarray
    validation_groups: np.ndarray


def train_model_grouped_impl(
    dataset: List[Dict[str, Any]],
    config: TrainingConfig,
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Train surrogate regressors with protein-grouped evaluation and sklearn pipelines."""
    prepared = _prepare_training_data(dataset, config)
    if isinstance(prepared, tuple):
        return prepared

    split_artifacts = _build_grouped_splits(prepared, config)
    if isinstance(split_artifacts, tuple):
        return split_artifacts

    models, unavailable_models = _build_model_catalog(
        config,
        prepared.numeric_features,
        prepared.categorical_features,
    )
    model_results, model_payloads, model_eval_cache, unavailable_models = _fit_and_evaluate_models(
        prepared,
        split_artifacts,
        config,
        models,
        unavailable_models,
    )
    model_results, model_lab_payload = annotate_model_comparison(
        model_results,
        unavailable_models=unavailable_models,
    )
    if not model_results:
        return _skip_training_result(
            "No model could be trained successfully.",
            prepared,
            unavailable_models=unavailable_models,
        ), {}

    candidate_results = {
        model_name: scores
        for model_name, scores in model_results.items()
        if model_name != "dummy_mean_baseline"
    }
    selection_results = dict(candidate_results) if candidate_results else dict(model_results)
    best_candidate_model_name = min(
        selection_results.items(),
        key=lambda item: item[1].get("validation_rmse", float("inf")),
    )[0]

    selection = _select_best_model(
        prepared,
        split_artifacts,
        config,
        model_results,
        candidate_results,
        best_candidate_model_name,
    )

    best_model_name = str(selection["best_model_name"])
    best_metrics = model_results[best_model_name]
    default_priority_recommendation = recommendation_for_priority(model_lab_payload, DEFAULT_PRIORITY)
    best_importances, best_importance_source = _normalized_permutation_importance(
        model_payloads[best_model_name]["model"],
        split_artifacts.x_val,
        split_artifacts.y_val,
        prepared.feature_names,
        config.random_state,
    )
    best_eval_payload = model_eval_cache.get(best_model_name, {})

    ablation_study = _build_ablation_study(prepared, split_artifacts)
    feature_importance_table = _build_feature_importance_table(prepared.feature_names, best_importances)
    top_feature_names = [row["feature"] for row in feature_importance_table[:3]]
    selection["interpretation_summary"] = {
        "top_features": feature_importance_table[:5],
        "plain_language": (
            f"Top model signals: {', '.join(top_feature_names) if top_feature_names else 'N/A'}. "
            "Feature importances are computed by permutation on the grouped validation split, "
            "so they describe model sensitivity under the same leakage-controlled protocol."
        ),
        "caution": (
            "These explanations describe a model trained on a simulated proxy target. "
            "They support transparent ranking, not experimental causality."
        ),
    }

    metrics: Dict[str, Any] = {
        "training_enabled": True,
        "proxy_on_proxy": True,
        "best_model": best_model_name,
        "best_model_name": best_model_name,
        "best_model_score": best_metrics.get("validation_rmse"),
        "best_candidate_model": best_candidate_model_name,
        "models_trained": list(model_results.keys()),
        "models_used_for_selection": list(selection_results.keys()),
        "baseline_model": "dummy_mean_baseline",
        "model_comparison": model_results,
        "rmse": best_metrics.get("rmse"),
        "mae": best_metrics.get("mae"),
        "r2": best_metrics.get("r2"),
        "validation_rmse": best_metrics.get("validation_rmse"),
        "validation_mae": best_metrics.get("validation_mae"),
        "validation_r2": best_metrics.get("validation_r2"),
        "training_time_seconds": best_metrics.get("training_time_seconds"),
        "prediction_time_seconds": best_metrics.get("prediction_time_seconds"),
        "accuracy_score": best_metrics.get("accuracy_score"),
        "speed_score": best_metrics.get("speed_score"),
        "interpretability_score": best_metrics.get("interpretability_score"),
        "interpretability_rating": best_metrics.get("interpretability_rating"),
        "cv_rmse_mean": best_metrics.get("cv_rmse_mean"),
        "cv_rmse_std": best_metrics.get("cv_rmse_std"),
        "train_samples": int(len(split_artifacts.x_train)),
        "test_samples": int(len(split_artifacts.x_test)),
        "validation_samples": int(len(split_artifacts.x_val)),
        "fit_samples": int(len(split_artifacts.x_fit)),
        "train_group_count": len(set(split_artifacts.train_groups.tolist())),
        "test_group_count": len(set(split_artifacts.test_groups.tolist())),
        "validation_group_count": len(set(split_artifacts.validation_groups.tolist())),
        "fit_group_count": len(set(split_artifacts.fit_groups.tolist())),
        "unique_group_count": prepared.unique_group_count,
        "train_test_group_overlap_count": selection["train_test_group_overlap_count"],
        "fit_validation_group_overlap_count": selection["fit_validation_group_overlap_count"],
        "feature_names": list(prepared.feature_names),
        "numeric_feature_names": list(prepared.numeric_features),
        "categorical_feature_names": list(prepared.categorical_features),
        "encoded_feature_names": model_payloads[best_model_name].get("encoded_feature_names", []),
        "feature_selection": prepared.feature_selection_payload,
        "feature_roles": prepared.feature_roles_payload,
        "constant_feature_warnings": prepared.constant_feature_warnings,
        "feature_importances": best_importances,
        "feature_importance_source": best_importance_source,
        "feature_importance_table": feature_importance_table,
        "top_features": feature_importance_table[:10],
        "target_dependency_diagnostics": prepared.target_dependency_diagnostics,
        "default_decision_priority": display_priority_name(DEFAULT_PRIORITY),
        "priority_recommendations": model_lab_payload.get("priority_recommendations", {}),
        "recommended_model_by_default_priority": default_priority_recommendation.get("model"),
        "recommended_model_label_by_default_priority": default_priority_recommendation.get("display_name"),
        "recommended_model_reason_by_default_priority": default_priority_recommendation.get("reason"),
        "model_lab": model_lab_payload,
        "baseline_comparison": selection["baseline_comparison"],
        "model_selection_report": selection["model_selection_report"],
        "interpretation_summary": selection["interpretation_summary"],
        "ablation_study": ablation_study,
        "actual_values": best_eval_payload.get("test_actual_values", []),
        "predicted_values": best_eval_payload.get("test_predicted_values", []),
        "residual_values": best_eval_payload.get("test_residual_values", []),
        "test_actual_values": best_eval_payload.get("test_actual_values", []),
        "test_predicted_values": best_eval_payload.get("test_predicted_values", []),
        "test_residual_values": best_eval_payload.get("test_residual_values", []),
        "validation_actual_values": best_eval_payload.get("validation_actual_values", []),
        "validation_predicted_values": best_eval_payload.get("validation_predicted_values", []),
        "validation_residual_values": best_eval_payload.get("validation_residual_values", []),
        "credibility_checks": selection["credibility_checks"],
        "ml_pipeline_schema": _ml_pipeline_schema(prepared.target_column),
        "unavailable_models": unavailable_models,
        "note": (
            "This model is trained on a simulated proxy target. Grouped evaluation makes the "
            "ML protocol more credible, but results remain a computational ranking aid, not "
            "wet-lab evidence."
        ),
        **prepared.base_meta,
    }
    if best_metrics.get("best_params"):
        metrics["best_params"] = best_metrics["best_params"]
    return metrics, model_payloads


def _prepare_training_data(
    dataset: List[Dict[str, Any]],
    config: TrainingConfig,
) -> _PreparedTrainingData | Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    df = pd.DataFrame(dataset)
    target_column = PROXY_TARGET_COLUMN if PROXY_TARGET_COLUMN in df.columns else LEGACY_TARGET_COLUMN
    group_column = GROUP_COLUMN if GROUP_COLUMN in df.columns else ("accession" if "accession" in df.columns else None)
    evaluation_protocol = "protein_grouped_train_validation_test_split"
    base_meta = {
        "total_samples": int(len(dataset)),
        "save_model_enabled": config.save_model,
        "target_column": target_column,
        "legacy_target_alias": LEGACY_TARGET_COLUMN,
        "group_column": group_column,
        "evaluation_protocol": evaluation_protocol,
        "proxy_model_statement": (
            "This is a surrogate ML model trained on a simulated proxy score. "
            "It is evaluated with protein-grouped splits and is not experimental biology."
        ),
    }

    if df.empty:
        return _skip_training_result("Dataset is empty.", base_meta=base_meta), {}

    feature_artifacts = _select_feature_columns(df)
    if not feature_artifacts.feature_names:
        return _skip_training_result(
            "No usable feature columns were found in the dataset.",
            base_meta=base_meta,
            feature_names=[],
            feature_selection=feature_artifacts.feature_selection_payload,
        ), {}

    target_series = _resolve_target_series(df, target_column)
    if target_series is None and target_column != LEGACY_TARGET_COLUMN:
        target_column = LEGACY_TARGET_COLUMN
        base_meta["target_column"] = target_column
        target_series = _resolve_target_series(df, target_column)
    if target_series is None:
        return _skip_training_result(
            f"{target_column} is missing or invalid.",
            base_meta=base_meta,
            feature_names=feature_artifacts.feature_names,
            feature_selection=feature_artifacts.feature_selection_payload,
        ), {}

    valid_mask = target_series.notna().to_numpy()
    x = feature_artifacts.frame.loc[valid_mask, feature_artifacts.numeric_features].copy()
    for feature_name in feature_artifacts.categorical_features:
        x[feature_name] = (
            df.loc[valid_mask, feature_name]
            .astype("string")
            .fillna("Unknown")
            .astype(str)
        )
    y = target_series.loc[valid_mask].to_numpy(dtype=float)

    group_column, groups = _build_groups(df, valid_mask, x.index, group_column)
    base_meta["group_column"] = group_column
    unique_group_count = int(np.unique(groups).size)
    target_dependency_diagnostics = _build_target_dependency_diagnostics(
        x,
        y,
        feature_artifacts.numeric_features,
        target_column,
    )

    min_samples_required = 25
    if len(y) < min_samples_required:
        return _skip_training_result(
            f"Dataset too small for robust multi-model training (minimum {min_samples_required} rows).",
            base_meta=base_meta,
            feature_names=feature_artifacts.feature_names,
            feature_selection=feature_artifacts.feature_selection_payload,
        ), {}
    if unique_group_count < 5:
        return _skip_training_result(
            "Too few protein groups for grouped train/validation/test evaluation.",
            base_meta=base_meta,
            feature_names=feature_artifacts.feature_names,
            feature_selection=feature_artifacts.feature_selection_payload,
            unique_group_count=unique_group_count,
        ), {}
    if np.unique(y).size <= 1:
        return _skip_training_result(
            "Target values are constant; model comparison is not informative.",
            base_meta=base_meta,
            feature_names=feature_artifacts.feature_names,
            feature_selection=feature_artifacts.feature_selection_payload,
        ), {}

    return _PreparedTrainingData(
        x=x,
        y=y,
        groups=groups,
        target_column=target_column,
        group_column=group_column,
        unique_group_count=unique_group_count,
        feature_names=list(feature_artifacts.feature_names),
        numeric_features=list(feature_artifacts.numeric_features),
        categorical_features=list(feature_artifacts.categorical_features),
        feature_selection_payload=feature_artifacts.feature_selection_payload,
        feature_roles_payload=feature_artifacts.feature_roles_payload,
        constant_feature_warnings=feature_artifacts.constant_feature_warnings,
        target_dependency_diagnostics=target_dependency_diagnostics,
        base_meta=base_meta,
    )


def _select_feature_columns(df: pd.DataFrame) -> _FeatureSelectionArtifacts:
    feature_pool = list(dict.fromkeys(UNIFIED_MODEL_FEATURES + GENERATED_MODEL_FEATURES))
    feature_pool = [
        feature
        for feature in feature_pool
        if feature not in TARGET_DERIVED_COLUMNS and feature not in DESCRIPTIVE_ONLY_COLUMNS
    ]

    available_series: Dict[str, pd.Series] = {}
    for feature_name in feature_pool:
        series = _numeric_series(df, feature_name)
        if series is not None:
            available_series[feature_name] = series

    if "protein_length" not in available_series:
        fallback_length = _numeric_series(df, "sequence_length_aa")
        if fallback_length is not None:
            available_series["protein_length"] = fallback_length
            if "protein_length" not in feature_pool:
                feature_pool.append("protein_length")

    cai_series = available_series.get("cai")
    gc_content_series = available_series.get("gc_content")
    rare_codon_series = available_series.get("rare_codon_ratio")
    if gc_content_series is not None:
        gc_percent = gc_content_series.apply(_to_percent_value)
        available_series["gc_deviation"] = (gc_percent - 52.5).abs()
    if cai_series is not None and rare_codon_series is not None:
        rare_ratio = rare_codon_series.apply(_to_ratio_value).clip(lower=0.0, upper=1.0)
        available_series["codon_efficiency"] = cai_series * (1.0 - rare_ratio)
    if gc_content_series is not None and rare_codon_series is not None:
        gc_percent = gc_content_series.apply(_to_percent_value)
        rare_ratio = rare_codon_series.apply(_to_ratio_value).clip(lower=0.0, upper=1.0)
        available_series["stability_index"] = gc_percent * (1.0 - rare_ratio)

    feature_frame = pd.DataFrame(index=df.index)
    selected_numeric_features: List[str] = []
    feature_diagnostics: List[Dict[str, Any]] = []
    total_rows = max(int(len(df)), 1)

    for feature_name in feature_pool:
        series = available_series.get(feature_name)
        if series is None:
            feature_diagnostics.append(
                {
                    "feature": feature_name,
                    "status": "excluded",
                    "reason": "missing_or_non_numeric",
                    "non_null_count": 0,
                    "missing_ratio": 1.0,
                    "unique_values": 0,
                    "variance": 0.0,
                    "imputation_value": None,
                }
            )
            continue

        clean_series = pd.to_numeric(series, errors="coerce")
        non_null_count = int(clean_series.notna().sum())
        missing_ratio = round(float(1.0 - (non_null_count / total_rows)), 6)
        if non_null_count == 0:
            feature_diagnostics.append(
                {
                    "feature": feature_name,
                    "status": "excluded",
                    "reason": "all_nan",
                    "non_null_count": 0,
                    "missing_ratio": 1.0,
                    "unique_values": 0,
                    "variance": 0.0,
                    "imputation_value": None,
                }
            )
            continue

        median_value = clean_series.median(skipna=True)
        fill_value = 0.0 if pd.isna(median_value) else float(median_value)
        filled_series = clean_series.fillna(fill_value)
        unique_values = int(filled_series.nunique(dropna=True))
        variance = float(np.var(filled_series.to_numpy(dtype=float)))
        if unique_values <= 1:
            feature_diagnostics.append(
                {
                    "feature": feature_name,
                    "status": "excluded",
                    "reason": "constant_feature",
                    "non_null_count": non_null_count,
                    "missing_ratio": missing_ratio,
                    "unique_values": unique_values,
                    "variance": round(variance, 10),
                    "imputation_value": round(fill_value, 6),
                }
            )
            continue
        if variance <= 1e-12:
            feature_diagnostics.append(
                {
                    "feature": feature_name,
                    "status": "excluded",
                    "reason": "near_zero_variance",
                    "non_null_count": non_null_count,
                    "missing_ratio": missing_ratio,
                    "unique_values": unique_values,
                    "variance": round(variance, 10),
                    "imputation_value": round(fill_value, 6),
                }
            )
            continue

        feature_frame[feature_name] = clean_series
        selected_numeric_features.append(feature_name)
        feature_diagnostics.append(
            {
                "feature": feature_name,
                "status": "selected",
                "reason": "usable",
                "non_null_count": non_null_count,
                "missing_ratio": missing_ratio,
                "unique_values": unique_values,
                "variance": round(variance, 10),
                "imputation_value": round(fill_value, 6),
            }
        )

    correlation_threshold = 0.98
    correlation_exclusions = _correlation_exclusions(feature_frame, selected_numeric_features, feature_pool)
    if correlation_exclusions:
        selected_numeric_features = [
            feature for feature in selected_numeric_features if feature not in correlation_exclusions
        ]
        feature_frame = feature_frame[selected_numeric_features].copy()
        for diagnostic in feature_diagnostics:
            feature_name = str(diagnostic.get("feature"))
            if feature_name in correlation_exclusions:
                diagnostic["status"] = "excluded"
                diagnostic["reason"] = correlation_exclusions[feature_name]

    categorical_features, categorical_diagnostics = _categorical_feature_diagnostics(df, total_rows)
    excluded_features = [
        {"feature": row.get("feature"), "reason": row.get("reason")}
        for row in feature_diagnostics
        if row.get("status") != "selected"
    ]
    excluded_features.extend(
        {"feature": row.get("feature"), "reason": row.get("reason")}
        for row in categorical_diagnostics
        if row.get("status") != "selected"
    )
    constant_feature_warnings = [
        {
            "feature": row.get("feature"),
            "reason": row.get("reason"),
            "unique_values": row.get("unique_values"),
        }
        for row in feature_diagnostics + categorical_diagnostics
        if str(row.get("reason", "")).startswith("constant")
    ]
    input_feature_names = list(selected_numeric_features) + list(categorical_features)
    feature_roles_payload = {
        "used_by_model": list(input_feature_names),
        "used_numeric": list(selected_numeric_features),
        "used_categorical": list(categorical_features),
        "descriptive_only": list(DESCRIPTIVE_ONLY_COLUMNS),
        "target_derived_excluded": list(TARGET_DERIVED_COLUMNS),
        "generated_candidate_features": list(GENERATED_MODEL_FEATURES),
    }
    feature_selection_payload = {
        "candidate_feature_count": len(feature_pool) + len(CATEGORICAL_MODEL_FEATURES),
        "selected_feature_count": len(input_feature_names),
        "excluded_feature_count": len(excluded_features),
        "selected_features": list(input_feature_names),
        "selected_numeric_features": list(selected_numeric_features),
        "selected_categorical_features": list(categorical_features),
        "excluded_features": excluded_features,
        "feature_diagnostics": feature_diagnostics + categorical_diagnostics,
        "constant_feature_warnings": constant_feature_warnings,
        "feature_roles": feature_roles_payload,
        "correlation_threshold": correlation_threshold,
        "strategy": "quality_filtering_plus_high_correlation_pruning",
    }
    return _FeatureSelectionArtifacts(
        frame=feature_frame,
        feature_names=input_feature_names,
        numeric_features=selected_numeric_features,
        categorical_features=categorical_features,
        feature_selection_payload=feature_selection_payload,
        feature_roles_payload=feature_roles_payload,
        constant_feature_warnings=constant_feature_warnings,
    )


def _build_grouped_splits(
    prepared: _PreparedTrainingData,
    config: TrainingConfig,
) -> _GroupedSplitArtifacts | Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    try:
        group_splitter = GroupShuffleSplit(
            n_splits=1,
            test_size=config.test_size,
            random_state=config.random_state,
        )
        train_idx, test_idx = next(group_splitter.split(prepared.x, prepared.y, groups=prepared.groups))
    except ValueError as exc:
        return _skip_training_result(
            f"Grouped train/test split failed: {exc}",
            prepared,
            unique_group_count=prepared.unique_group_count,
        ), {}

    x_train = prepared.x.iloc[train_idx].copy()
    x_test = prepared.x.iloc[test_idx].copy()
    y_train = prepared.y[train_idx]
    y_test = prepared.y[test_idx]
    train_groups = prepared.groups[train_idx]
    test_groups = prepared.groups[test_idx]
    if len(x_train) < 10 or len(x_test) < 3:
        return _skip_training_result(
            "Train/test split is too small for reliable evaluation.",
            prepared,
            train_samples=int(len(x_train)),
            test_samples=int(len(x_test)),
        ), {}

    try:
        validation_splitter = GroupShuffleSplit(
            n_splits=1,
            test_size=0.2,
            random_state=config.random_state,
        )
        fit_rel_idx, val_rel_idx = next(validation_splitter.split(x_train, y_train, groups=train_groups))
    except ValueError as exc:
        return _skip_training_result(
            f"Grouped fit/validation split failed: {exc}",
            prepared,
            train_samples=int(len(x_train)),
            test_samples=int(len(x_test)),
        ), {}

    x_fit = x_train.iloc[fit_rel_idx].copy()
    x_val = x_train.iloc[val_rel_idx].copy()
    y_fit = y_train[fit_rel_idx]
    y_val = y_train[val_rel_idx]
    fit_groups = train_groups[fit_rel_idx]
    validation_groups = train_groups[val_rel_idx]
    if len(x_fit) < 8 or len(x_val) < 3:
        return _skip_training_result(
            "Fit/validation split is too small.",
            prepared,
            train_samples=int(len(x_train)),
            test_samples=int(len(x_test)),
            validation_samples=int(len(x_val)),
        ), {}

    return _GroupedSplitArtifacts(
        x_train=x_train,
        x_test=x_test,
        x_fit=x_fit,
        x_val=x_val,
        y_train=y_train,
        y_test=y_test,
        y_fit=y_fit,
        y_val=y_val,
        train_groups=train_groups,
        test_groups=test_groups,
        fit_groups=fit_groups,
        validation_groups=validation_groups,
    )


def _build_model_catalog(
    config: TrainingConfig,
    numeric_features: List[str],
    categorical_features: List[str],
) -> Tuple[Dict[str, Any], List[str]]:
    models: Dict[str, Any] = {
        "dummy_mean_baseline": _make_model_pipeline(
            DummyRegressor(strategy="mean"),
            numeric_features,
            categorical_features,
            scale_numeric=False,
        ),
        "linear_regression": _make_model_pipeline(
            LinearRegression(),
            numeric_features,
            categorical_features,
            scale_numeric=True,
        ),
        "ridge": _make_model_pipeline(
            Ridge(alpha=1.0),
            numeric_features,
            categorical_features,
            scale_numeric=True,
        ),
        "random_forest": _make_model_pipeline(
            RandomForestRegressor(
                n_estimators=config.rf_n_estimators,
                max_depth=config.rf_max_depth,
                min_samples_split=config.min_samples_split,
                min_samples_leaf=config.min_samples_leaf,
                random_state=config.random_state,
                n_jobs=1,
            ),
            numeric_features,
            categorical_features,
            scale_numeric=False,
        ),
    }
    unavailable_models: List[str] = []

    xgb_module = _import_optional_module("xgboost")
    if xgb_module is not None:
        models["xgboost"] = _make_model_pipeline(
            xgb_module.XGBRegressor(
                n_estimators=config.xgb_n_estimators,
                max_depth=config.xgb_max_depth,
                learning_rate=config.xgb_learning_rate,
                subsample=config.xgb_subsample,
                colsample_bytree=config.xgb_colsample_bytree,
                objective="reg:squarederror",
                random_state=config.random_state,
                n_jobs=1,
                verbosity=0,
            ),
            numeric_features,
            categorical_features,
            scale_numeric=False,
        )
    else:
        unavailable_models.append("xgboost")

    lgb_module = _import_optional_module("lightgbm")
    if lgb_module is not None:
        models["lightgbm"] = _make_model_pipeline(
            lgb_module.LGBMRegressor(
                n_estimators=350,
                learning_rate=0.05,
                max_depth=-1,
                random_state=config.random_state,
                n_jobs=1,
                verbose=-1,
            ),
            numeric_features,
            categorical_features,
            scale_numeric=False,
        )
    else:
        unavailable_models.append("lightgbm")

    if config.enabled_models:
        requested_models = {str(name) for name in config.enabled_models}
        available_requested_models = {
            model_name: model
            for model_name, model in models.items()
            if model_name in requested_models
        }
        missing_requested_models = sorted(requested_models - set(available_requested_models))
        unavailable_models.extend(
            f"{model_name}: not_available_or_not_configured"
            for model_name in missing_requested_models
        )
        models = available_requested_models

    if len(models) < 5 and not config.enabled_models:
        models["gradient_boosting_fallback"] = _make_model_pipeline(
            GradientBoostingRegressor(random_state=config.random_state),
            numeric_features,
            categorical_features,
            scale_numeric=False,
        )
    return models, unavailable_models


def _fit_and_evaluate_models(
    prepared: _PreparedTrainingData,
    split_artifacts: _GroupedSplitArtifacts,
    config: TrainingConfig,
    models: Dict[str, Any],
    unavailable_models: List[str],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, List[float]]], List[str]]:
    model_results: Dict[str, Dict[str, Any]] = {}
    model_payloads: Dict[str, Dict[str, Any]] = {}
    model_eval_cache: Dict[str, Dict[str, List[float]]] = {}
    y_test_list = _float_list(split_artifacts.y_test)
    y_val_list = _float_list(split_artifacts.y_val)
    cv_group_count = int(np.unique(split_artifacts.fit_groups).size)

    for model_name, base_model in models.items():
        model, best_params = _tune_model(
            model_name,
            base_model,
            split_artifacts,
            config,
            cv_group_count,
        )
        try:
            fit_start = time.perf_counter()
            model.fit(split_artifacts.x_fit, split_artifacts.y_fit)
            training_time_seconds = time.perf_counter() - fit_start
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            unavailable_models.append(f"{model_name}: {exc}")
            continue

        prediction_start = time.perf_counter()
        val_predictions = np.asarray(model.predict(split_artifacts.x_val), dtype=float)
        test_predictions = np.asarray(model.predict(split_artifacts.x_test), dtype=float)
        prediction_time_seconds = time.perf_counter() - prediction_start
        validation_rmse = _rmse(split_artifacts.y_val, val_predictions)
        validation_mae = float(mean_absolute_error(split_artifacts.y_val, val_predictions))
        validation_r2 = float(r2_score(split_artifacts.y_val, val_predictions))
        test_rmse = _rmse(split_artifacts.y_test, test_predictions)
        test_mae = float(mean_absolute_error(split_artifacts.y_test, test_predictions))
        test_r2 = float(r2_score(split_artifacts.y_test, test_predictions))

        model_eval_cache[model_name] = {
            "test_actual_values": y_test_list,
            "test_predicted_values": _float_list(test_predictions),
            "test_residual_values": _float_list(np.asarray(split_artifacts.y_test, dtype=float) - test_predictions),
            "validation_actual_values": y_val_list,
            "validation_predicted_values": _float_list(val_predictions),
            "validation_residual_values": _float_list(np.asarray(split_artifacts.y_val, dtype=float) - val_predictions),
        }

        cv_rmse_mean = None
        cv_rmse_std = None
        train_group_count = int(np.unique(split_artifacts.train_groups).size)
        if len(split_artifacts.x_train) >= 5 and train_group_count >= 2:
            cv = GroupKFold(n_splits=min(5, train_group_count))
            try:
                cv_scores = cross_val_score(
                    clone(model),
                    split_artifacts.x_train,
                    split_artifacts.y_train,
                    cv=cv,
                    groups=split_artifacts.train_groups,
                    scoring="neg_mean_squared_error",
                    n_jobs=1,
                )
                cv_rmse = np.sqrt(np.maximum(0.0, -cv_scores))
                cv_rmse_mean = float(cv_rmse.mean())
                cv_rmse_std = float(cv_rmse.std())
            except ValueError:
                cv_rmse_mean = None
                cv_rmse_std = None

        feature_importances, importance_source = _normalized_permutation_importance(
            model,
            split_artifacts.x_val,
            split_artifacts.y_val,
            prepared.feature_names,
            config.random_state,
        )
        result: Dict[str, Any] = {
            "rmse": round(test_rmse, 4),
            "mae": round(test_mae, 4),
            "r2": round(test_r2, 4),
            "validation_rmse": round(validation_rmse, 4),
            "validation_mae": round(validation_mae, 4),
            "validation_r2": round(validation_r2, 4),
            "training_time_seconds": round(float(training_time_seconds), 6),
            "prediction_time_seconds": round(float(prediction_time_seconds), 6),
            "feature_names": list(prepared.feature_names),
            "test_actual_values": y_test_list,
            "test_predicted_values": _float_list(test_predictions),
            "test_residual_values": _float_list(np.asarray(split_artifacts.y_test, dtype=float) - test_predictions),
            "validation_actual_values": y_val_list,
            "validation_predicted_values": _float_list(val_predictions),
            "validation_residual_values": _float_list(np.asarray(split_artifacts.y_val, dtype=float) - val_predictions),
        }
        if cv_rmse_mean is not None:
            result["cv_rmse_mean"] = round(cv_rmse_mean, 4)
        if cv_rmse_std is not None:
            result["cv_rmse_std"] = round(cv_rmse_std, 4)
        if best_params:
            result["best_params"] = best_params
        if model_name == "dummy_mean_baseline":
            result["model_role"] = "baseline"
        if feature_importances:
            result["feature_importances"] = feature_importances
            result["feature_importance_source"] = importance_source
            result["feature_importance_table"] = _build_feature_importance_table(
                prepared.feature_names,
                feature_importances,
            )

        model_results[model_name] = result
        model_payloads[model_name] = {
            "model": model,
            "feature_names": list(prepared.feature_names),
            "numeric_feature_names": list(prepared.numeric_features),
            "categorical_feature_names": list(prepared.categorical_features),
            "encoded_feature_names": _encoded_feature_names(model, prepared.feature_names),
            "target_column": prepared.target_column,
            "group_column": prepared.group_column,
            "evaluation_protocol": prepared.base_meta["evaluation_protocol"],
            "best_params": best_params,
        }

    return model_results, model_payloads, model_eval_cache, unavailable_models


def _select_best_model(
    prepared: _PreparedTrainingData,
    split_artifacts: _GroupedSplitArtifacts,
    config: TrainingConfig,
    model_results: Dict[str, Dict[str, Any]],
    candidate_results: Dict[str, Dict[str, Any]],
    best_candidate_model_name: str,
) -> Dict[str, Any]:
    best_model_name = best_candidate_model_name
    baseline_metrics = model_results.get("dummy_mean_baseline", {})
    baseline_validation_rmse = baseline_metrics.get("validation_rmse")
    candidate_validation_rmse = model_results[best_candidate_model_name].get("validation_rmse")
    baseline_gate_reason = "baseline_unavailable"
    baseline_min_gain_pct = round(float(config.baseline_min_relative_improvement) * 100.0, 4)
    best_candidate_beats_baseline = False
    if baseline_validation_rmse is not None and candidate_validation_rmse is not None:
        baseline_value = float(baseline_validation_rmse)
        candidate_value = float(candidate_validation_rmse)
        required_gain = baseline_value * float(config.baseline_min_relative_improvement)
        best_candidate_beats_baseline = candidate_value <= (baseline_value - required_gain)
        baseline_gate_reason = (
            "candidate_clears_baseline_margin"
            if best_candidate_beats_baseline
            else "candidate_does_not_clear_baseline_margin"
        )
        if not best_candidate_beats_baseline and "dummy_mean_baseline" in model_results:
            best_model_name = "dummy_mean_baseline"

    best_metrics = model_results[best_model_name]
    best_validation_rmse = best_metrics.get("validation_rmse")
    improvement_vs_baseline_pct = _improvement_pct(baseline_validation_rmse, best_validation_rmse)
    candidate_improvement_vs_baseline_pct = _improvement_pct(baseline_validation_rmse, candidate_validation_rmse)
    test_rmse_improvement_vs_baseline_pct = _improvement_pct(
        baseline_metrics.get("rmse"),
        best_metrics.get("rmse"),
    )
    generalization_gap = None
    if best_metrics.get("rmse") is not None and best_validation_rmse is not None:
        generalization_gap = round(abs(float(best_metrics["rmse"]) - float(best_validation_rmse)), 4)
    cv_stability_ratio = None
    if best_metrics.get("cv_rmse_mean") is not None and best_metrics.get("cv_rmse_std") is not None:
        cv_mean = float(best_metrics["cv_rmse_mean"])
        if cv_mean > 0:
            cv_stability_ratio = round(float(best_metrics["cv_rmse_std"]) / cv_mean, 4)

    train_group_set = set(split_artifacts.train_groups.tolist())
    test_group_set = set(split_artifacts.test_groups.tolist())
    fit_group_set = set(split_artifacts.fit_groups.tolist())
    validation_group_set = set(split_artifacts.validation_groups.tolist())
    train_test_overlap_count = len(train_group_set & test_group_set)
    fit_validation_overlap_count = len(fit_group_set & validation_group_set)

    credibility_checks: Dict[str, Any] = {
        "baseline_model": "dummy_mean_baseline",
        "baseline_validation_rmse": baseline_validation_rmse,
        "best_validation_rmse": best_validation_rmse,
        "validation_rmse_improvement_vs_baseline_pct": improvement_vs_baseline_pct,
        "test_rmse_improvement_vs_baseline_pct": test_rmse_improvement_vs_baseline_pct,
        "best_candidate_model": best_candidate_model_name,
        "best_candidate_validation_rmse": candidate_validation_rmse,
        "best_candidate_improvement_vs_baseline_pct": candidate_improvement_vs_baseline_pct,
        "best_candidate_beats_baseline": best_candidate_beats_baseline,
        "baseline_min_relative_improvement": config.baseline_min_relative_improvement,
        "baseline_min_gain_pct": baseline_min_gain_pct,
        "baseline_gate_reason": baseline_gate_reason,
        "generalization_gap_abs": generalization_gap,
        "cv_stability_ratio": cv_stability_ratio,
        "selection_metric": "validation_rmse",
        "split_protocol": prepared.base_meta["evaluation_protocol"],
        "group_column": prepared.group_column,
        "train_test_group_overlap_count": train_test_overlap_count,
        "fit_validation_group_overlap_count": fit_validation_overlap_count,
        "leakage_check_passed": train_test_overlap_count == 0 and fit_validation_overlap_count == 0,
        "unique_groups_total": prepared.unique_group_count,
        "train_groups": len(train_group_set),
        "test_groups": len(test_group_set),
        "fit_groups": len(fit_group_set),
        "validation_groups": len(validation_group_set),
    }
    if improvement_vs_baseline_pct is not None:
        credibility_checks["summary"] = (
            f"RMSE-selected model improves grouped-validation RMSE by {improvement_vs_baseline_pct}% vs baseline."
        )
    else:
        credibility_checks["summary"] = "Baseline comparison unavailable for this run."
    if best_model_name == "dummy_mean_baseline" and candidate_results:
        credibility_checks["summary"] = (
            "No candidate model cleared the configured baseline improvement margin; "
            "the dummy mean baseline is kept as the selected model for honesty."
        )

    feature_importance_table = _build_feature_importance_table(prepared.feature_names, [])
    top_feature_names = [row["feature"] for row in feature_importance_table[:3]]
    baseline_comparison: Dict[str, Any] = {
        "baseline_model": "dummy_mean_baseline",
        "selected_model": best_model_name,
        "best_candidate_model": best_candidate_model_name,
        "baseline_metrics": baseline_metrics,
        "selected_model_metrics": best_metrics,
        "best_candidate_metrics": model_results.get(best_candidate_model_name, {}),
        "validation_rmse_improvement_vs_baseline_pct": improvement_vs_baseline_pct,
        "test_rmse_improvement_vs_baseline_pct": test_rmse_improvement_vs_baseline_pct,
        "best_candidate_improvement_vs_baseline_pct": candidate_improvement_vs_baseline_pct,
        "best_candidate_beats_baseline": best_candidate_beats_baseline,
        "minimum_required_gain_pct": baseline_min_gain_pct,
    }
    if best_model_name == "dummy_mean_baseline" and candidate_results:
        selection_reason = (
            "The best non-baseline model did not improve grouped validation RMSE enough "
            "to clear the configured baseline margin."
        )
    elif best_model_name == best_candidate_model_name:
        selection_reason = (
            f"{best_model_name} had the lowest grouped validation RMSE among candidate models "
            "and cleared the baseline comparison gate."
        )
    else:
        selection_reason = f"{best_model_name} was selected by grouped validation RMSE."

    interpretation_summary: Dict[str, Any] = {
        "top_features": feature_importance_table[:5],
        "plain_language": (
            f"Top model signals: {', '.join(top_feature_names) if top_feature_names else 'N/A'}. "
            "Feature importances are computed by permutation on the grouped validation split, "
            "so they describe model sensitivity under the same leakage-controlled protocol."
        ),
        "caution": (
            "These explanations describe a model trained on a simulated proxy target. "
            "They support transparent ranking, not experimental causality."
        ),
    }
    return {
        "best_model_name": best_model_name,
        "baseline_comparison": baseline_comparison,
        "model_selection_report": {
            "selected_model": best_model_name,
            "best_candidate_model": best_candidate_model_name,
            "selection_metric": "validation_rmse",
            "selection_reason": selection_reason,
            "baseline_gate_reason": baseline_gate_reason,
            "models_considered": list(model_results.keys()),
            "candidate_models_considered": list(candidate_results.keys()),
            "baseline_comparison": baseline_comparison,
        },
        "interpretation_summary": interpretation_summary,
        "credibility_checks": credibility_checks,
        "train_test_group_overlap_count": train_test_overlap_count,
        "fit_validation_group_overlap_count": fit_validation_overlap_count,
    }


def _build_ablation_study(
    prepared: _PreparedTrainingData,
    split_artifacts: _GroupedSplitArtifacts,
) -> Dict[str, Any]:
    def _evaluate_ablation(numeric_features: List[str], categorical_features: List[str]) -> Dict[str, Any]:
        if not numeric_features and not categorical_features:
            return {
                "model": "ridge_surrogate",
                "skipped": True,
                "reason": "No available features for this block.",
            }
        ablation_model = _make_model_pipeline(
            Ridge(alpha=1.0),
            numeric_features,
            categorical_features,
            scale_numeric=True,
        )
        try:
            ablation_model.fit(split_artifacts.x_fit, split_artifacts.y_fit)
            val_pred = np.asarray(ablation_model.predict(split_artifacts.x_val), dtype=float)
            test_pred = np.asarray(ablation_model.predict(split_artifacts.x_test), dtype=float)
            return {
                "model": "ridge_surrogate",
                "features": list(numeric_features) + list(categorical_features),
                "validation_rmse": round(_rmse(split_artifacts.y_val, val_pred), 4),
                "validation_mae": round(float(mean_absolute_error(split_artifacts.y_val, val_pred)), 4),
                "validation_r2": round(float(r2_score(split_artifacts.y_val, val_pred)), 4),
                "rmse": round(_rmse(split_artifacts.y_test, test_pred), 4),
                "mae": round(float(mean_absolute_error(split_artifacts.y_test, test_pred)), 4),
                "r2": round(float(r2_score(split_artifacts.y_test, test_pred)), 4),
            }
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
            return {
                "model": "ridge_surrogate",
                "skipped": True,
                "reason": str(exc),
                "features": list(numeric_features) + list(categorical_features),
            }

    ablation_study: Dict[str, Any] = {}
    for block_name, block_features in FEATURE_BLOCKS.items():
        block_numeric = [name for name in block_features if name in prepared.numeric_features]
        block_categorical = [name for name in block_features if name in prepared.categorical_features]
        ablation_study[block_name] = _evaluate_ablation(block_numeric, block_categorical)
    ablation_study["dna_plus_host"] = _evaluate_ablation(
        [name for name in FEATURE_BLOCKS["dna_codon"] if name in prepared.numeric_features],
        [name for name in FEATURE_BLOCKS["host"] if name in prepared.categorical_features],
    )
    ablation_study["protein_plus_structure"] = _evaluate_ablation(
        [
            name
            for name in FEATURE_BLOCKS["protein_sequence"] + FEATURE_BLOCKS["structure"]
            if name in prepared.numeric_features
        ],
        [],
    )
    ablation_study["full_surrogate"] = _evaluate_ablation(
        prepared.numeric_features,
        prepared.categorical_features,
    )
    return ablation_study


def _numeric_series(df: pd.DataFrame, column_name: str) -> Optional[pd.Series]:
    if column_name not in df.columns:
        return None
    series = pd.to_numeric(df[column_name], errors="coerce")
    return series if series.notna().any() else None


def _resolve_target_series(df: pd.DataFrame, target_column: str) -> Optional[pd.Series]:
    return _numeric_series(df, target_column)


def _build_groups(
    df: pd.DataFrame,
    valid_mask: np.ndarray,
    index: pd.Index,
    group_column: Optional[str],
) -> Tuple[str, np.ndarray]:
    if group_column and group_column in df.columns:
        group_series = (
            df.loc[valid_mask, group_column]
            .astype("string")
            .fillna("")
            .astype(str)
            .str.strip()
        )
        row_group_fallback = pd.Series([f"row_{idx}" for idx in index], index=index, dtype="string")
        group_series = group_series.where(group_series != "", row_group_fallback)
        return group_column, group_series.to_numpy(dtype=str)
    fallback_series = pd.Series([f"row_{idx}" for idx in index], index=index, dtype="string")
    return "row_index_fallback", fallback_series.to_numpy(dtype=str)


def _correlation_exclusions(
    feature_frame: pd.DataFrame,
    selected_numeric_features: List[str],
    feature_pool: List[str],
) -> Dict[str, str]:
    correlation_exclusions: Dict[str, str] = {}
    if len(selected_numeric_features) <= 1:
        return correlation_exclusions
    corr = feature_frame[selected_numeric_features].corr().abs()
    for index, feature_a in enumerate(selected_numeric_features):
        for feature_b in selected_numeric_features[index + 1 :]:
            if feature_a in correlation_exclusions or feature_b in correlation_exclusions:
                continue
            corr_value = corr.loc[feature_a, feature_b]
            if pd.isna(corr_value) or float(corr_value) < 0.98:
                continue
            if _feature_rank(feature_a, feature_pool) <= _feature_rank(feature_b, feature_pool):
                keep_feature, drop_feature = feature_a, feature_b
            else:
                keep_feature, drop_feature = feature_b, feature_a
            correlation_exclusions[drop_feature] = f"highly_correlated_with:{keep_feature}"
    return correlation_exclusions


def _categorical_feature_diagnostics(
    df: pd.DataFrame,
    total_rows: int,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    categorical_features: List[str] = []
    diagnostics: List[Dict[str, Any]] = []
    for feature_name in CATEGORICAL_MODEL_FEATURES:
        if feature_name not in df.columns:
            diagnostics.append(
                {
                    "feature": feature_name,
                    "status": "excluded",
                    "reason": "missing_categorical_feature",
                    "unique_values": 0,
                    "missing_ratio": 1.0,
                }
            )
            continue
        clean_series = df[feature_name].astype("string")
        non_null_count = int(clean_series.notna().sum())
        missing_ratio = round(float(1.0 - (non_null_count / total_rows)), 6)
        unique_values = int(clean_series.dropna().nunique())
        if unique_values <= 1:
            diagnostics.append(
                {
                    "feature": feature_name,
                    "status": "excluded",
                    "reason": "constant_categorical_feature",
                    "unique_values": unique_values,
                    "missing_ratio": missing_ratio,
                }
            )
            continue
        categorical_features.append(feature_name)
        diagnostics.append(
            {
                "feature": feature_name,
                "status": "selected",
                "reason": "usable_categorical",
                "unique_values": unique_values,
                "missing_ratio": missing_ratio,
            }
        )
    return categorical_features, diagnostics


def _feature_rank(feature_name: str, feature_pool: List[str]) -> int:
    if feature_name in FEATURE_PRIORITY:
        return FEATURE_PRIORITY[feature_name]
    try:
        return 10_000 + feature_pool.index(feature_name)
    except ValueError:
        return 20_000


def _make_preprocessor(
    numeric_features: List[str],
    categorical_features: List[str],
    scale_numeric: bool,
) -> ColumnTransformer:
    transformers: List[Tuple[str, Any, List[str]]] = []
    if numeric_features:
        numeric_steps: List[Tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
        if scale_numeric:
            numeric_steps.append(("scaler", StandardScaler()))
        transformers.append(("numeric", Pipeline(numeric_steps), numeric_features))
    if categorical_features:
        categorical_pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", _one_hot_encoder()),
            ]
        )
        transformers.append(("categorical", categorical_pipeline, categorical_features))
    return ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        verbose_feature_names_out=False,
    )


def _make_model_pipeline(
    estimator: Any,
    numeric_features: List[str],
    categorical_features: List[str],
    scale_numeric: bool,
) -> Pipeline:
    return Pipeline(
        [
            ("preprocessor", _make_preprocessor(numeric_features, categorical_features, scale_numeric)),
            ("model", estimator),
        ]
    )


def _one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def _encoded_feature_names(model: Any, fallback_names: List[str]) -> List[str]:
    if not hasattr(model, "named_steps"):
        return list(fallback_names)
    preprocessor = model.named_steps.get("preprocessor")
    if preprocessor is None or not hasattr(preprocessor, "get_feature_names_out"):
        return list(fallback_names)
    try:
        return [str(name) for name in preprocessor.get_feature_names_out()]
    except (AttributeError, TypeError, ValueError):
        return list(fallback_names)


def _normalized_permutation_importance(
    model: Any,
    x_eval: pd.DataFrame,
    y_eval: np.ndarray,
    feature_names: List[str],
    random_state: int,
) -> Tuple[List[float], str]:
    if not feature_names:
        return [], "unavailable"
    try:
        importance = permutation_importance(
            model,
            x_eval,
            y_eval,
            n_repeats=8,
            random_state=random_state,
            scoring="neg_mean_squared_error",
            n_jobs=1,
        )
        raw_values = np.maximum(0.0, np.asarray(importance.importances_mean, dtype=float))
        if raw_values.size != len(feature_names):
            resized = np.zeros(len(feature_names), dtype=float)
            limit = min(len(feature_names), raw_values.size)
            resized[:limit] = raw_values[:limit]
            raw_values = resized
        total = float(raw_values.sum())
        if total <= 0:
            uniform = round(1.0 / len(feature_names), 6)
            return [uniform] * len(feature_names), "uniform_permutation_fallback"
        normalized = raw_values / total
        return [round(float(value), 6) for value in normalized.tolist()], "permutation_importance_validation"
    except ValueError:
        uniform = round(1.0 / len(feature_names), 6)
        return [uniform] * len(feature_names), "uniform_permutation_fallback"


def _tune_model(
    model_name: str,
    base_model: Any,
    split_artifacts: _GroupedSplitArtifacts,
    config: TrainingConfig,
    cv_group_count: int,
) -> Tuple[Any, Dict[str, Any]]:
    if not config.hyperparameter_search or cv_group_count < 3:
        return base_model, {}
    if model_name == "random_forest":
        search = RandomizedSearchCV(
            estimator=base_model,
            param_distributions={
                "model__n_estimators": [180, 250, 350, 450, 550],
                "model__max_depth": [None, 6, 10, 14, 20],
                "model__min_samples_leaf": [1, 2, 4],
            },
            n_iter=8,
            cv=GroupKFold(n_splits=min(3, cv_group_count)),
            scoring="neg_mean_squared_error",
            random_state=config.random_state,
            n_jobs=1,
        )
        return _run_randomized_search(search, base_model, split_artifacts)
    if model_name == "xgboost":
        search = RandomizedSearchCV(
            estimator=base_model,
            param_distributions={
                "model__learning_rate": [0.01, 0.03, 0.05, 0.08, 0.12],
                "model__max_depth": [3, 4, 5, 6, 8],
                "model__n_estimators": [120, 200, 300, 420, 560],
            },
            n_iter=8,
            cv=GroupKFold(n_splits=min(3, cv_group_count)),
            scoring="neg_mean_squared_error",
            random_state=config.random_state,
            n_jobs=1,
        )
        return _run_randomized_search(search, base_model, split_artifacts)
    return base_model, {}


def _run_randomized_search(
    search: RandomizedSearchCV,
    base_model: Any,
    split_artifacts: _GroupedSplitArtifacts,
) -> Tuple[Any, Dict[str, Any]]:
    try:
        search.fit(split_artifacts.x_fit, split_artifacts.y_fit, groups=split_artifacts.fit_groups)
        return search.best_estimator_, {
            key.replace("model__", ""): _json_safe_scalar(value)
            for key, value in search.best_params_.items()
        }
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return base_model, {}


def _build_target_dependency_diagnostics(
    x: pd.DataFrame,
    y: np.ndarray,
    numeric_features: List[str],
    target_column: str,
) -> Dict[str, Any]:
    target_summary = {
        "min": round(float(np.min(y)), 6),
        "median": round(float(np.median(y)), 6),
        "mean": round(float(np.mean(y)), 6),
        "max": round(float(np.max(y)), 6),
        "std": round(float(np.std(y)), 6),
        "unique_values": int(np.unique(y).size),
    }
    target_for_corr = pd.Series(y, index=x.index, dtype="float64")
    target_corr_rows: List[Dict[str, Any]] = []
    for feature_name in numeric_features:
        feature_series = pd.to_numeric(x[feature_name], errors="coerce")
        if feature_series.nunique(dropna=True) <= 1:
            continue
        corr_value = target_for_corr.corr(feature_series)
        if pd.isna(corr_value):
            continue
        target_corr_rows.append(
            {
                "feature": feature_name,
                "correlation": round(float(corr_value), 6),
                "abs_correlation": round(abs(float(corr_value)), 6),
            }
        )
    target_corr_rows = sorted(
        target_corr_rows,
        key=lambda row: float(row.get("abs_correlation", 0.0)),
        reverse=True,
    )
    high_target_corr_threshold = 0.95
    return {
        "target_version": PROXY_TARGET_VERSION,
        "synthetic_target": True,
        "target_column": target_column,
        "target_summary": target_summary,
        "top_abs_feature_correlations": target_corr_rows[:10],
        "high_correlation_warning_threshold": high_target_corr_threshold,
        "potential_target_leakage_features": [
            row["feature"]
            for row in target_corr_rows
            if float(row.get("abs_correlation", 0.0)) >= high_target_corr_threshold
        ],
        "target_derived_columns_excluded": list(TARGET_DERIVED_COLUMNS),
        "assumption_note": (
            "The target is intentionally simulated. Diagnostics flag direct target aliases "
            "and unusually high feature-target correlations, but normal biological-design "
            "features can still correlate with the proxy by construction."
        ),
    }


def _build_feature_importance_table(feature_names: List[str], importances: List[float]) -> List[Dict[str, Any]]:
    feature_block_lookup: Dict[str, str] = {}
    for block_name, block_features in FEATURE_BLOCKS.items():
        for feature_name in block_features:
            feature_block_lookup.setdefault(feature_name, block_name)
    return sorted(
        [
            {
                "feature": feature_name,
                "importance": importance,
                "role": "model_input",
                "block": feature_block_lookup.get(feature_name, "engineered"),
            }
            for feature_name, importance in zip(feature_names, importances)
        ],
        key=lambda row: float(row.get("importance", 0.0)),
        reverse=True,
    )


def _ml_pipeline_schema(target_column: str) -> Dict[str, Any]:
    return {
        "objective": f"Predict {target_column} as a simulated proxy/surrogate target",
        "feature_strategy": "Numeric quality filtering, high-correlation pruning, and host one-hot encoding",
        "selection_metric": "validation_rmse",
        "split_protocol": "protein_grouped_train_validation_test_split",
        "steps": [
            "Input dataset -> candidate feature pool from DNA/codon/protein/structure descriptors",
            "Numeric conversion and unsupervised feature quality checks",
            "Remove constant, near-zero-variance, and highly correlated numeric features",
            "Add plant_host as a categorical feature with one-hot encoding inside sklearn pipelines",
            "Split train/validation/test by protein accession to prevent protein-level leakage",
            "Impute numeric/categorical missing values inside the training pipeline",
            "Train baseline + multi-model regressors with grouped hyperparameter search",
            "Select a candidate model only when grouped validation RMSE clears the baseline gate",
            "Report grouped holdout test metrics, CV RMSE, residuals, and predicted-vs-actual vectors",
            "Export ablation study, permutation importance, and prediction diagnostics",
        ],
    }


def _skip_training_result(
    reason: str,
    prepared: Optional[_PreparedTrainingData] = None,
    base_meta: Optional[Dict[str, Any]] = None,
    feature_names: Optional[List[str]] = None,
    feature_selection: Optional[Dict[str, Any]] = None,
    **extra: Any,
) -> Dict[str, Any]:
    metadata = dict(prepared.base_meta if prepared is not None else (base_meta or {}))
    return {
        "training_enabled": True,
        "proxy_on_proxy": True,
        "skipped": True,
        "reason": reason,
        "feature_names": list(feature_names if feature_names is not None else (prepared.feature_names if prepared else [])),
        "feature_selection": feature_selection if feature_selection is not None else (
            prepared.feature_selection_payload if prepared is not None else {}
        ),
        **extra,
        **metadata,
    }


def _import_optional_module(module_name: str) -> Optional[Any]:
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def _float_list(values: Any) -> List[float]:
    array_values = np.asarray(values, dtype=float)
    return [round(float(value), 6) for value in array_values.tolist()]


def _improvement_pct(baseline_value: Any, improved_value: Any) -> Optional[float]:
    if baseline_value is None or improved_value is None:
        return None
    baseline_float = float(baseline_value)
    improved_float = float(improved_value)
    if baseline_float <= 0:
        return None
    return round(((baseline_float - improved_float) / baseline_float) * 100.0, 2)


def _json_safe_scalar(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_percent_value(value: Any) -> float:
    numeric = _to_float(value, default=0.0)
    return numeric * 100.0 if abs(numeric) <= 1.5 else numeric


def _to_ratio_value(value: Any) -> float:
    numeric = _to_float(value, default=0.0)
    if numeric > 1.5:
        numeric /= 100.0
    return max(0.0, min(1.0, numeric))


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    diff = y_true - y_pred
    return float(np.sqrt(np.mean(np.square(diff))))
