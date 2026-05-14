"""Shared schema constants for generated datasets and model artifacts."""

from typing import Dict, List


PROXY_TARGET_COLUMN = "simulated_proxy_expression_score"
LEGACY_TARGET_COLUMN = "target_expression_score"
GROUP_COLUMN = "protein_accession"
PROXY_TARGET_VERSION = "v2_soft_codon_surrogate"

CATEGORICAL_MODEL_FEATURES: List[str] = ["plant_host"]

TARGET_DERIVED_COLUMNS: List[str] = [
    PROXY_TARGET_COLUMN,
    LEGACY_TARGET_COLUMN,
    "naive_proxy_expression_score",
    "delta_proxy_expression",
]

DESCRIPTIVE_ONLY_COLUMNS: List[str] = [
    "protein_accession",
    "accession",
    "protein_name",
    "organism",
    "sequence_length_aa",
    "dna_sequence",
    "naive_dna_sequence",
    "pdb_url",
    "pdb_id",
    "structure_source",
    "naive_cai",
    "naive_gc_content",
    "delta_cai",
    "delta_gc",
    "codon_usage_difference_score",
    "dna_valid",
    "protein_valid",
    "proxy_score_note",
    "proxy_target_version",
]

UNIFIED_MODEL_FEATURES: List[str] = [
    "cai",
    "gc_content",
    "gc_skew",
    "gc3_content",
    "at_content",
    "purine_content",
    "codon_count",
    "sequence_length_nt",
    "unique_codons",
    "codon_entropy",
    "effective_codon_fraction",
    "stop_codon_count",
    "invalid_codon_count",
    "repetitive_codon_ratio",
    "rare_codon_ratio",
    "protein_aa_entropy",
    "protein_mean_hydrophobicity",
    "protein_length_penalty",
    "helix_ratio",
    "sheet_ratio",
    "coil_ratio",
    "hydrophobicity_score",
    "stability_score",
    "protein_length",
    "structure_confidence",
]

GENERATED_MODEL_FEATURES: List[str] = [
    "gc_deviation",
    "codon_efficiency",
    "stability_index",
]

FEATURE_BLOCKS: Dict[str, List[str]] = {
    "dna_codon": [
        "cai",
        "gc_content",
        "gc_skew",
        "gc3_content",
        "purine_content",
        "unique_codons",
        "codon_entropy",
        "effective_codon_fraction",
        "repetitive_codon_ratio",
        "rare_codon_ratio",
        "gc_deviation",
        "codon_efficiency",
        "stability_index",
    ],
    "protein_sequence": [
        "protein_length",
        "protein_aa_entropy",
        "protein_length_penalty",
        "protein_mean_hydrophobicity",
    ],
    "structure": [
        "helix_ratio",
        "sheet_ratio",
        "coil_ratio",
        "hydrophobicity_score",
        "stability_score",
        "structure_confidence",
    ],
    "host": list(CATEGORICAL_MODEL_FEATURES),
}

FEATURE_PRIORITY: Dict[str, int] = {
    "cai": 0,
    "gc_content": 1,
    "gc_skew": 2,
    "gc3_content": 3,
    "purine_content": 4,
    "rare_codon_ratio": 5,
    "repetitive_codon_ratio": 6,
    "codon_entropy": 7,
    "effective_codon_fraction": 8,
    "unique_codons": 9,
    "protein_length": 10,
    "protein_aa_entropy": 11,
    "hydrophobicity_score": 12,
    "stability_score": 13,
    "helix_ratio": 14,
    "sheet_ratio": 15,
    "coil_ratio": 16,
    "structure_confidence": 17,
    "gc_deviation": 18,
    "codon_efficiency": 19,
    "stability_index": 20,
}

HOST_EXPRESSION_PRIORS: Dict[str, float] = {
    "Arabidopsis thaliana": 0.97,
    "Oryza sativa": 1.01,
    "Zea mays": 1.05,
    "Phoenix dactylifera": 0.95,
}

HOST_GC_OPTIMA: Dict[str, float] = {
    "Arabidopsis thaliana": 0.43,
    "Oryza sativa": 0.56,
    "Zea mays": 0.58,
    "Phoenix dactylifera": 0.48,
}

DATASET_FIELDNAMES: List[str] = [
    "protein_accession",
    "accession",
    "protein_name",
    "organism",
    "plant_host",
    "dna_sequence",
    "naive_dna_sequence",
    "sequence_length_aa",
    "protein_length",
    "sequence_length_nt",
    "cai",
    "gc_content",
    "gc_skew",
    "naive_cai",
    "naive_gc_content",
    "delta_cai",
    "delta_gc",
    "gc3_content",
    "at_content",
    "purine_content",
    "codon_count",
    "unique_codons",
    "codon_entropy",
    "effective_codon_fraction",
    "stop_codon_count",
    "invalid_codon_count",
    "repetitive_codon_ratio",
    "rare_codon_ratio",
    "helix_ratio",
    "sheet_ratio",
    "coil_ratio",
    "hydrophobicity_score",
    "stability_score",
    "pdb_url",
    "pdb_id",
    "structure_confidence",
    "structure_source",
    "protein_aa_entropy",
    "protein_mean_hydrophobicity",
    "protein_length_penalty",
    PROXY_TARGET_COLUMN,
    LEGACY_TARGET_COLUMN,
    "naive_proxy_expression_score",
    "delta_proxy_expression",
    "codon_usage_difference_score",
    "dna_valid",
    "protein_valid",
    "proxy_score_note",
    "proxy_target_version",
]
