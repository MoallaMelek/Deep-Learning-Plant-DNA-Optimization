import unittest

from app.internal import metrics_dashboard


class MetricsDashboardTests(unittest.TestCase):
    def test_selected_model_diagnostics_use_prediction_vectors(self) -> None:
        selected_metrics = {
            "test_actual_values": [0.1, 0.2],
            "test_predicted_values": [0.11, 0.21],
        }
        fallback_metrics = {"test_actual_values": [0.9], "test_predicted_values": [0.95]}

        resolved = metrics_dashboard._metrics_with_prediction_vectors(selected_metrics, fallback_metrics)

        self.assertIs(resolved, selected_metrics)

    def test_selected_model_diagnostics_fallback_when_missing_vectors(self) -> None:
        selected_metrics = {"test_actual_values": []}
        fallback_metrics = {"test_actual_values": [0.9], "test_predicted_values": [0.95]}

        resolved = metrics_dashboard._metrics_with_prediction_vectors(selected_metrics, fallback_metrics)

        self.assertIs(resolved, fallback_metrics)

    def test_unavailable_model_fallback_prefers_recommended(self) -> None:
        available_models = ["ridge", "linear_regression"]

        resolved = metrics_dashboard._resolve_active_model_for_diagnostics(
            available_models,
            requested_model="xgboost",
            recommended_model="ridge",
            fallback_model="linear_regression",
        )

        self.assertEqual(resolved, "ridge")

    def test_unavailable_model_fallback_uses_fallback_model(self) -> None:
        available_models = ["ridge", "linear_regression"]

        resolved = metrics_dashboard._resolve_active_model_for_diagnostics(
            available_models,
            requested_model="xgboost",
            recommended_model="lightgbm",
            fallback_model="linear_regression",
        )

        self.assertEqual(resolved, "linear_regression")


if __name__ == "__main__":
    unittest.main()
