"""Validation helpers shared by dataset generation and tests."""

from typing import Optional


VALID_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")
VALID_DNA_BASES = frozenset("ATGC")
STOP_CODONS = frozenset({"TAA", "TAG", "TGA"})


def is_valid_protein_sequence(protein_sequence: str) -> bool:
    seq = (protein_sequence or "").strip().upper()
    return bool(seq) and all(aa in VALID_AMINO_ACIDS for aa in seq)


def validate_dna_sequence(dna_sequence: str) -> Optional[str]:
    """Return a data-quality reason when a coding DNA sequence is invalid."""
    if not dna_sequence:
        return "invalid_sequence_filtered"
    if len(dna_sequence) % 3 != 0:
        return "invalid_length_filtered"

    seq = dna_sequence.upper()
    if any(base not in VALID_DNA_BASES for base in seq):
        return "invalid_nucleotides_filtered"

    codons = [seq[i : i + 3] for i in range(0, len(seq), 3)]
    if any(codon in STOP_CODONS for codon in codons[:-1]):
        return "internal_stop_filtered"

    return None
