from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from Bio.Seq import Seq


STOP_CODONS = {"TAA", "TAG", "TGA"}


def normalize_sequence(sequence: str) -> str:
    return "".join(base for base in sequence.upper() if base in {"A", "T", "G", "C"})


def gc_content(sequence: str) -> float:
    if not sequence:
        return 0.0
    gc_count = sum(1 for base in sequence if base in {"G", "C"})
    return round((gc_count / len(sequence)) * 100, 2)


def find_orfs(sequence: str, min_codon_length: int = 20) -> list[dict[str, Any]]:
    orfs: list[dict[str, Any]] = []
    for frame in range(3):
        start = None
        for i in range(frame, len(sequence) - 2, 3):
            codon = sequence[i : i + 3]
            if codon == "ATG" and start is None:
                start = i
            elif codon in STOP_CODONS and start is not None:
                codon_span = (i + 3 - start) // 3
                if codon_span >= min_codon_length:
                    nuc_seq = sequence[start : i + 3]
                    orfs.append(
                        {
                            "frame": frame + 1,
                            "start": start,
                            "end": i + 3,
                            "length_bp": i + 3 - start,
                            "protein": str(Seq(nuc_seq).translate(to_stop=True)),
                        }
                    )
                start = None
    return orfs


def detect_motifs(sequence: str, motifs: list[str] | None = None) -> dict[str, list[int]]:
    motifs = motifs or ["TATA", "AATAAA", "CACGTG", "GGATCC"]
    results: dict[str, list[int]] = {}
    for motif in motifs:
        positions = [i for i in range(len(sequence) - len(motif) + 1) if sequence[i : i + len(motif)] == motif]
        if positions:
            results[motif] = positions
    return results


def protein_translation(sequence: str) -> str:
    if len(sequence) < 3:
        return ""
    trimmed = sequence[: len(sequence) - (len(sequence) % 3)]
    return str(Seq(trimmed).translate())


@dataclass(slots=True)
class DNAAnalysisResult:
    normalized_sequence: str
    gc_percent: float
    orfs: list[dict[str, Any]]
    motifs: dict[str, list[int]]
    protein_translation: str
    figure_paths: list[str]


class DNAAnalyzer:
    def analyze(self, sequence: str, output_dir: Path) -> DNAAnalysisResult:
        sequence = normalize_sequence(sequence)
        output_dir.mkdir(parents=True, exist_ok=True)
        gc = gc_content(sequence)
        orfs = find_orfs(sequence)
        motifs = detect_motifs(sequence)
        protein = protein_translation(sequence)
        figs = self._generate_figures(sequence, orfs, output_dir)
        return DNAAnalysisResult(
            normalized_sequence=sequence,
            gc_percent=gc,
            orfs=orfs,
            motifs=motifs,
            protein_translation=protein,
            figure_paths=figs,
        )

    def _generate_figures(self, sequence: str, orfs: list[dict[str, Any]], output_dir: Path) -> list[str]:
        figure_paths: list[str] = []
        if sequence:
            window = max(10, len(sequence) // 8)
            xs = list(range(0, len(sequence), window))
            ys = [gc_content(sequence[i : i + window]) for i in xs]
            plt.figure(figsize=(8, 3.5))
            plt.plot(xs, ys, marker="o")
            plt.title("GC Content Profile")
            plt.xlabel("Sequence Position")
            plt.ylabel("GC%")
            plt.tight_layout()
            gc_path = output_dir / "gc_profile.png"
            plt.savefig(gc_path, dpi=160)
            plt.close()
            figure_paths.append(str(gc_path))

        if sequence:
            plt.figure(figsize=(8, 1.8))
            plt.hlines(y=1, xmin=0, xmax=len(sequence), linewidth=2)
            for orf in orfs:
                plt.hlines(y=1, xmin=orf["start"], xmax=orf["end"], linewidth=7)
            plt.title("ORF Map")
            plt.yticks([])
            plt.xlabel("Nucleotide Position")
            plt.tight_layout()
            orf_path = output_dir / "orf_map.png"
            plt.savefig(orf_path, dpi=160)
            plt.close()
            figure_paths.append(str(orf_path))
        return figure_paths

