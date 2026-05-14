"""
Codon Analysis Module
=====================
Functions for codon optimization and analysis.
Part of Module 5 - Therapeutic Protein Production Pipeline.

This module provides:
1. CAI (Codon Adaptation Index) calculation
2. Codon optimization for plant expression
3. Sequence comparison (naive vs optimized)
4. Feature extraction for machine learning

All functions use real Kazusa codon usage data.
"""

import math
import random
from typing import Dict, List, Tuple, Optional
import sys
from pathlib import Path

try:
    from data.codon_tables.codon_data import (
        CODON_TABLES,
        CODON_TO_AA,
        AA_TO_CODONS,
        SUPPORTED_SPECIES,
        get_codon_table,
        get_codons_for_aa,
    )
except ImportError:
    # Backward-compatible fallback for running this file directly as a script.
    codon_table_dir = Path(__file__).resolve().parents[1] / "data" / "codon_tables"
    if str(codon_table_dir) not in sys.path:
        sys.path.insert(0, str(codon_table_dir))
    from codon_data import (  # type: ignore[no-redef]
        CODON_TABLES,
        CODON_TO_AA,
        AA_TO_CODONS,
        SUPPORTED_SPECIES,
        get_codon_table,
        get_codons_for_aa,
    )


# =============================================================================
# GC CONTENT CALCULATION
# =============================================================================

def calculate_gc_content(dna_sequence: str) -> float:
    """
    Calculate the GC content of a DNA sequence.
    
    GC content = (number of G + number of C) / total length
    
    This is important because:
    - GC content affects DNA stability (higher GC = more stable)
    - Plants prefer certain GC ranges (typically 40-60%)
    
    Args:
        dna_sequence: DNA sequence string (only A, T, G, C)
        
    Returns:
        GC content as a decimal (0.0 to 1.0)
        
    Example:
        >>> calculate_gc_content("ATGCATGC")
        0.5  # 4 G/C out of 8 total
    """
    if not dna_sequence:
        return 0.0
    
    # Convert to uppercase for consistency
    seq = dna_sequence.upper()
    
    # Count G and C nucleotides
    gc_count = seq.count('G') + seq.count('C')
    
    # Calculate percentage
    gc_content = gc_count / len(seq)
    
    return round(gc_content, 4)


# =============================================================================
# CODON ADAPTATION INDEX (CAI) CALCULATION
# =============================================================================

def calculate_cai(dna_sequence: str, species: str) -> float:
    """
    Calculate the Codon Adaptation Index (CAI) for a DNA sequence.
    
    CAI measures how well the codon usage of a sequence matches
    the preferred codon usage of the target organism.
    
    HOW CAI IS CALCULATED:
    ----------------------
    1. For each amino acid, find the most frequent codon (reference codon)
    2. For each codon in the sequence, calculate "relative adaptiveness" (w):
       w = frequency of this codon / frequency of reference codon
    3. CAI = geometric mean of all w values
       CAI = (w1 × w2 × w3 × ... × wn)^(1/n)
    
    CAI ranges from 0 to 1:
    - CAI close to 1 = codons match the organism's preferences (good!)
    - CAI close to 0 = codons are rarely used by this organism (bad)
    
    Args:
        dna_sequence: DNA sequence (must be divisible by 3)
        species: Target plant species name
        
    Returns:
        CAI score between 0 and 1
        
    Example:
        >>> calculate_cai("ATGGCGTGA", "Arabidopsis thaliana")
        0.85  # Example value
    """
    # Validate sequence length
    if len(dna_sequence) % 3 != 0:
        raise ValueError("DNA sequence length must be divisible by 3 (codons)")
    
    if not dna_sequence:
        return 0.0
    
    # Get codon usage table for the species
    codon_table = get_codon_table(species)
    
    # Step 1: Find the maximum frequency codon for each amino acid
    # This will be our reference (w_max)
    max_freq_per_aa = {}
    for aa, codons in AA_TO_CODONS.items():
        if aa == '*':  # Skip stop codons
            continue
        # Find the maximum frequency among all codons for this amino acid
        max_freq = max(codon_table.get(codon, 0.0) for codon in codons)
        max_freq_per_aa[aa] = max_freq
    
    # Step 2: Split sequence into codons
    codons = [dna_sequence[i:i+3].upper() for i in range(0, len(dna_sequence), 3)]
    
    # Step 3: Calculate relative adaptiveness for each codon
    w_values = []
    
    for codon in codons:
        # Get the amino acid this codon encodes
        aa = CODON_TO_AA.get(codon)
        
        if aa is None or aa == '*':
            # Skip unknown or stop codons
            continue
        
        # Get frequency of this codon
        codon_freq = codon_table.get(codon, 0.0)
        
        # Get maximum frequency for this amino acid
        max_freq = max_freq_per_aa.get(aa, 0.0)
        
        if max_freq > 0:
            # Calculate relative adaptiveness (w)
            # w = codon_frequency / max_frequency_for_this_aa
            w = codon_freq / max_freq
            w_values.append(w)
    
    # Step 4: Calculate CAI as geometric mean
    if not w_values:
        return 0.0
    
    # Geometric mean = (product of all values)^(1/n)
    # Using logarithms to avoid overflow: exp(mean(log(values)))
    # Filter out zero values (would make log undefined)
    non_zero_w = [w for w in w_values if w > 0]
    
    if not non_zero_w:
        return 0.0
    
    log_sum = sum(math.log(w) for w in non_zero_w)
    cai = math.exp(log_sum / len(non_zero_w))
    
    return round(cai, 4)


# =============================================================================
# CODON OPTIMIZATION
# =============================================================================

def optimize_codons(
    protein_sequence: str,
    species: str,
    random_state: Optional[int] = None,
    min_relative_frequency: float = 0.62,
    frequency_exponent: float = 1.8,
    exploration_rate: float = 0.05,
) -> str:
    """
    Convert a protein sequence to host-adapted DNA using synonymous codons.
    
    This strategy is intentionally biased toward highly preferred host codons,
    but not perfectly greedy. For each amino acid:
    1) keep codons above a relative-frequency cutoff for most positions,
    2) occasionally sample from all observed synonymous codons,
    3) use frequency-weighted probabilities rather than strict top-codon picks.

    This usually improves CAI versus naive translation while avoiding the
    artificial "always CAI=1" behavior of strict top-codon selection.
    
    Args:
        protein_sequence: Amino acid sequence (single letter codes)
        species: Target plant species name
        random_state: Optional seed for reproducible codon sampling
        min_relative_frequency: Keep codons with freq >= max_freq * this value
        frequency_exponent: Weight sharpness (>1 biases toward top codons)
        exploration_rate: Probability of sampling from all positive-frequency
            synonymous codons instead of only the preferred pool
        
    Returns:
        Optimized DNA sequence
        
    Example:
        >>> optimize_codons("MKL", "Arabidopsis thaliana")
        "ATGAAACTC"  # Uses preferred codons for Arabidopsis
    """
    if not (0.0 <= min_relative_frequency <= 1.0):
        raise ValueError("min_relative_frequency must be between 0.0 and 1.0")
    if frequency_exponent <= 0:
        raise ValueError("frequency_exponent must be > 0")
    if not (0.0 <= exploration_rate <= 1.0):
        raise ValueError("exploration_rate must be between 0.0 and 1.0")

    # Get codon usage table for the species
    codon_table = get_codon_table(species)
    rng = random.Random(random_state) if random_state is not None else random
    
    dna_codons = []
    
    for aa in protein_sequence.upper():
        # Get all codons that encode this amino acid
        possible_codons = get_codons_for_aa(aa)

        codon_freqs: List[Tuple[str, float]] = [
            (codon, max(0.0, float(codon_table.get(codon, 0.0))))
            for codon in possible_codons
        ]
        positive_freqs = [(codon, freq) for codon, freq in codon_freqs if freq > 0]

        # Fallback for sparse/unknown usage tables: keep genetic-code validity.
        if not positive_freqs:
            dna_codons.append(possible_codons[0])
            continue

        max_freq = max(freq for _, freq in positive_freqs)
        cutoff = max_freq * min_relative_frequency
        preferred_pool = [
            (codon, freq) for codon, freq in positive_freqs if freq >= cutoff
        ]

        if not preferred_pool:
            preferred_pool = [max(positive_freqs, key=lambda item: item[1])]

        # If the cutoff leaves a single synonymous option, include the next best
        # observed codon so long proteins do not collapse to an ideal CAI=1 design.
        if len(preferred_pool) == 1 and len(positive_freqs) > 1:
            preferred_codons = {codon for codon, _ in preferred_pool}
            fallback_codons = [
                item for item in sorted(positive_freqs, key=lambda value: value[1], reverse=True)
                if item[0] not in preferred_codons
            ]
            if fallback_codons:
                preferred_pool.append(fallback_codons[0])

        candidate_pool = (
            positive_freqs
            if len(positive_freqs) > 1 and rng.random() < exploration_rate
            else preferred_pool
        )

        codon_candidates = [codon for codon, _ in candidate_pool]
        weights = [((freq / max_freq) ** frequency_exponent) for _, freq in candidate_pool]
        dna_codons.append(rng.choices(codon_candidates, weights=weights, k=1)[0])
    
    return "".join(dna_codons)


def naive_translation(protein_sequence: str) -> str:
    """
    Convert a protein sequence to DNA using the first available codon.
    
    This is the "naive" approach - it doesn't consider codon preferences.
    It's used as a baseline for comparison with optimized sequences.
    
    Args:
        protein_sequence: Amino acid sequence (single letter codes)
        
    Returns:
        DNA sequence (not optimized)
    """
    dna_codons = []
    
    for aa in protein_sequence.upper():
        # Get all codons and just use the first one
        possible_codons = get_codons_for_aa(aa)
        dna_codons.append(possible_codons[0])
    
    return "".join(dna_codons)


# =============================================================================
# SEQUENCE COMPARISON
# =============================================================================

def compare_sequences(
    protein_sequence: str,
    species: str,
    random_state: Optional[int] = None,
) -> Dict:
    """
    Compare naive vs optimized DNA sequences for a protein.
    
    This function:
    1. Generates naive DNA (first available codon)
    2. Generates optimized DNA (best codon for species)
    3. Calculates GC content and CAI for both
    4. Computes improvement metrics
    
    Args:
        protein_sequence: Amino acid sequence
        species: Target plant species
        
    Returns:
        Dictionary with comparison results
    """
    # Generate both DNA versions
    naive_dna = naive_translation(protein_sequence)
    optimized_dna = optimize_codons(protein_sequence, species, random_state=random_state)
    
    # Calculate metrics for naive sequence
    naive_gc = calculate_gc_content(naive_dna)
    naive_cai = calculate_cai(naive_dna, species)
    
    # Calculate metrics for optimized sequence
    opt_gc = calculate_gc_content(optimized_dna)
    opt_cai = calculate_cai(optimized_dna, species)
    
    # Calculate improvements
    cai_improvement = opt_cai - naive_cai
    gc_change = opt_gc - naive_gc
    
    return {
        "species": species,
        "protein_length": len(protein_sequence),
        "dna_length": len(optimized_dna),
        "naive": {
            "sequence": naive_dna,
            "gc_content": naive_gc,
            "cai": naive_cai
        },
        "optimized": {
            "sequence": optimized_dna,
            "gc_content": opt_gc,
            "cai": opt_cai
        },
        "improvement": {
            "cai_gain": round(cai_improvement, 4),
            "gc_change": round(gc_change, 4)
        }
    }


def compare_all_species(protein_sequence: str, random_state: Optional[int] = None) -> Dict:
    """
    Compare optimization results across all supported plant species.
    
    Args:
        protein_sequence: Amino acid sequence
        
    Returns:
        Dictionary with results for each species
    """
    results = {}
    
    for idx, species in enumerate(SUPPORTED_SPECIES):
        species_seed = None if random_state is None else (random_state + idx)
        results[species] = compare_sequences(
            protein_sequence,
            species,
            random_state=species_seed,
        )
    
    return results


# =============================================================================
# RARE CODON ANALYSIS
# =============================================================================

def count_rare_codons(dna_sequence: str, species: str, threshold: float = 10.0) -> Dict:
    """
    Count the number of rare codons in a DNA sequence.
    
    A rare codon is defined as a codon with frequency below the threshold
    (default: 10 per 1000 codons).
    
    Rare codons can slow down translation and reduce protein expression.
    
    Args:
        dna_sequence: DNA sequence
        species: Target plant species
        threshold: Frequency threshold (codons below this are "rare")
        
    Returns:
        Dictionary with rare codon statistics
    """
    codon_table = get_codon_table(species)
    
    # Split into complete codons only. Incomplete trailing chunks are invalid
    # sequence quality issues, not biologically meaningful rare codons.
    raw_codons = [dna_sequence[i:i+3].upper() for i in range(0, len(dna_sequence), 3)]
    codons = [codon for codon in raw_codons if len(codon) == 3]
    incomplete_codon_count = len(raw_codons) - len(codons)
    
    rare_codons = []
    rare_count = 0
    invalid_codon_count = 0
    
    for codon in codons:
        freq = codon_table.get(codon, 0.0)
        aa = CODON_TO_AA.get(codon)

        if aa is None:
            invalid_codon_count += 1
            continue
        
        if freq < threshold and aa != '*':
            rare_count += 1
            rare_codons.append({
                "codon": codon,
                "amino_acid": aa,
                "frequency": freq
            })
    
    return {
        "total_codons": len(codons),
        "rare_codon_count": rare_count,
        "rare_codon_percentage": round(rare_count / len(codons) * 100, 2) if codons else 0,
        "invalid_codon_count": invalid_codon_count,
        "incomplete_codon_count": incomplete_codon_count,
        "threshold": threshold,
        "rare_codons": rare_codons[:10]  # Return first 10 for brevity
    }


# =============================================================================
# FEATURE EXTRACTION FOR MACHINE LEARNING
# =============================================================================

def extract_ml_features(protein_sequence: str, dna_sequence: str, species: str) -> Dict:
    """
    Extract features from sequences for machine learning models.
    
    This function prepares a feature vector that can be used to predict
    protein expression levels or other properties.
    
    Features extracted:
    1. gc_content: GC percentage of DNA
    2. cai: Codon Adaptation Index
    3. sequence_length: Number of amino acids
    4. dna_length: Number of nucleotides
    5. rare_codon_count: Number of rare codons
    6. rare_codon_fraction: Proportion of rare codons
    
    Args:
        protein_sequence: Amino acid sequence
        dna_sequence: DNA sequence (optimized)
        species: Target plant species
        
    Returns:
        Dictionary of features (easy to convert to ML input)
    """
    # Basic sequence properties
    gc = calculate_gc_content(dna_sequence)
    cai = calculate_cai(dna_sequence, species)
    
    # Rare codon analysis
    rare_analysis = count_rare_codons(dna_sequence, species)
    
    # Calculate additional properties
    # GC at third codon position (GC3)
    codons = [dna_sequence[i:i+3].upper() for i in range(0, len(dna_sequence), 3)]
    gc3_count = sum(1 for c in codons if len(c) == 3 and c[2] in 'GC')
    gc3 = gc3_count / len(codons) if codons else 0
    
    # Create feature vector
    features = {
        # Sequence lengths
        "protein_length": len(protein_sequence),
        "dna_length": len(dna_sequence),
        
        # Composition features
        "gc_content": gc,
        "gc3_content": round(gc3, 4),
        
        # Codon usage features
        "cai": cai,
        "rare_codon_count": rare_analysis["rare_codon_count"],
        "rare_codon_fraction": round(rare_analysis["rare_codon_count"] / len(codons), 4) if codons else 0,
        
        # Species information
        "species": species
    }
    
    return features


def extract_features_all_species(protein_sequence: str, random_state: Optional[int] = None) -> Dict:
    """
    Extract ML features for all supported plant species.
    
    Args:
        protein_sequence: Amino acid sequence
        
    Returns:
        Dictionary mapping species to feature dictionaries
    """
    all_features = {}
    
    for idx, species in enumerate(SUPPORTED_SPECIES):
        # Optimize DNA for this species
        species_seed = None if random_state is None else (random_state + idx)
        optimized_dna = optimize_codons(
            protein_sequence,
            species,
            random_state=species_seed,
        )
        
        # Extract features
        features = extract_ml_features(protein_sequence, optimized_dna, species)
        all_features[species] = features
    
    return all_features


def get_feature_vector(features: Dict) -> List[float]:
    """
    Convert feature dictionary to a numeric vector for ML models.
    
    This function extracts only the numeric features in a consistent order.
    
    Args:
        features: Feature dictionary from extract_ml_features()
        
    Returns:
        List of numeric values
    """
    # Define the order of features
    feature_order = [
        "protein_length",
        "dna_length",
        "gc_content",
        "gc3_content",
        "cai",
        "rare_codon_count",
        "rare_codon_fraction"
    ]
    
    return [features[key] for key in feature_order]


def get_feature_names() -> List[str]:
    """Return the names of ML features in order."""
    return [
        "protein_length",
        "dna_length",
        "gc_content",
        "gc3_content",
        "cai",
        "rare_codon_count",
        "rare_codon_fraction"
    ]


# =============================================================================
# MAIN (TESTING)
# =============================================================================

if __name__ == "__main__":
    # Test with a short protein sequence
    test_protein = "MALWMRLLPL"
    
    print("Codon Analysis Module - Test")
    print("=" * 60)
    print(f"Test protein: {test_protein}")
    print()
    
    # Compare all species
    print("SPECIES COMPARISON")
    print("-" * 60)
    
    for species in SUPPORTED_SPECIES:
        result = compare_sequences(test_protein, species, random_state=42)
        print(f"\n{species}:")
        print(f"  Naive CAI:     {result['naive']['cai']:.4f}")
        print(f"  Optimized CAI: {result['optimized']['cai']:.4f}")
        print(f"  CAI Gain:      +{result['improvement']['cai_gain']:.4f}")
        print(f"  GC Content:    {result['optimized']['gc_content']:.1%}")
    
    # Show ML features
    print("\n" + "=" * 60)
    print("ML FEATURES (Arabidopsis)")
    print("-" * 60)
    
    opt_dna = optimize_codons(test_protein, "Arabidopsis thaliana", random_state=42)
    features = extract_ml_features(test_protein, opt_dna, "Arabidopsis thaliana")
    
    for key, value in features.items():
        print(f"  {key}: {value}")
