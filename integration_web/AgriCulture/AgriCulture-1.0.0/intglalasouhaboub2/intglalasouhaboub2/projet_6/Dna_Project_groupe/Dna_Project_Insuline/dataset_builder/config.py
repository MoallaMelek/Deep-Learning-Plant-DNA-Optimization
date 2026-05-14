"""Configuration for automated dataset generation."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class UniprotConfig:
    base_url: str = "https://rest.uniprot.org/uniprotkb/search"
    fields: str = "accession,protein_name,organism_name,sequence"
    batch_size: int = 100
    timeout_sec: int = 20
    max_retries: int = 3
    user_agent: str = "dna-project-insuline/1.0"


@dataclass(frozen=True)
class PipelineConfig:
    output_dir: str = "outputs/datasets"
    random_seed: int = 42
    codon_min_relative_frequency: float = 0.62
    codon_frequency_exponent: float = 1.8
    codon_exploration_rate: float = 0.05
    plant_hosts: List[str] = field(
        default_factory=lambda: [
            "Arabidopsis thaliana",
            "Oryza sativa",
            "Zea mays",
            "Phoenix dactylifera",
        ]
    )
    default_keyword: str = "receptor"
    default_protein_limit: int = 180
    rare_codon_threshold: float = 10.0
    proxy_weight_aa_entropy: float = 0.5
    proxy_weight_hydrophobicity: float = 0.3
    proxy_weight_length_penalty: float = 0.2
    alphafold_enabled: bool = True
    structure_timeout_sec: int = 20
    structure_max_retries: int = 2


@dataclass(frozen=True)
class TrainingConfig:
    enabled: bool = True
    enabled_models: Optional[List[str]] = None
    test_size: float = 0.2
    random_state: int = 42
    hyperparameter_search: bool = True
    rf_n_estimators: int = 350
    rf_max_depth: int = 14
    min_samples_split: int = 2
    min_samples_leaf: int = 1
    xgb_n_estimators: int = 350
    xgb_max_depth: int = 6
    xgb_learning_rate: float = 0.05
    xgb_subsample: float = 0.9
    xgb_colsample_bytree: float = 0.9
    baseline_min_relative_improvement: float = 0.01
    save_model: bool = True
