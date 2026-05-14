import json
import shutil
import unittest
from pathlib import Path

import joblib

from app.internal.artifacts import load_artifacts_from_manifest, load_model_payload


TEST_TMP_ROOT = Path("tests") / "_tmp"


class AppArtifactTests(unittest.TestCase):
    def test_load_artifacts_from_manifest_reads_relative_artifacts(self) -> None:
        root = TEST_TMP_ROOT / "app_artifacts"
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
        try:
            dataset_path = root / "dataset.csv"
            metadata_path = root / "metadata.json"
            quality_path = root / "quality.json"
            metrics_path = root / "metrics.json"
            manifest_path = root / "latest_run_manifest.json"

            dataset_path.write_text("protein_accession,cai\nP00001,0.71\n", encoding="utf-8")
            metadata_path.write_text(json.dumps({"keyword": "insulin"}), encoding="utf-8")
            quality_path.write_text(json.dumps({"rows_generated": 1}), encoding="utf-8")
            metrics_path.write_text(json.dumps({"best_model_name": "ridge"}), encoding="utf-8")
            manifest_path.write_text(
                json.dumps(
                    {
                        "latest_dataset_path": dataset_path.name,
                        "latest_metadata_path": metadata_path.name,
                        "latest_quality_report_path": quality_path.name,
                        "latest_metrics_path": metrics_path.name,
                    }
                ),
                encoding="utf-8",
            )

            payload = load_artifacts_from_manifest(manifest_path)
        finally:
            if root.exists():
                shutil.rmtree(root)

        self.assertEqual(payload["manifest_path"], manifest_path)
        self.assertEqual(payload["dataset"].shape, (1, 2))
        self.assertEqual(payload["metadata"]["keyword"], "insulin")
        self.assertEqual(payload["quality"]["rows_generated"], 1)
        self.assertEqual(payload["metrics"]["best_model_name"], "ridge")

    def test_load_model_payload_returns_saved_joblib_payload(self) -> None:
        root = TEST_TMP_ROOT / "model_payload"
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
        try:
            model_path = root / "model.joblib"
            joblib.dump({"model": "ridge", "feature_names": ["cai"]}, model_path)

            payload = load_model_payload(str(model_path))
        finally:
            if root.exists():
                shutil.rmtree(root)

        self.assertIsNone(payload["error"])
        self.assertEqual(payload["model"], "ridge")
        self.assertEqual(payload["payload"]["feature_names"], ["cai"])

    def test_load_model_payload_reports_missing_file(self) -> None:
        payload = load_model_payload("C:/definitely_missing/model.joblib")
        self.assertEqual(payload["error"], "Model file not found.")


if __name__ == "__main__":
    unittest.main()
