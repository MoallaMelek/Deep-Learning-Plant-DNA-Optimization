import json
import shutil
import unittest
from pathlib import Path

from dataset_builder import DatasetBuilder, PipelineConfig, TrainingConfig
from dataset_builder.uniprot_fetcher import ProteinRecord


TEST_TMP_ROOT = Path("tests") / "_tmp"


class StubFetcher:
    def __init__(self, records):
        self.records = records

    def fetch(self, keyword: str, limit: int):
        return self.records[:limit]


class DatasetBuilderTests(unittest.TestCase):
    def test_build_writes_compatible_artifacts_without_training(self) -> None:
        records = [
            ProteinRecord("P00001", "Example protein", "Synthetic organism", "MKT"),
            ProteinRecord("P00001", "Duplicate protein", "Synthetic organism", "MKT"),
            ProteinRecord("P00002", "Invalid protein", "Synthetic organism", "MZ"),
        ]

        output_dir = TEST_TMP_ROOT / "dataset_builder_unit"
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            builder = DatasetBuilder(
                pipeline_config=PipelineConfig(
                    output_dir=str(output_dir),
                    alphafold_enabled=False,
                    plant_hosts=["Arabidopsis thaliana", "Oryza sativa"],
                ),
                training_config=TrainingConfig(enabled=False),
            )
            builder.fetcher = StubFetcher(records)

            result = builder.build(keyword="insulin test", protein_limit=3)

            dataset_path = Path(result["csv"])
            quality_path = Path(result["quality"])
            metrics_path = output_dir / "metrics_insulin_test.json"
            manifest_path = Path(result["manifest"])

            self.assertTrue(dataset_path.exists())
            self.assertTrue(quality_path.exists())
            self.assertTrue(metrics_path.exists())
            self.assertTrue(manifest_path.exists())

            quality = json.loads(quality_path.read_text(encoding="utf-8"))
            self.assertEqual(quality["duplicates_filtered"], 1)
            self.assertEqual(quality["invalid_protein_sequence_count"], 1)
            self.assertEqual(quality["rows_generated"], 2)
            self.assertEqual(quality["rows_per_plant_host"]["Arabidopsis thaliana"], 1)
            self.assertEqual(quality["rows_per_plant_host"]["Oryza sativa"], 1)

            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            self.assertFalse(metrics["training_enabled"])
            self.assertEqual(metrics["target_column"], "simulated_proxy_expression_score")

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["latest_dataset_path"], str(dataset_path))
            self.assertEqual(manifest["rows_generated"], 2)
        finally:
            if output_dir.exists():
                shutil.rmtree(output_dir)

    def test_build_rejects_non_positive_protein_limit(self) -> None:
        builder = DatasetBuilder(training_config=TrainingConfig(enabled=False))
        with self.assertRaises(ValueError):
            builder.build(keyword="insulin", protein_limit=0)


if __name__ == "__main__":
    unittest.main()
