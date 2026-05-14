from __future__ import annotations

from app.services.dna_analysis import gc_content, normalize_sequence


def test_normalize_sequence() -> None:
    assert normalize_sequence("atgcNNNxyz") == "ATGC"


def test_gc_content() -> None:
    assert gc_content("GGCCATAT") == 50.0

