"""DNA sequence feature encoding for model inputs."""

from __future__ import annotations

from itertools import product
from typing import Dict, List

import numpy as np

BASES = ("A", "C", "G", "T")


def nucleotide_composition(sequence: str) -> np.ndarray:
    seq = sequence.upper()
    n = max(1, len(seq))
    return np.array([seq.count(base) / n for base in BASES], dtype=np.float32)


def gc_content(sequence: str) -> float:
    seq = sequence.upper()
    n = max(1, len(seq))
    return float((seq.count("G") + seq.count("C")) / n)


def kmer_index(k: int = 3) -> Dict[str, int]:
    return {"".join(chars): i for i, chars in enumerate(product(BASES, repeat=k))}


def encode_kmer_frequency(sequence: str, k: int = 3) -> np.ndarray:
    seq = sequence.upper()
    idx = kmer_index(k)
    vec = np.zeros(len(idx), dtype=np.float32)
    if len(seq) < k:
        return vec
    for i in range(len(seq) - k + 1):
        token = seq[i : i + k]
        if token in idx:
            vec[idx[token]] += 1.0
    total = vec.sum()
    if total > 0:
        vec /= total
    return vec


def build_dna_feature_vector(sequence: str, k: int = 3) -> np.ndarray:
    seq = sequence.upper()
    comp = nucleotide_composition(seq)
    gc = np.array([gc_content(seq)], dtype=np.float32)
    length_scaled = np.array([min(len(seq), 50_000) / 50_000.0], dtype=np.float32)
    kmers = encode_kmer_frequency(seq, k=k)
    return np.concatenate([comp, gc, length_scaled, kmers], axis=0).astype(np.float32)


def feature_names(k: int = 3) -> List[str]:
    names = [f"comp_{b}" for b in BASES] + ["gc_content", "length_scaled"]
    names += [f"kmer_{kmer}" for kmer in kmer_index(k).keys()]
    return names
