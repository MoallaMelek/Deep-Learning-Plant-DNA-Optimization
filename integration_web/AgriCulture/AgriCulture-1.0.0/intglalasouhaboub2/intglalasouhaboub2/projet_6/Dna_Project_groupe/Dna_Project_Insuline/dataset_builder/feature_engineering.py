"""Feature engineering for protein expression dataset."""

from dataclasses import dataclass
from typing import Dict

from src.codon_analysis import calculate_cai, calculate_gc_content, count_rare_codons
from src.codon_analysis import CODON_TO_AA


@dataclass(frozen=True)
class FeatureSet:
    cai: float
    gc_content: float
    gc_skew: float
    gc3_content: float
    at_content: float
    purine_content: float
    sequence_length_nt: int
    codon_count: int
    unique_codons: int
    codon_entropy: float
    effective_codon_fraction: float
    stop_codon_count: int
    invalid_codon_count: int
    repetitive_codon_ratio: float
    rare_codon_ratio: float


class FeatureEngineer:
    def __init__(self, rare_codon_threshold: float = 10.0) -> None:
        self.rare_codon_threshold = rare_codon_threshold

    def compute_features(self, dna_sequence: str, plant_host: str) -> FeatureSet:
        """
        Compute sequence-derived proxy features from a codon-optimized DNA sequence.

        Notes:
        - This method only uses sequence-derived heuristics.
        - Bounded ratios are clamped to [0, 1] for consistency.
        """
        cai = calculate_cai(dna_sequence, plant_host)
        gc_content = calculate_gc_content(dna_sequence)
        gc_skew = self._gc_skew(dna_sequence)
        gc3_content = self._gc3_content(dna_sequence)
        at_content = self._at_content(dna_sequence)
        purine_content = self._purine_content(dna_sequence)
        length_nt = len(dna_sequence)
        codon_bias = self._codon_bias_metrics(dna_sequence)
        effective_codon_fraction = self._effective_codon_fraction(codon_bias["entropy"])
        rare_info = count_rare_codons(dna_sequence, plant_host, threshold=self.rare_codon_threshold)
        rare_ratio = rare_info.get("rare_codon_percentage", 0.0) / 100.0
        stop_codon_count = self._stop_codon_count(dna_sequence)
        invalid_codon_count = self._invalid_codon_count(dna_sequence)
        repetitive_codon_ratio = self._repetitive_codon_ratio(dna_sequence)
        return FeatureSet(
            cai=_clip01(cai),
            gc_content=_clip01(gc_content),
            gc_skew=_clip_signed(gc_skew),
            gc3_content=_clip01(gc3_content),
            at_content=_clip01(at_content),
            purine_content=_clip01(purine_content),
            sequence_length_nt=length_nt,
            codon_count=codon_bias["codon_count"],
            unique_codons=codon_bias["unique_codons"],
            codon_entropy=codon_bias["entropy"],
            effective_codon_fraction=_clip01(effective_codon_fraction),
            stop_codon_count=stop_codon_count,
            invalid_codon_count=invalid_codon_count,
            repetitive_codon_ratio=_clip01(repetitive_codon_ratio),
            rare_codon_ratio=_clip01(round(rare_ratio, 4)),
        )

    def _codon_bias_metrics(self, dna_sequence: str) -> Dict[str, float]:
        if len(dna_sequence) % 3 != 0:
            return {"codon_count": 0, "unique_codons": 0, "entropy": 0.0}

        codons = [dna_sequence[i : i + 3].upper() for i in range(0, len(dna_sequence), 3)]
        counts: Dict[str, int] = {}
        for codon in codons:
            if codon in CODON_TO_AA:
                counts[codon] = counts.get(codon, 0) + 1

        total = sum(counts.values())
        if total == 0:
            return {"codon_count": 0, "unique_codons": 0, "entropy": 0.0}

        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * _log2(p)

        return {
            "codon_count": total,
            "unique_codons": len(counts),
            "entropy": round(entropy, 4),
        }

    def _gc3_content(self, dna_sequence: str) -> float:
        if len(dna_sequence) < 3 or len(dna_sequence) % 3 != 0:
            return 0.0
        third_bases = dna_sequence[2::3].upper()
        if not third_bases:
            return 0.0
        gc_count = third_bases.count("G") + third_bases.count("C")
        return round(gc_count / len(third_bases), 4)

    def _gc_skew(self, dna_sequence: str) -> float:
        if not dna_sequence:
            return 0.0
        seq = dna_sequence.upper()
        g_count = seq.count("G")
        c_count = seq.count("C")
        denominator = g_count + c_count
        if denominator == 0:
            return 0.0
        return round((g_count - c_count) / denominator, 4)

    def _at_content(self, dna_sequence: str) -> float:
        if not dna_sequence:
            return 0.0
        seq = dna_sequence.upper()
        at_count = seq.count("A") + seq.count("T")
        return round(at_count / len(seq), 4)

    def _purine_content(self, dna_sequence: str) -> float:
        if not dna_sequence:
            return 0.0
        seq = dna_sequence.upper()
        purine_count = seq.count("A") + seq.count("G")
        return round(purine_count / len(seq), 4)

    def _effective_codon_fraction(self, codon_entropy: float) -> float:
        if codon_entropy <= 0:
            return 0.0
        return round((2 ** codon_entropy) / 61.0, 4)

    def _stop_codon_count(self, dna_sequence: str) -> int:
        if len(dna_sequence) < 3:
            return 0
        codons = [dna_sequence[i : i + 3].upper() for i in range(0, len(dna_sequence), 3)]
        return sum(1 for codon in codons if CODON_TO_AA.get(codon) == "*")

    def _invalid_codon_count(self, dna_sequence: str) -> int:
        if len(dna_sequence) < 3:
            return 0
        codons = [dna_sequence[i : i + 3].upper() for i in range(0, len(dna_sequence), 3)]
        return sum(1 for codon in codons if codon not in CODON_TO_AA)

    def _repetitive_codon_ratio(self, dna_sequence: str) -> float:
        if len(dna_sequence) < 6 or len(dna_sequence) % 3 != 0:
            return 0.0
        codons = [dna_sequence[i : i + 3].upper() for i in range(0, len(dna_sequence), 3)]
        repeats = 0
        for i in range(1, len(codons)):
            if codons[i] == codons[i - 1]:
                repeats += 1
        return round(repeats / (len(codons) - 1), 4) if len(codons) > 1 else 0.0


def _log2(value: float) -> float:
    import math

    return math.log(value, 2)


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def _clip_signed(value: float) -> float:
    return max(-1.0, min(1.0, round(value, 4)))
