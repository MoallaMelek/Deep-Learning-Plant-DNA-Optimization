"""Utilities for loading and validating plant DNA sequences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

NCBI_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Arabidopsis thaliana DNA fragment (example).
EXAMPLE_DNA_SEQUENCE = (
    "ATGGCTTCTTCTTCTGCTTCTCCGTTGCTGCTGCTGTTGATGGTGGTGATGCTGCTGATGAT"
    "GCTGATGCTGATGTTGCTGATGATGCTGCTGCTGATGCTGATGATGCTGATGATGCTGATGAT"
    "GCTGATGATGCTGATGATGCTGCTGATGATGCTGATGATGCTGCTGATGATGCTGCTGATGAT"
)


@dataclass
class DNARecord:
    sequence: str
    source: str


def sanitize_dna_sequence(sequence: str) -> str:
    """Uppercase sequence and keep only valid DNA bases."""
    cleaned = "".join(base for base in sequence.upper() if base in {"A", "C", "G", "T"})
    if len(cleaned) < 30:
        raise ValueError("DNA sequence is too short after cleaning (minimum 30 bases).")
    return cleaned


def parse_fasta_sequence(fasta_text: str) -> str:
    """Extract sequence from FASTA content."""
    lines = [line.strip() for line in fasta_text.splitlines() if line.strip()]
    seq_lines = [line for line in lines if not line.startswith(">")]
    if not seq_lines:
        raise ValueError("No DNA sequence found in FASTA content.")
    return sanitize_dna_sequence("".join(seq_lines))


def fetch_ncbi_sequence(accession: str, email: Optional[str] = None, timeout: int = 20) -> DNARecord:
    """Download a nucleotide sequence from NCBI by accession."""
    params = {
        "db": "nuccore",
        "id": accession,
        "rettype": "fasta",
        "retmode": "text",
    }
    if email:
        params["email"] = email

    response = requests.get(NCBI_EFETCH_URL, params=params, timeout=timeout)
    response.raise_for_status()
    sequence = parse_fasta_sequence(response.text)
    return DNARecord(sequence=sequence, source=f"NCBI:{accession}")


def load_dna_sequence(
    raw_sequence: Optional[str] = None,
    accession: Optional[str] = None,
    email: Optional[str] = None,
) -> DNARecord:
    """Load DNA from raw input, NCBI accession, or bundled example."""
    if raw_sequence and raw_sequence.strip():
        return DNARecord(sequence=sanitize_dna_sequence(raw_sequence), source="user_input")
    if accession and accession.strip():
        return fetch_ncbi_sequence(accession.strip(), email=email)
    return DNARecord(sequence=sanitize_dna_sequence(EXAMPLE_DNA_SEQUENCE), source="example")
