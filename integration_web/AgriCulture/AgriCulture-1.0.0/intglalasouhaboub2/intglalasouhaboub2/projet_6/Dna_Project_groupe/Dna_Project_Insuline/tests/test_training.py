import importlib
import unittest
from unittest import mock

from dataset_builder.config import TrainingConfig
from dataset_builder.dataset_builder import _train_model_grouped_impl
from dataset_builder.schema import PROXY_TARGET_COLUMN, TARGET_DERIVED_COLUMNS


HOSTS = [
    "Arabidopsis thaliana",
    "Oryza sativa",
    "Zea mays",
    "Phoenix dactylifera",
]


def _training_rows(group_count: int = 8):
    rows = []
    for group_idx in range(group_count):
        for host_idx, host in enumerate(HOSTS):
            cai = 0.45 + group_idx * 0.035 + host_idx * 0.01
            gc_content = 0.38 + group_idx * 0.015 + host_idx * 0.02
            rare_ratio = 0.08 + (3 - host_idx) * 0.01
            target = min(0.98, 0.25 + cai * 0.45 + gc_content * 0.2 - rare_ratio * 0.15)
            rows.append(
                {
                    "protein_accession": f"P{group_idx:05d}",
                    "accession": f"P{group_idx:05d}",
                    "plant_host": host,
                    "cai": round(cai, 4),
                    "gc_content": round(gc_content, 4),
                    "gc_skew": round(-0.1 + host_idx * 0.05, 4),
                    "gc3_content": round(gc_content + 0.03, 4),
                    "at_content": round(1.0 - gc_content, 4),
                    "purine_content": round(0.48 + group_idx * 0.005, 4),
                    "sequence_length_nt": 300 + group_idx * 9,
                    "codon_count": 100 + group_idx * 3,
                    "unique_codons": 20 + host_idx,
                    "codon_entropy": round(3.1 + group_idx * 0.03, 4),
                    "effective_codon_fraction": round(0.2 + host_idx * 0.02, 4),
                    "stop_codon_count": 0,
                    "invalid_codon_count": 0,
                    "repetitive_codon_ratio": round(0.02 + host_idx * 0.005, 4),
                    "rare_codon_ratio": round(rare_ratio, 4),
                    "protein_aa_entropy": round(0.72 + group_idx * 0.01, 4),
                    "protein_mean_hydrophobicity": round(-0.2 + host_idx * 0.03, 4),
                    "protein_length_penalty": round(0.1 + group_idx * 0.01, 4),
                    "helix_ratio": round(0.3 + host_idx * 0.01, 4),
                    "sheet_ratio": round(0.25 + group_idx * 0.005, 4),
                    "coil_ratio": 0.45,
                    "hydrophobicity_score": round(-0.4 + group_idx * 0.02, 4),
                    "stability_score": round(0.5 + host_idx * 0.03, 4),
                    "protein_length": 100 + group_idx * 3,
                    "structure_confidence": 80 + host_idx,
                    PROXY_TARGET_COLUMN: round(target, 4),
                    "target_expression_score": round(target, 4),
                }
            )
    return rows


class TrainingTests(unittest.TestCase):
    def test_grouped_training_reports_no_group_leakage(self) -> None:
        metrics, payloads = _train_model_grouped_impl(
            _training_rows(),
            TrainingConfig(
                save_model=False,
                enabled_models=["dummy_mean_baseline", "ridge", "linear_regression"],
                hyperparameter_search=False,
            ),
        )

        self.assertFalse(metrics.get("skipped"), metrics.get("reason"))
        self.assertEqual(
            metrics["evaluation_protocol"],
            "protein_grouped_train_validation_test_split",
        )
        self.assertEqual(metrics["train_test_group_overlap_count"], 0)
        self.assertEqual(metrics["fit_validation_group_overlap_count"], 0)
        self.assertTrue(metrics["credibility_checks"]["leakage_check_passed"])
        self.assertEqual(set(metrics["models_trained"]), {"dummy_mean_baseline", "ridge", "linear_regression"})
        self.assertIn(metrics["best_model_name"], payloads)
        self.assertEqual(payloads[metrics["best_model_name"]]["feature_names"], metrics["feature_names"])
        self.assertIn("model_lab", metrics)
        self.assertIn("priority_recommendations", metrics)
        for model_name in ("ridge", "linear_regression"):
            model_metrics = metrics["model_comparison"][model_name]
            self.assertIn("training_time_seconds", model_metrics)
            self.assertIn("prediction_time_seconds", model_metrics)
            self.assertIn("accuracy_score", model_metrics)
            self.assertIn("speed_score", model_metrics)
            self.assertIn("overall_scores", model_metrics)
            self.assertGreaterEqual(model_metrics["training_time_seconds"], 0.0)
            self.assertGreaterEqual(model_metrics["prediction_time_seconds"], 0.0)

    def test_feature_selection_excludes_constant_and_target_derived_columns(self) -> None:
        metrics, _ = _train_model_grouped_impl(
            _training_rows(),
            TrainingConfig(
                save_model=False,
                enabled_models=["dummy_mean_baseline", "ridge"],
                hyperparameter_search=False,
            ),
        )

        self.assertFalse(metrics.get("skipped"), metrics.get("reason"))
        selected_features = set(metrics["feature_selection"]["selected_features"])
        self.assertNotIn("coil_ratio", selected_features)
        for target_column in TARGET_DERIVED_COLUMNS:
            self.assertNotIn(target_column, selected_features)

        excluded = {
            row["feature"]: row["reason"]
            for row in metrics["feature_selection"]["excluded_features"]
        }
        self.assertEqual(excluded["coil_ratio"], "constant_feature")
        self.assertIn("plant_host", selected_features)

    def test_can_train_only_selected_model_with_grouped_protocol(self) -> None:
        metrics, payloads = _train_model_grouped_impl(
            _training_rows(),
            TrainingConfig(
                save_model=False,
                enabled_models=["dummy_mean_baseline", "ridge"],
                hyperparameter_search=False,
            ),
        )

        self.assertFalse(metrics.get("skipped"), metrics.get("reason"))
        self.assertEqual(set(metrics["models_trained"]), {"dummy_mean_baseline", "ridge"})
        self.assertEqual(metrics["train_test_group_overlap_count"], 0)
        self.assertEqual(metrics["fit_validation_group_overlap_count"], 0)
        self.assertTrue(metrics["credibility_checks"]["leakage_check_passed"])
        self.assertIn("ridge", metrics["model_comparison"])
        self.assertIn("ridge", payloads)
        self.assertNotIn("random_forest", metrics["model_comparison"])

    def test_missing_lightgbm_dependency_is_reported_cleanly(self) -> None:
        real_import_module = importlib.import_module

        def _patched_import(name: str, package=None):
            if name == "lightgbm":
                raise ImportError("simulated missing lightgbm")
            return real_import_module(name, package)

        with mock.patch("dataset_builder.grouped_training.importlib.import_module", side_effect=_patched_import):
            metrics, payloads = _train_model_grouped_impl(
                _training_rows(),
                TrainingConfig(
                    save_model=False,
                    enabled_models=["lightgbm"],
                    hyperparameter_search=False,
                ),
            )

        self.assertTrue(metrics["skipped"])
        self.assertEqual(metrics["reason"], "No model could be trained successfully.")
        self.assertFalse(payloads)
        self.assertIn("lightgbm: not_available_or_not_configured", metrics["unavailable_models"])


if __name__ == "__main__":
    unittest.main()
