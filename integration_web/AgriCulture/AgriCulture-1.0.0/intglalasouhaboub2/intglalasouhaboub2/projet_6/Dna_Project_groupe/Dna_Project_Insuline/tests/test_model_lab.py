import unittest

from dataset_builder.model_lab import (
    annotate_model_comparison,
    build_model_lab_payload,
    list_supported_models,
    recommendation_for_priority,
)


def _comparison_metrics():
    return {
        "linear_regression": {
            "mae": 0.13,
            "rmse": 0.17,
            "r2": 0.79,
            "validation_mae": 0.12,
            "validation_rmse": 0.16,
            "validation_r2": 0.8,
            "training_time_seconds": 0.01,
            "prediction_time_seconds": 0.001,
        },
        "ridge": {
            "mae": 0.12,
            "rmse": 0.165,
            "r2": 0.81,
            "validation_mae": 0.115,
            "validation_rmse": 0.155,
            "validation_r2": 0.82,
            "training_time_seconds": 0.015,
            "prediction_time_seconds": 0.0012,
        },
        "random_forest": {
            "mae": 0.11,
            "rmse": 0.15,
            "r2": 0.84,
            "validation_mae": 0.105,
            "validation_rmse": 0.145,
            "validation_r2": 0.85,
            "training_time_seconds": 0.12,
            "prediction_time_seconds": 0.004,
        },
        "xgboost": {
            "mae": 0.09,
            "rmse": 0.125,
            "r2": 0.89,
            "validation_mae": 0.085,
            "validation_rmse": 0.12,
            "validation_r2": 0.9,
            "training_time_seconds": 0.08,
            "prediction_time_seconds": 0.003,
        },
        "lightgbm": {
            "mae": 0.095,
            "rmse": 0.13,
            "r2": 0.88,
            "validation_mae": 0.09,
            "validation_rmse": 0.125,
            "validation_r2": 0.89,
            "training_time_seconds": 0.03,
            "prediction_time_seconds": 0.0015,
        },
    }


class ModelLabTests(unittest.TestCase):
    def test_model_registry_contains_expected_supported_models(self) -> None:
        self.assertEqual(
            list_supported_models(),
            ["linear_regression", "ridge", "random_forest", "xgboost", "lightgbm"],
        )

    def test_priority_based_recommendation_changes_with_objective(self) -> None:
        payload = build_model_lab_payload(_comparison_metrics())

        self.assertEqual(recommendation_for_priority(payload, "accuracy")["model"], "xgboost")
        self.assertEqual(recommendation_for_priority(payload, "speed")["model"], "linear_regression")
        self.assertIn(
            recommendation_for_priority(payload, "interpretability")["model"],
            {"linear_regression", "ridge"},
        )
        self.assertIn(
            recommendation_for_priority(payload, "balanced")["model"],
            {"linear_regression", "ridge", "lightgbm", "xgboost", "random_forest"},
        )

    def test_missing_optional_model_dependency_does_not_break_payload(self) -> None:
        payload = build_model_lab_payload(
            {
                "linear_regression": _comparison_metrics()["linear_regression"],
                "ridge": _comparison_metrics()["ridge"],
            },
            unavailable_models=[
                "xgboost: not_available_or_not_configured",
                "lightgbm: not_available_or_not_configured",
            ],
        )

        supported = {row["model"]: row for row in payload["supported_models"]}
        self.assertFalse(supported["xgboost"]["available"])
        self.assertFalse(supported["lightgbm"]["available"])
        self.assertEqual(recommendation_for_priority(payload, "accuracy")["model"], "ridge")

    def test_annotated_scores_match_comparison_rows(self) -> None:
        annotated, payload = annotate_model_comparison(_comparison_metrics())
        rows_by_model = {row["model"]: row for row in payload["comparison_rows"]}

        for model_name in ("linear_regression", "ridge", "random_forest", "xgboost", "lightgbm"):
            self.assertEqual(annotated[model_name]["accuracy_score"], rows_by_model[model_name]["accuracy_score"])
            self.assertEqual(annotated[model_name]["speed_score"], rows_by_model[model_name]["speed_score"])
            self.assertEqual(annotated[model_name]["overall_scores"], rows_by_model[model_name]["overall_scores"])
            self.assertEqual(annotated[model_name]["interpretability_rating"], rows_by_model[model_name]["interpretability_rating"])

    def test_payload_explains_scoring_and_priority_weights(self) -> None:
        payload = build_model_lab_payload(_comparison_metrics())

        self.assertIn("scoring_method", payload)
        self.assertIn("priority_weights", payload)
        self.assertIn("speed_warning", payload)
        self.assertIn("scoring_note", payload)
        self.assertIn("accuracy_score", payload["scoring_method"])
        self.assertIn("speed_score", payload["scoring_method"])
        self.assertIn("interpretability_score", payload["scoring_method"])
        self.assertIn("overall_score", payload["scoring_method"])
        self.assertEqual(set(payload["priority_weights"]), {"accuracy", "speed", "interpretability", "balanced"})


if __name__ == "__main__":
    unittest.main()
