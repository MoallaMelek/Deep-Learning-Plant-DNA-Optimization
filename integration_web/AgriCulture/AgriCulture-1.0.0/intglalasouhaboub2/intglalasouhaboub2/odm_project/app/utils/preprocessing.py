import re
import random
import numpy as np
from Bio.Seq import Seq


def clean_sequence(seq: str) -> str:
    """Uppercase, strip whitespace/newlines, keep only ATCGN."""
    seq = seq.upper().replace(" ", "").replace("\n", "").replace("\r", "").strip()
    seq = re.sub(r"[^ATCGN]", "", seq)
    return seq


def validate_sequence(seq: str) -> tuple[bool, str]:
    """Return (is_valid, error_message)."""
    if not seq:
        return False, "Sequence is empty."
    if len(seq) < 50:
        return False, f"Sequence too short ({len(seq)} bp). Minimum is 50 bp."
    invalid = set(seq) - set("ATCGN")
    if invalid:
        return False, f"Invalid bases detected: {invalid}"
    n_ratio = seq.count("N") / len(seq)
    if n_ratio > 0.3:
        return False, f"Too many N bases ({n_ratio:.1%}). Maximum 30 % allowed."
    return True, ""


def resolve_sequence(full_seq: str, start_primer: str, end_primer: str,
                     estimated_length: int = 400) -> tuple[str, str]:
    """
    Resolve target sequence from:
    - a full sequence (priority), OR
    - a start/end primer pair (fills the gap with synthetic nucleotides).
    Returns (sequence, info_message).
    """
    full_seq     = clean_sequence(full_seq)
    start_primer = clean_sequence(start_primer)
    end_primer   = clean_sequence(end_primer)

    if full_seq:
        return full_seq, f"Full sequence provided ({len(full_seq)} bp)"

    if start_primer and end_primer:
        n_fill = max(0, estimated_length - len(start_primer) - len(end_primer))
        fill   = ("ATCGATCGAT" * (n_fill // 10 + 1))[:n_fill]
        seq    = start_primer + fill + end_primer
        info   = (f"Sequence reconstructed from primers: "
                  f"{start_primer[:12]}...{end_primer[-12:]} ({len(seq)} bp)")
        return seq, info

    raise ValueError(
        "Provide either 'sequence' or both 'start_primer' and 'end_primer'."
    )


def compute_gc(seq: str) -> float:
    if not seq:
        return 0.0
    return sum(1 for b in seq if b in "GC") / len(seq) * 100


def entropy_conservation(seq: str, window: int = 10) -> np.ndarray:
    """Local conservation via Shannon entropy (1 = conserved, 0 = variable)."""
    n = len(seq)
    scores = np.zeros(n)
    for i in range(n):
        chunk = seq[max(0, i - window // 2): min(n, i + window // 2 + 1)]
        c = np.array([chunk.count(b) for b in "ATCG"], dtype=float)
        t = c.sum()
        if t > 0:
            p = c[c > 0] / t
            scores[i] = -np.sum(p * np.log2(p)) / 2.0
    return 1.0 - scores
