"""Dataset builder orchestrating fetch, optimization, and feature extraction."""

import random
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .config import PipelineConfig, UniprotConfig, TrainingConfig
from .dna_generator import DnaGenerator
from .feature_engineering import FeatureEngineer
from .grouped_training import train_model_grouped_impl as _train_model_grouped_impl_internal
from .protein_structure import ProteinStructureAnnotator, StructureAnnotation, mean_hydrophobicity_kd
from .schema import (
    CATEGORICAL_MODEL_FEATURES,
    DATASET_FIELDNAMES,
    DESCRIPTIVE_ONLY_COLUMNS,
    GROUP_COLUMN,
    HOST_EXPRESSION_PRIORS,
    HOST_GC_OPTIMA,
    LEGACY_TARGET_COLUMN,
    PROXY_TARGET_COLUMN,
    PROXY_TARGET_VERSION,
    TARGET_DERIVED_COLUMNS,
    UNIFIED_MODEL_FEATURES,
)
from .uniprot_fetcher import ProteinRecord, UniprotFetcher
from .utils import ensure_dir, sanitize_filename, save_csv, save_json, setup_logger, utc_timestamp
from .validation import is_valid_protein_sequence, validate_dna_sequence
from src.codon_analysis import naive_translation


class DatasetBuilder:
    def __init__(
        self,
        pipeline_config: Optional[PipelineConfig] = None,
        uniprot_config: Optional[UniprotConfig] = None,
        training_config: Optional[TrainingConfig] = None,
    ) -> None:
        self.pipeline_config = pipeline_config or PipelineConfig()
        self.uniprot_config = uniprot_config or UniprotConfig()
        self.training_config = training_config or TrainingConfig()
        self.fetcher = UniprotFetcher(self.uniprot_config)
        self.dna_generator = DnaGenerator(
            random_seed=self.pipeline_config.random_seed,
            min_relative_frequency=self.pipeline_config.codon_min_relative_frequency,
            frequency_exponent=self.pipeline_config.codon_frequency_exponent,
            exploration_rate=self.pipeline_config.codon_exploration_rate,
        )
        self.feature_engineer = FeatureEngineer(self.pipeline_config.rare_codon_threshold)
        self.structure_annotator = ProteinStructureAnnotator(
            use_alphafold=self.pipeline_config.alphafold_enabled,
            timeout_sec=self.pipeline_config.structure_timeout_sec,
            max_retries=self.pipeline_config.structure_max_retries,
            user_agent=self.uniprot_config.user_agent,
        )
        self.logger = setup_logger(self.__class__.__name__)

    def build(self, keyword: str, protein_limit: int) -> Dict[str, Any]:
        """
        Build a proxy-expression dataset from UniProt proteins.

        The target simulates expression-like behavior by combining DNA/codon,
        protein, structural, and host-specific effects. It is deterministic and
        reproducible, but not a wet-lab biological measurement.
        """
        keyword = (keyword or self.pipeline_config.default_keyword).strip()
        if not keyword:
            keyword = self.pipeline_config.default_keyword

        try:
            protein_limit = int(protein_limit)
        except (TypeError, ValueError) as exc:
            raise ValueError("protein_limit must be an integer") from exc
        if protein_limit <= 0:
            raise ValueError("protein_limit must be greater than zero")
        if not self.pipeline_config.plant_hosts:
            raise ValueError("At least one plant host must be configured")

        random.seed(self.pipeline_config.random_seed)
        np.random.seed(self.pipeline_config.random_seed)
        self.logger.info("Using random seed=%s", self.pipeline_config.random_seed)

        proteins = self.fetcher.fetch(keyword, protein_limit)
        dataset: List[Dict[str, Any]] = []
        data_quality: Dict[str, Any] = {
            "fetched_proteins": len(proteins),
            "duplicates_filtered": 0,
            "empty_sequence_filtered": 0,
            "invalid_protein_sequence_count": 0,
            "rejected_before_dna_generation": 0,
            "invalid_sequence_filtered": 0,
            "internal_stop_filtered": 0,
            "invalid_nucleotides_filtered": 0,
            "invalid_length_filtered": 0,
            "rows_generated": 0,
            "proteins_skipped_total": 0,
            "valid_proteins_after_protein_qc": 0,
            "valid_proteins_with_output_rows": 0,
            "valid_proteins_with_zero_output_rows": 0,
            "proteins_with_no_valid_dna_rows": 0,
            "structures_retrieved_from_alphafold": 0,
            "structures_using_mock_fallback": 0,
            "structure_retrieval_rate": 0.0,
        }
        rows_per_plant = {host: 0 for host in self.pipeline_config.plant_hosts}

        seen_accessions = set()
        valid_proteins_after_protein_qc = 0
        valid_proteins_with_output_rows = 0

        for protein in proteins:
            if protein.accession in seen_accessions:
                data_quality["duplicates_filtered"] += 1
                data_quality["rejected_before_dna_generation"] += 1
                continue
            seen_accessions.add(protein.accession)

            if not protein.sequence:
                data_quality["empty_sequence_filtered"] += 1
                data_quality["rejected_before_dna_generation"] += 1
                continue

            protein_valid = self._is_valid_protein_sequence(protein.sequence)
            if not protein_valid:
                data_quality["invalid_protein_sequence_count"] += 1
                data_quality["rejected_before_dna_generation"] += 1
                continue

            valid_proteins_after_protein_qc += 1
            rows, qc_stats = self._build_rows(protein, protein_valid=protein_valid)
            for key, value in qc_stats.items():
                data_quality[key] += value
            if not rows:
                data_quality["valid_proteins_with_zero_output_rows"] += 1
                data_quality["proteins_with_no_valid_dna_rows"] += 1
                continue

            valid_proteins_with_output_rows += 1

            dataset.extend(rows)
            for row in rows:
                rows_per_plant[row["plant_host"]] += 1

        data_quality["rows_generated"] = len(dataset)
        data_quality["proteins_skipped_total"] = (
            data_quality["duplicates_filtered"]
            + data_quality["empty_sequence_filtered"]
            + data_quality["invalid_protein_sequence_count"]
        )
        # Backward-compatible alias: same value as valid_proteins_with_output_rows.
        data_quality["valid_proteins_retained"] = valid_proteins_with_output_rows
        data_quality["valid_proteins_after_protein_qc"] = valid_proteins_after_protein_qc
        data_quality["valid_proteins_with_output_rows"] = valid_proteins_with_output_rows
        data_quality["rejected_proteins_total"] = (
            data_quality["rejected_before_dna_generation"]
            + data_quality["valid_proteins_with_zero_output_rows"]
        )
        fetched_total = max(1, data_quality["fetched_proteins"])
        data_quality["rejection_rate"] = round(data_quality["rejected_proteins_total"] / fetched_total, 4)
        data_quality["average_rows_per_valid_protein"] = (
            round(len(dataset) / valid_proteins_with_output_rows, 4)
            if valid_proteins_with_output_rows > 0
            else 0.0
        )
        structures_total = (
            data_quality["structures_retrieved_from_alphafold"]
            + data_quality["structures_using_mock_fallback"]
        )
        data_quality["structure_retrieval_rate"] = (
            round(data_quality["structures_retrieved_from_alphafold"] / structures_total, 4)
            if structures_total > 0
            else 0.0
        )
        data_quality["rows_per_plant_host"] = rows_per_plant
        data_quality["summary"] = {
            "protein_filtering": {
                "fetched": data_quality["fetched_proteins"],
                "rejected_before_dna_generation": data_quality["rejected_before_dna_generation"],
                "valid_after_protein_qc": data_quality["valid_proteins_after_protein_qc"],
                "valid_with_output_rows": data_quality["valid_proteins_with_output_rows"],
                "valid_with_zero_output_rows": data_quality["valid_proteins_with_zero_output_rows"],
                "valid_proteins_retained_alias_of_valid_with_output_rows": True,
            },
            "dna_qc": {
                "invalid_sequence_filtered_note": "DNA-level empty/invalid sequence counter",
                "invalid_sequence_filtered": data_quality["invalid_sequence_filtered"],
                "internal_stop_filtered": data_quality["internal_stop_filtered"],
                "invalid_nucleotides_filtered": data_quality["invalid_nucleotides_filtered"],
                "invalid_length_filtered": data_quality["invalid_length_filtered"],
            },
            "output_summary": {
                "rows_generated": data_quality["rows_generated"],
                "average_rows_per_valid_protein": data_quality["average_rows_per_valid_protein"],
                "rejected_proteins_total": data_quality["rejected_proteins_total"],
                "rejection_rate": data_quality["rejection_rate"],
            },
            "structure_retrieval": {
                "structures_retrieved_from_alphafold": data_quality["structures_retrieved_from_alphafold"],
                "structures_using_mock_fallback": data_quality["structures_using_mock_fallback"],
                "structure_retrieval_rate": data_quality["structure_retrieval_rate"],
                "note": "Rate is computed at protein level before host expansion.",
            },
        }

        for host, count in rows_per_plant.items():
            self.logger.info("Rows generated for %s: %s", host, count)
        self.logger.info("Proteins skipped: %s", data_quality["proteins_skipped_total"])

        ensure_dir(self.pipeline_config.output_dir)
        output_dir = Path(self.pipeline_config.output_dir)
        safe_keyword = sanitize_filename(keyword)
        csv_path = str(output_dir / f"dataset_{safe_keyword}.csv")
        json_path = str(output_dir / f"dataset_{safe_keyword}.json")
        metadata_path = str(output_dir / f"metadata_{safe_keyword}.json")
        metrics_path = str(output_dir / f"metrics_{safe_keyword}.json")
        quality_path = str(output_dir / f"data_quality_report_{safe_keyword}.json")
        manifest_path = str(output_dir / "latest_run_manifest.json")

        save_csv(csv_path, dataset, DATASET_FIELDNAMES)
        save_json(json_path, dataset)
        self.logger.info("Saved dataset to %s and %s", csv_path, json_path)

        metadata = {
            "timestamp": utc_timestamp(),
            "keyword": keyword,
            "protein_limit": protein_limit,
            "proteins_fetched": len(proteins),
            "unique_accessions": len(seen_accessions),
            "rows_generated": len(dataset),
            "plant_hosts": list(self.pipeline_config.plant_hosts),
            "random_seed": self.pipeline_config.random_seed,
            "codon_optimization": {
                "strategy": "host_biased_soft_weighted_sampling",
                "min_relative_frequency": self.pipeline_config.codon_min_relative_frequency,
                "frequency_exponent": self.pipeline_config.codon_frequency_exponent,
                "exploration_rate": self.pipeline_config.codon_exploration_rate,
                "seed_derivation": "sha256(random_seed|plant_host|protein_sequence)",
                "anti_perfect_cai_note": (
                    "Optimization samples codons from a preferred pool with a small deterministic "
                    "exploration probability, so optimized CAI should improve over naive translation "
                    "without being forced to 1.0."
                ),
            },
            "rare_codon_threshold": self.pipeline_config.rare_codon_threshold,
            "proxy_weights": {
                "protein_aa_entropy": self.pipeline_config.proxy_weight_aa_entropy,
                "protein_mean_hydrophobicity": self.pipeline_config.proxy_weight_hydrophobicity,
                "protein_length_penalty": self.pipeline_config.proxy_weight_length_penalty,
            },
            "structure_enrichment": {
                "alphafold_enabled": self.pipeline_config.alphafold_enabled,
                "secondary_structure_method": "windowed Chou-Fasman heuristic",
                "hydrophobicity_method": "Kyte-Doolittle mean",
                "stability_method": "amino-acid composition proxy",
            },
            "host_expression_priors_used": dict(HOST_EXPRESSION_PRIORS),
            "host_gc_optima_used": dict(HOST_GC_OPTIMA),
            "host_simulation_assumption_note": (
                "Host priors and GC optima are predefined simulation assumptions used to create "
                "a realistic proxy-learning task; they are not experimental biological measurements."
            ),
            "proxy_target": {
                "version": PROXY_TARGET_VERSION,
                "target_column": PROXY_TARGET_COLUMN,
                "legacy_alias": LEGACY_TARGET_COLUMN,
                "assumption": (
                    "The target is a deterministic simulated surrogate for relative expression. "
                    "It blends codon adaptation, host GC compatibility, protein/structure context, "
                    "latent protein signatures, and deterministic biological variability."
                ),
                "leakage_policy": (
                    "Target aliases, naive proxy scores, and delta proxy columns are excluded from "
                    "model training. Direct design descriptors remain eligible because the objective "
                    "is to learn a transparent proxy, not infer hidden experimental expression."
                ),
            },
            "training_enabled": self.training_config.enabled,
            "model_input_columns": list(UNIFIED_MODEL_FEATURES),
            "categorical_model_columns": list(CATEGORICAL_MODEL_FEATURES),
            "target_derived_columns": list(TARGET_DERIVED_COLUMNS),
            "descriptive_only_columns": list(DESCRIPTIVE_ONLY_COLUMNS),
            "model_group_column": GROUP_COLUMN,
            "model_target_column": PROXY_TARGET_COLUMN,
            "legacy_target_alias": LEGACY_TARGET_COLUMN,
            "non_model_columns": list(dict.fromkeys(DESCRIPTIVE_ONLY_COLUMNS + TARGET_DERIVED_COLUMNS)),
            "proxy_note": "This is a simulated proxy model combining DNA, codon, protein, and structural descriptors; not experimental biology.",
            "ml_method_note": (
                "Model evaluation uses protein-grouped splits so the same accession is not shared "
                "between train, validation, and test sets."
            ),
        }
        save_json(metadata_path, metadata)

        metrics: Dict[str, Any] = {}
        latest_model_path = None
        latest_model_lab_path = None
        latest_model_comparison_csv_path = None
        if self.training_config.enabled and dataset:
            metrics = self._train_model(dataset, metrics_path, safe_keyword)
            latest_model_path = metrics.get("model_path")
            latest_model_lab_path = metrics.get("model_lab_path")
            latest_model_comparison_csv_path = metrics.get("model_comparison_csv_path")
        else:
            save_json(
                metrics_path,
                {
                    "training_enabled": False,
                    "feature_names": list(UNIFIED_MODEL_FEATURES),
                    "target_column": PROXY_TARGET_COLUMN,
                    "group_column": GROUP_COLUMN,
                    "note": "Training disabled. This is a proxy model combining sequence and structural descriptors.",
                },
            )

        save_json(quality_path, data_quality)

        manifest = {
            "latest_dataset_path": csv_path,
            "latest_json_path": json_path,
            "latest_metadata_path": metadata_path,
            "latest_metrics_path": metrics_path,
            "latest_quality_report_path": quality_path,
            "latest_model_path": latest_model_path,
            "latest_model_lab_path": latest_model_lab_path,
            "latest_model_comparison_csv_path": latest_model_comparison_csv_path,
            "rows_generated": len(dataset),
            "training_enabled": self.training_config.enabled,
            "run_timestamp": metadata["timestamp"],
            "keyword": keyword,
        }
        save_json(manifest_path, manifest)

        return {
            "rows": len(dataset),
            "csv": csv_path,
            "json": json_path,
            "metadata": metadata_path,
            "metrics": metrics,
            "quality": quality_path,
            "manifest": manifest_path,
        }

    def _build_rows(
        self, protein: ProteinRecord, protein_valid: bool
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        rows: List[Dict[str, Any]] = []
        qc_stats = {
            "invalid_sequence_filtered": 0,
            "internal_stop_filtered": 0,
            "invalid_nucleotides_filtered": 0,
            "invalid_length_filtered": 0,
            "proteins_with_no_valid_dna_rows": 0,
            "structures_retrieved_from_alphafold": 0,
            "structures_using_mock_fallback": 0,
        }

        structure_annotation = self.structure_annotator.annotate(
            protein.accession,
            protein.sequence,
        )
        if structure_annotation.structure_source == "alphafold":
            qc_stats["structures_retrieved_from_alphafold"] += 1
        else:
            qc_stats["structures_using_mock_fallback"] += 1

        proxy_components = self._proxy_components(protein.sequence, structure_annotation)
        naive_dna_sequence = naive_translation(protein.sequence)

        for plant_host in self.pipeline_config.plant_hosts:
            result = self.dna_generator.generate(protein.sequence, plant_host)
            qc_issue = self._validate_dna(result.dna_sequence)
            dna_valid = qc_issue is None
            if qc_issue:
                qc_stats[qc_issue] += 1
                continue

            features = self.feature_engineer.compute_features(result.dna_sequence, plant_host)
            naive_features = self.feature_engineer.compute_features(naive_dna_sequence, plant_host)

            naive_proxy_score = self._simulate_proxy_expression_score(
                protein=protein,
                plant_host=plant_host,
                dna_features=naive_features,
                proxy_components=proxy_components,
                structure_annotation=structure_annotation,
            )

            proxy_score = self._simulate_proxy_expression_score(
                protein=protein,
                plant_host=plant_host,
                dna_features=features,
                proxy_components=proxy_components,
                structure_annotation=structure_annotation,
            )

            delta_cai = round(features.cai - naive_features.cai, 4)
            delta_gc = round(features.gc_content - naive_features.gc_content, 4)
            delta_proxy_expression = round(proxy_score - naive_proxy_score, 4)
            codon_usage_difference_score = _codon_usage_difference_score(
                naive_dna_sequence,
                result.dna_sequence,
            )

            rows.append(
                {
                    "protein_accession": protein.accession,
                    "accession": protein.accession,
                    "protein_name": protein.protein_name,
                    "organism": protein.organism,
                    "plant_host": plant_host,
                    "dna_sequence": result.dna_sequence,
                    "naive_dna_sequence": naive_dna_sequence,
                    "sequence_length_aa": len(protein.sequence),
                    "protein_length": structure_annotation.protein_length,
                    "sequence_length_nt": features.sequence_length_nt,
                    "cai": features.cai,
                    "gc_content": features.gc_content,
                    "gc_skew": features.gc_skew,
                    "naive_cai": naive_features.cai,
                    "naive_gc_content": naive_features.gc_content,
                    "delta_cai": delta_cai,
                    "delta_gc": delta_gc,
                    "gc3_content": features.gc3_content,
                    "at_content": features.at_content,
                    "purine_content": features.purine_content,
                    "codon_count": features.codon_count,
                    "unique_codons": features.unique_codons,
                    "codon_entropy": features.codon_entropy,
                    "effective_codon_fraction": features.effective_codon_fraction,
                    "stop_codon_count": features.stop_codon_count,
                    "invalid_codon_count": features.invalid_codon_count,
                    "repetitive_codon_ratio": features.repetitive_codon_ratio,
                    "rare_codon_ratio": features.rare_codon_ratio,
                    "helix_ratio": structure_annotation.helix_ratio,
                    "sheet_ratio": structure_annotation.sheet_ratio,
                    "coil_ratio": structure_annotation.coil_ratio,
                    "hydrophobicity_score": structure_annotation.hydrophobicity_score,
                    "stability_score": structure_annotation.stability_score,
                    "pdb_url": structure_annotation.pdb_url,
                    "pdb_id": structure_annotation.pdb_id,
                    "structure_confidence": (
                        structure_annotation.structure_confidence
                        if structure_annotation.structure_confidence is not None
                        else ""
                    ),
                    "structure_source": structure_annotation.structure_source,
                    "protein_aa_entropy": proxy_components["protein_aa_entropy"],
                    "protein_mean_hydrophobicity": proxy_components["protein_mean_hydrophobicity"],
                    "protein_length_penalty": proxy_components["protein_length_penalty"],
                    PROXY_TARGET_COLUMN: proxy_score,
                    "target_expression_score": proxy_score,
                    "naive_proxy_expression_score": naive_proxy_score,
                    "delta_proxy_expression": delta_proxy_expression,
                    "codon_usage_difference_score": codon_usage_difference_score,
                    "dna_valid": dna_valid,
                    "protein_valid": protein_valid,
                    "proxy_score_note": "Simulated proxy score combining sequence and structure descriptors; not experimental biology.",
                    "proxy_target_version": PROXY_TARGET_VERSION,
                }
            )

        if not rows:
            qc_stats["proteins_with_no_valid_dna_rows"] += 1
        return rows, qc_stats

    def _proxy_components(
        self,
        protein_sequence: str,
        structure_annotation: Optional[StructureAnnotation] = None,
    ) -> Dict[str, float]:
        if not protein_sequence:
            return {
                "protein_aa_entropy": 0.0,
                "protein_mean_hydrophobicity": 0.0,
                "protein_length_penalty": 1.0,
            }

        if structure_annotation is not None:
            normalized_hydrophobicity = _normalize_hydrophobicity(
                structure_annotation.hydrophobicity_score
            )
        else:
            normalized_hydrophobicity = _normalize_hydrophobicity(
                mean_hydrophobicity_kd(protein_sequence)
            )

        return {
            "protein_aa_entropy": _amino_acid_entropy(protein_sequence),
            "protein_mean_hydrophobicity": normalized_hydrophobicity,
            "protein_length_penalty": min(len(protein_sequence) / 1000.0, 1.0),
        }

    def _simulate_proxy_expression_score(
        self,
        protein: ProteinRecord,
        plant_host: str,
        dna_features: Any,
        proxy_components: Dict[str, float],
        structure_annotation: StructureAnnotation,
    ) -> float:
        """
        Simulated proxy target with partial independence from model inputs.

        The score mixes:
        - codon adaptation behavior per host,
        - structure-informed compatibility,
        - latent protein and host interaction terms,
        - deterministic biological variability.
        """
        host_factor = HOST_EXPRESSION_PRIORS.get(plant_host, 1.0)
        host_gc_optimum = HOST_GC_OPTIMA.get(plant_host, 0.5)

        gc_fit = max(0.0, 1.0 - abs(_to_float(dna_features.gc_content) - host_gc_optimum) * 2.2)
        gc3_fit = max(0.0, 1.0 - abs(_to_float(dna_features.gc3_content) - host_gc_optimum) * 1.4)
        cai_fit = _sigmoid((_to_float(dna_features.cai) - 0.78) * 9.0)
        codon_diversity_fit = _to_float(getattr(dna_features, "effective_codon_fraction", 0.5), default=0.5)
        codon_fit = (
            0.34 * cai_fit
            + 0.20 * gc_fit
            + 0.10 * gc3_fit
            + 0.20 * (1.0 - _to_float(dna_features.rare_codon_ratio))
            + 0.08 * (1.0 - _to_float(dna_features.repetitive_codon_ratio))
            + 0.08 * codon_diversity_fit
        )

        structure_compactness = max(0.0, min(1.0, 1.0 - abs(
            _to_float(structure_annotation.helix_ratio)
            - _to_float(structure_annotation.sheet_ratio)
        )))
        structure_fit = (
            0.45 * _to_float(structure_annotation.stability_score)
            + 0.35 * _hydrophobicity_balance(_to_float(structure_annotation.hydrophobicity_score))
            + 0.20 * structure_compactness
        )

        protein_weights = {
            "entropy": max(0.0, _to_float(self.pipeline_config.proxy_weight_aa_entropy, default=0.0)),
            "hydrophobicity": max(0.0, _to_float(self.pipeline_config.proxy_weight_hydrophobicity, default=0.0)),
            "length": max(0.0, _to_float(self.pipeline_config.proxy_weight_length_penalty, default=0.0)),
        }
        protein_weight_total = sum(protein_weights.values()) or 1.0
        protein_context_fit = (
            protein_weights["entropy"] * _to_float(proxy_components.get("protein_aa_entropy", 0.0))
            + protein_weights["hydrophobicity"]
            * (1.0 - abs(_to_float(proxy_components.get("protein_mean_hydrophobicity", 0.0))))
            + protein_weights["length"] * (1.0 - _to_float(proxy_components.get("protein_length_penalty", 1.0)))
        ) / protein_weight_total

        protein_latent = (
            0.55 * _sequence_latent_signature(protein.sequence)
            + 0.45 * _hash_unit_interval(f"{protein.accession}|{protein.organism}")
        )

        design_complexity = (
            0.55 * codon_diversity_fit
            + 0.45 * (1.0 - _to_float(dna_features.repetitive_codon_ratio))
        )

        host_interaction = 0.07 * _hash_signed_interval(f"{protein.accession}|{plant_host}|interaction")
        biological_variability = 0.055 * _hash_signed_interval(f"{protein.accession}|{plant_host}|bio")

        base_signal = (
            0.24 * codon_fit
            + 0.20 * structure_fit
            + 0.20 * protein_context_fit
            + 0.18 * protein_latent
            + 0.10 * gc_fit
            + 0.08 * design_complexity
        )

        score = (base_signal * host_factor) + host_interaction + biological_variability
        return round(max(0.0, min(1.0, score)), 4)

    def _is_valid_protein_sequence(self, protein_sequence: str) -> bool:
        return is_valid_protein_sequence(protein_sequence)

    def _validate_dna(self, dna_sequence: str) -> Optional[str]:
        return validate_dna_sequence(dna_sequence)

    def _train_model(self, dataset: List[Dict[str, Any]], metrics_path: str, safe_keyword: str) -> Dict[str, Any]:
        try:
            metrics, model_payloads = _train_model_grouped_impl(dataset, self.training_config)
            if "train_samples" in metrics and "test_samples" in metrics:
                self.logger.info(
                    "Training samples=%s, Test samples=%s",
                    metrics["train_samples"],
                    metrics["test_samples"],
                )

            if self.training_config.save_model and model_payloads:
                model_paths: Dict[str, str] = {}
                for model_name, payload in model_payloads.items():
                    model_path = str(Path(self.pipeline_config.output_dir) / f"model_{safe_keyword}_{model_name}.joblib")
                    _save_model(payload, model_path)
                    model_paths[model_name] = model_path

                metrics["model_paths"] = model_paths
                best_model = str(metrics.get("best_model_name") or metrics.get("best_model", ""))
                if best_model in model_paths:
                    metrics["model_path"] = model_paths[best_model]
                    metrics["best_model_path"] = model_paths[best_model]

            comparison_artifacts = _save_model_lab_artifacts(
                metrics,
                Path(self.pipeline_config.output_dir),
                safe_keyword,
            )
            metrics.update(comparison_artifacts)
            save_json(metrics_path, metrics)
            return metrics
        except Exception as exc:
            self.logger.warning("Training skipped: %s", exc)
            error_metrics = {
                "training_enabled": True,
                "skipped": True,
                "error": str(exc),
                "reason": "Training failed before metrics could be produced.",
                "target_column": PROXY_TARGET_COLUMN,
                "group_column": GROUP_COLUMN,
                "feature_names": list(UNIFIED_MODEL_FEATURES),
            }
            save_json(metrics_path, error_metrics)
            return error_metrics


def _train_model_grouped_impl(
    dataset: List[Dict[str, Any]],
    config: TrainingConfig,
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Backward-compatible wrapper for the grouped, leakage-controlled trainer."""
    return _train_model_grouped_impl_internal(dataset, config)


def _train_model_impl(
    dataset: List[Dict[str, Any]],
    config: TrainingConfig,
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Legacy entrypoint kept for compatibility; delegates to grouped training."""
    return _train_model_grouped_impl_internal(dataset, config)


def _save_model(payload: Dict[str, Any], path: str) -> None:
    import joblib

    joblib.dump(payload, path)


def _save_model_lab_artifacts(metrics: Dict[str, Any], output_dir: Path, safe_keyword: str) -> Dict[str, str]:
    model_lab = metrics.get("model_lab", {})
    comparison_rows = model_lab.get("comparison_rows", []) if isinstance(model_lab, dict) else []
    if not comparison_rows:
        return {}

    model_lab_path = str(output_dir / f"model_lab_{safe_keyword}.json")
    comparison_csv_path = str(output_dir / f"model_comparison_{safe_keyword}.csv")

    save_json(model_lab_path, model_lab)
    csv_rows = [
        {
            "model": row.get("model"),
            "display_name": row.get("display_name"),
            "mae": row.get("mae"),
            "rmse": row.get("rmse"),
            "r2": row.get("r2"),
            "validation_mae": row.get("validation_mae"),
            "validation_rmse": row.get("validation_rmse"),
            "validation_r2": row.get("validation_r2"),
            "training_time_seconds": row.get("training_time_seconds"),
            "prediction_time_seconds": row.get("prediction_time_seconds"),
            "accuracy_score": row.get("accuracy_score"),
            "speed_score": row.get("speed_score"),
            "interpretability_score": row.get("interpretability_score"),
            "interpretability_rating": row.get("interpretability_rating"),
            "overall_accuracy": (row.get("overall_scores") or {}).get("accuracy"),
            "overall_speed": (row.get("overall_scores") or {}).get("speed"),
            "overall_interpretability": (row.get("overall_scores") or {}).get("interpretability"),
            "overall_balanced": (row.get("overall_scores") or {}).get("balanced"),
            "recommended_for": row.get("recommended_for"),
        }
        for row in comparison_rows
    ]
    save_csv(
        comparison_csv_path,
        csv_rows,
        [
            "model",
            "display_name",
            "mae",
            "rmse",
            "r2",
            "validation_mae",
            "validation_rmse",
            "validation_r2",
            "training_time_seconds",
            "prediction_time_seconds",
            "accuracy_score",
            "speed_score",
            "interpretability_score",
            "interpretability_rating",
            "overall_accuracy",
            "overall_speed",
            "overall_interpretability",
            "overall_balanced",
            "recommended_for",
        ],
    )
    return {
        "model_lab_path": model_lab_path,
        "model_comparison_csv_path": comparison_csv_path,
    }


def _amino_acid_entropy(protein_sequence: str) -> float:
    from collections import Counter
    import math

    seq = protein_sequence.upper()
    counts = Counter(seq)
    total = sum(counts.values())
    if total == 0:
        return 0.0

    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log(p, 2)

    return round(entropy / math.log(20, 2), 4)


def _normalize_hydrophobicity(kd_mean_value: float) -> float:
    return round(max(-1.0, min(1.0, kd_mean_value / 4.5)), 4)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _hash_unit_interval(text: str) -> float:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    integer = int.from_bytes(digest[:8], "big")
    return integer / float((1 << 64) - 1)


def _hash_signed_interval(text: str) -> float:
    return (_hash_unit_interval(text) * 2.0) - 1.0


def _hydrophobicity_balance(hydrophobicity_score: float) -> float:
    # Penalize extreme hydrophobicity values and favor balanced proteins.
    return max(0.0, 1.0 - abs(hydrophobicity_score) / 4.5)


def _sigmoid(value: float) -> float:
    clipped = max(-60.0, min(60.0, value))
    return float(1.0 / (1.0 + np.exp(-clipped)))


def _sequence_latent_signature(sequence: str) -> float:
    seq = (sequence or "").upper()
    if not seq:
        return 0.0
    motif_score = (
        seq.count("N")
        + seq.count("Q")
        + seq.count("S")
        + seq.count("T")
    ) / len(seq)
    return max(0.0, min(1.0, 0.65 * motif_score + 0.35 * _hash_unit_interval(seq[:120])))


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    diff = y_true - y_pred
    return float(np.sqrt(np.mean(np.square(diff))))


def _codon_usage_difference_score(naive_dna: str, optimized_dna: str) -> float:
    naive = (naive_dna or "").upper()
    optimized = (optimized_dna or "").upper()
    common_len = min(len(naive), len(optimized))
    common_len -= common_len % 3
    if common_len <= 0:
        return 0.0

    codon_total = common_len // 3
    differences = 0
    for i in range(0, common_len, 3):
        if naive[i : i + 3] != optimized[i : i + 3]:
            differences += 1

    return round(differences / codon_total, 4)

