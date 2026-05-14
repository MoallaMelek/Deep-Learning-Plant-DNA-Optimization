"""Minimal src package exports used by the final Streamlit demo."""

from .codon_analysis import (
    calculate_gc_content,
    calculate_cai,
    optimize_codons,
    naive_translation,
    compare_sequences,
    compare_all_species,
    count_rare_codons,
    extract_ml_features,
    extract_features_all_species,
    get_feature_vector,
    get_feature_names
)

__all__ = [
    'calculate_gc_content',
    'calculate_cai',
    'optimize_codons',
    'naive_translation',
    'compare_sequences',
    'compare_all_species',
    'count_rare_codons',
    'extract_ml_features',
    'extract_features_all_species',
    'get_feature_vector',
    'get_feature_names'
]
