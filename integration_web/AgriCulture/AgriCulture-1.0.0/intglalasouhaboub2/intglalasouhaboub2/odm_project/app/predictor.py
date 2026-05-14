"""
predictor.py — Central prediction logic for the ODM Wheat pipeline.

This module wires together:
  1. Functional sequence analysis  (DNABERT attention + motif detection)
  2. Mutation candidate generation  (scoring + filtering)
  3. ODM oligonucleotide design     (XGBoost scorer trained on CRISPR data)

It is intentionally stateless so it can be loaded once at startup and called
for every request without re-instantiating heavy models.
"""

from __future__ import annotations

import re
import random
import json
import numpy as np

from pathlib import Path
from typing import List, Optional

from Bio.Seq import Seq
from Bio.SeqUtils import MeltingTemp as mt
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
import xgboost as xgb

from app.config import SEED, DEFAULT_MAX_OFF_TARGET_RISK
from app.models.wheat import (
    BiologicalObjective,
    MutationCandidate,
    ODMOligonucleotide,
    WHEAT_OBJECTIVES,
)
from app.utils.preprocessing import compute_gc, entropy_conservation

random.seed(SEED)
np.random.seed(SEED)

# ── Regex motifs ────────────────────────────────────────────────────────────
MOTIFS = {
    "TATA_box":        r"TATA[AT]A[AT]",
    "CAAT_box":        r"CCAAT",
    "G_box":           r"CACGTG",
    "W_box":           r"TTGAC[CT]",
    "splice_donor":    r"GT[AG]AGT",
    "splice_acceptor": r"[CT]{10}AG",
    "start_codon":     r"ATG",
    "stop_codon":      r"(?:TAA|TAG|TGA)",
}

# ── Nearest-neighbour ΔG table ──────────────────────────────────────────────
NN_DG = {
    "AA": -1.0, "AT": -0.9, "AC": -1.3, "AG": -1.1,
    "TA": -0.6, "TT": -1.0, "TC": -1.1, "TG": -1.4,
    "CA": -1.4, "CT": -1.1, "CC": -1.8, "CG": -2.1,
    "GA": -1.1, "GT": -1.3, "GC": -2.1, "GG": -1.8,
}


# ──────────────────────────────────────────────────────────────────────────
# 1. Functional sequence analyser (no DNABERT — uses heuristics + motifs)
# ──────────────────────────────────────────────────────────────────────────

class FunctionalSequenceAnalyzer:
    """
    Analyses a DNA sequence and returns per-position importance scores
    together with region annotations and motif hits.

    When a trained DNABERT wrapper is available it is used for attention
    scores; otherwise a GC-complexity heuristic is used as a fallback so
    the API can operate without GPU / large model downloads.
    """

    def __init__(self, dnabert_wrapper=None):
        self.dnabert = dnabert_wrapper

    def analyze(
        self,
        seq: str,
        objective: BiologicalObjective,
        genomic_start: Optional[int] = None,
        seqname: str = "1A",
    ) -> dict:
        seq = seq.upper()
        n   = len(seq)

        attention    = self._attention(seq)
        motif_hits   = {k: [m.start() for m in re.finditer(p, seq)]
                        for k, p in MOTIFS.items()
                        if re.search(p, seq)}
        regions      = self._heuristic_regions(seq, motif_hits)
        conservation = entropy_conservation(seq)

        return {
            "sequence":            seq,
            "length":              n,
            "attention_scores":    attention,
            "motif_hits":          motif_hits,
            "region_annotations":  regions,
            "conservation_scores": conservation,
            "objective":           objective,
        }

    # ── internal ──────────────────────────────────────────────────────────

    def _attention(self, seq: str) -> np.ndarray:
        """Heuristic attention: GC-complexity + local entropy."""
        n      = len(seq)
        scores = np.zeros(n)
        w      = 10
        for i in range(n):
            chunk = seq[max(0, i - w): min(n, i + w + 1)]
            gc    = sum(1 for b in chunk if b in "GC") / len(chunk)
            # reward moderate GC (40-60%) + penalise homopolymers
            scores[i] = 1 - abs(gc - 0.5) * 2
            if len(set(chunk)) <= 2:
                scores[i] *= 0.5
        # add motif peaks
        for pattern in MOTIFS.values():
            for m in re.finditer(pattern, seq):
                s, e = m.start(), m.end()
                scores[s:e] = np.maximum(scores[s:e], 0.8)
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
        return scores

    def _heuristic_regions(self, seq: str, motif_hits: dict) -> list:
        regions = []
        atg  = [m.start() for m in re.finditer("ATG", seq)]
        stop = [m.start() for m in re.finditer(r"(?:TAA|TAG|TGA)", seq)]

        if atg:
            regions.append({
                "type": "promoter",
                "start": max(0, atg[0] - 200),
                "end": atg[0],
                "priority": "high",
                "source": "heuristic",
            })
        if atg and stop:
            for a in atg[:3]:
                sv = [x for x in stop if x > a and (x - a) % 3 == 0]
                if sv:
                    regions.append({
                        "type": "exon",
                        "start": a,
                        "end": sv[0] + 3,
                        "priority": "high",
                        "source": "heuristic",
                    })
        for p in motif_hits.get("splice_donor", []):
            regions.append({"type": "splice_donor",   "start": p, "end": p + 6,
                            "priority": "critical", "source": "motif"})
        for p in motif_hits.get("splice_acceptor", []):
            regions.append({"type": "splice_acceptor", "start": p, "end": p + 8,
                            "priority": "critical", "source": "motif"})
        return regions


# ──────────────────────────────────────────────────────────────────────────
# 2. Mutation candidate generator
# ──────────────────────────────────────────────────────────────────────────

_TRANSITIONS  = {"A": "G", "G": "A", "C": "T", "T": "C"}
_TRANSVERSIONS = {"A": ["C", "T"], "G": ["C", "T"], "C": ["A", "G"], "T": ["A", "G"]}


class MutationCandidateGenerator:
    def generate(
        self,
        analysis: dict,
        max_candidates: int = 20,
        threshold: float = 0.1,
    ) -> List[MutationCandidate]:
        seq  = analysis["sequence"]
        att  = analysis["attention_scores"]
        con  = analysis["conservation_scores"]
        obj  = analysis["objective"]
        regs = analysis["region_annotations"]

        region_boost = self._region_boost(seq, regs, obj)
        priority_map = att * 0.4 + region_boost * 0.4 + con * 0.2

        # adaptive threshold
        for thr in [threshold, 0.05, 0.01, 0.0]:
            positions = sorted(
                [i for i, s in enumerate(priority_map)
                 if s >= thr and seq[i] in "ATCG"],
                key=lambda i: priority_map[i],
                reverse=True,
            )[:max_candidates]
            if len(positions) >= 3:
                break

        candidates: List[MutationCandidate] = []
        for pos in positions:
            orig = seq[pos]
            mut_list = [("transition", _TRANSITIONS[orig])] + \
                       [("transversion", b) for b in _TRANSVERSIONS[orig]]
            for mut_type, mut_base in mut_list:
                mutated  = seq[:pos] + mut_base + seq[pos + 1:]
                impact   = self._cosine_impact(seq, mutated, pos)
                region   = self._region_at(pos, regs)
                effect   = self._predict_effect(seq, pos, orig, mut_base, region)
                risk     = min(
                    seq.count(seq[max(0, pos - 5): min(len(seq), pos + 6)]) / 10.0,
                    1.0,
                )
                brel = self._bio_relevance(
                    priority_map[pos], impact, effect, region, obj, float(con[pos])
                )
                cand = MutationCandidate(
                    position=pos,
                    original_base=orig,
                    mutant_base=mut_base,
                    mutation_type=mut_type,
                    functional_region=region,
                    conservation_score=float(con[pos]),
                    predicted_effect=effect,
                    biological_relevance=brel,
                    dnabert_attention=float(att[pos]),
                    off_target_risk=risk,
                )
                cand.final_score = round(brel * (1 - risk * 0.3), 4)
                candidates.append(cand)

        return sorted(candidates, key=lambda c: c.final_score, reverse=True)

    # ── internal ──────────────────────────────────────────────────────────

    def _cosine_impact(self, orig: str, mutated: str, pos: int,
                       window: int = 50) -> float:
        """GC-vector cosine distance as proxy for mutation impact."""
        c, e = max(0, pos - window), min(len(orig), pos + window)
        o_chunk = orig[c:e]
        m_chunk = mutated[c:e]

        def vec(s):
            return np.array([s.count(b) / len(s) for b in "ATCG"], dtype=float)

        ov, mv = vec(o_chunk), vec(m_chunk)
        cos    = np.dot(ov, mv) / (np.linalg.norm(ov) * np.linalg.norm(mv) + 1e-8)
        return round(float(1.0 - cos), 4)

    def _region_boost(self, seq: str, regions: list,
                      obj: BiologicalObjective) -> np.ndarray:
        b = np.zeros(len(seq))
        for r in regions:
            if r["type"] in obj.priority_regions:
                val = 0.4 if r.get("priority") == "critical" else 0.3
                b[r["start"]: r["end"]] = val
        return b

    def _region_at(self, pos: int, regions: list) -> str:
        for r in sorted(regions,
                        key=lambda r: 0 if r.get("priority") == "critical" else 1):
            if r["start"] <= pos <= r["end"]:
                return r["type"]
        return "intergenic"

    def _predict_effect(self, seq: str, pos: int, orig: str,
                        mut: str, region: str) -> str:
        if region == "promoter":
            return "regulatory"
        if "splice" in region:
            return "splicing_disruption"
        if region in ("exon", "CDS"):
            cp = pos % 3
            cs = pos - cp
            if cs + 3 <= len(seq):
                oc = seq[cs: cs + 3]
                mc = list(oc)
                mc[cp] = mut
                mc_str = "".join(mc)
                if mc_str in {"TAA", "TAG", "TGA"}:
                    return "nonsense"
                if oc == mc_str:
                    return "silent"
                return "missense"
        return "intergenic"

    def _bio_relevance(self, priority: float, impact: float, effect: str,
                       region: str, obj: BiologicalObjective,
                       conservation: float) -> float:
        lof_scores = {
            "nonsense": 0.9, "splicing_disruption": 0.85,
            "missense": 0.6, "regulatory": 0.5,
            "silent": 0.1,   "intergenic": 0.05,
        }
        score = impact * 0.30
        if obj.preferred_effect == "loss_of_function":
            score += lof_scores.get(effect, 0.1) * 0.35
        elif obj.preferred_effect == "gain_of_function":
            score += {"missense": 0.7, "regulatory": 0.6,
                      "nonsense": 0.1}.get(effect, 0.1) * 0.35
        else:
            score += lof_scores.get(effect, 0.1) * 0.20
        return round(min(score + conservation * 0.15 + priority * 0.10, 1.0), 4)


# ──────────────────────────────────────────────────────────────────────────
# 3. ODM Oligo Designer
# ──────────────────────────────────────────────────────────────────────────

class ODMOligoDesigner:
    LENS_STANDARD = [35, 40, 45, 50, 55]
    LENS_SHORT    = [15, 20, 25, 29]

    def __init__(self, crispr_df=None):
        self.scorer = self._train_scorer(crispr_df) if crispr_df is not None else None

    def design(
        self,
        sequence: str,
        mutation: MutationCandidate,
        n_results: int = 3,
    ) -> List[ODMOligonucleotide]:
        for lens, strict in [
            (self.LENS_STANDARD, True),
            (self.LENS_SHORT,    True),
            (self.LENS_STANDARD, False),
            (self.LENS_SHORT,    False),
        ]:
            result = self._design_with_lens(sequence, mutation, n_results, lens, strict)
            if result:
                return result
        return []

    # ── internal ──────────────────────────────────────────────────────────

    def _train_scorer(self, df) -> xgb.XGBRegressor:
        """Train XGBoost on CRISPR efficiency data."""
        rows = []
        sample = df.sample(min(5000, len(df)), random_state=SEED)
        for _, row in sample.iterrows():
            seq = str(row["sequence"])
            gc  = row["gc_pct"]
            try:
                tm = float(mt.Tm_Wallace(Seq(seq)))
            except Exception:
                tm = 2 * (len(seq) - gc / 100 * len(seq)) + 4 * (gc / 100 * len(seq))
            dg = sum(NN_DG.get(seq[i: i + 2], -1.0) for i in range(len(seq) - 1))
            ss = min(
                sum(1 for k in range(4, min(8, len(seq) // 2))
                    for i in range(len(seq) - k)
                    if seq[i: i + k] in str(Seq(seq).reverse_complement()))
                / (len(seq) * 2),
                1.0,
            )
            pam = float(row.get("has_pam", 0))
            rows.append([gc, tm, dg, ss, pam, len(seq) / 60.0, row["efficiency_norm"]])

        arr = np.array(rows)
        X, y = arr[:, :6], arr[:, 6]
        Xtr, Xva, ytr, yva = train_test_split(X, y, test_size=0.1, random_state=SEED)
        model = xgb.XGBRegressor(
            n_estimators=400, learning_rate=0.05,
            max_depth=6, random_state=SEED, verbosity=0,
        )
        model.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
        return model

    def _score_oligo(
        self, oligo_seq: str, length: int,
        mm_pos: int, mutation: MutationCandidate,
    ) -> ODMOligonucleotide:
        gc = compute_gc(oligo_seq)
        try:
            tm = float(mt.Tm_Wallace(Seq(oligo_seq)))
        except Exception:
            tm = 2 * (length - gc / 100 * length) + 4 * (gc / 100 * length)
        dg = sum(NN_DG.get(oligo_seq[i: i + 2], -1.0) for i in range(len(oligo_seq) - 1))
        ss = min(
            sum(1 for k in range(4, min(8, length // 2))
                for i in range(length - k)
                if oligo_seq[i: i + k] in str(Seq(oligo_seq).reverse_complement()))
            / (length * 2),
            1.0,
        )
        mmd = abs(mm_pos - length // 2) / length
        pam = 1.0 if oligo_seq[-2:] == "GG" else 0.0
        feat = np.array([[gc, tm, dg, ss, pam, length / 60.0]])

        if self.scorer is not None:
            pe = float(np.clip(self.scorer.predict(feat)[0] * 100, 0, 100))
        else:
            # simple heuristic when no CRISPR data provided
            pe = 40 + (10 if 40 <= gc <= 60 else 0) + (10 if 55 <= tm <= 72 else 0)

        sp = min(max(
            0.5 + (0.1 if 40 <= gc <= 60 else 0)
            + (0.15 if 55 <= tm <= 72 else 0)
            - ss * 0.3 - mmd * 0.2,
            0.05,
        ), 0.99)
        composite = (
            0.35 * pe
            + 0.25 * sp * 100
            + 0.20 * (1 - ss) * 100
            + 0.10 * (40 <= gc <= 60) * 100
            + 0.10 * (1 - mutation.off_target_risk) * 100
        )
        return ODMOligonucleotide(
            sequence=oligo_seq, mutation=mutation, length=length,
            gc_content=round(gc, 2), tm=round(tm, 2), delta_g=round(dg, 3),
            secondary_structure_score=round(ss, 4),
            off_target_risk=round(mutation.off_target_risk, 4),
            predicted_efficiency=round(pe, 2),
            predicted_success_prob=round(sp, 4),
            composite_score=round(composite, 2),
            mismatch_position=mm_pos,
        )

    def _ok(self, seq: str, strict: bool = True) -> bool:
        if re.search(r"[^ATCG]", seq):
            return False
        gc = compute_gc(seq)
        if strict:
            if re.search(r"(A{4}|T{4}|C{4}|G{4})", seq):
                return False
            return 25 <= gc <= 75
        else:
            if re.search(r"(A{5}|T{5}|C{5}|G{5})", seq):
                return False
            return 15 <= gc <= 85

    def _design_with_lens(
        self,
        sequence: str,
        mutation: MutationCandidate,
        n_results: int,
        lens: list,
        strict: bool,
    ) -> List[ODMOligonucleotide]:
        pos    = mutation.position
        oligos = []

        for length in lens:
            for strand in ["sense", "antisense"]:
                for offset in [0, -3, 3, -5, 5, -8, 8, -10, 10]:
                    start = pos - length // 2 + offset
                    end   = start + length
                    if start < 0 or end > len(sequence):
                        continue
                    oligo = list(sequence[start:end])
                    mm_p  = pos - start
                    if 0 <= mm_p < length:
                        oligo[mm_p] = mutation.mutant_base
                    os_ = "".join(oligo)
                    if strand == "antisense":
                        os_  = str(Seq(os_).reverse_complement())
                        mm_p = length - mm_p - 1
                    if not self._ok(os_, strict=strict):
                        continue
                    try:
                        scored       = self._score_oligo(os_, length, mm_p, mutation)
                        scored.strand = strand
                        oligos.append(scored)
                    except Exception:
                        continue

        seen: List[str] = []
        unique: List[ODMOligonucleotide] = []
        for o in sorted(oligos, key=lambda x: x.composite_score, reverse=True):
            if o.sequence not in seen:
                seen.append(o.sequence)
                unique.append(o)
            if len(unique) >= n_results:
                break
        return unique


# ──────────────────────────────────────────────────────────────────────────
# Top-level predictor (singleton-friendly)
# ──────────────────────────────────────────────────────────────────────────

class ODMPredictor:
    """
    Orchestrates the full ODM pipeline:
    analyse → generate mutations → design oligos.
    """

    def __init__(self, crispr_df=None, dnabert_wrapper=None):
        self.analyzer = FunctionalSequenceAnalyzer(dnabert_wrapper)
        self.mut_gen  = MutationCandidateGenerator()
        self.designer = ODMOligoDesigner(crispr_df)

    def predict(
        self,
        sequence: str,
        objective_key: str,
        max_candidates: int = 20,
        n_oligos_per_mut: int = 3,
        top_n: int = 10,
        max_off_target_risk: float = DEFAULT_MAX_OFF_TARGET_RISK,
        genomic_start: Optional[int] = None,
        genomic_chrom: str = "1A",
    ) -> dict:
        objective = WHEAT_OBJECTIVES[objective_key]

        # Step 1 — functional analysis
        analysis = self.analyzer.analyze(
            sequence, objective, genomic_start, genomic_chrom
        )

        # Step 2 — mutation candidates
        mutations = self.mut_gen.generate(analysis, max_candidates=max_candidates)
        mutations = [m for m in mutations if m.off_target_risk <= max_off_target_risk]

        if not mutations:
            return {
                "status": "no_mutations",
                "message": "No mutation candidates passed the filters.",
                "results": [],
                "summary": {},
            }

        # Step 3 — oligo design
        all_oligos: List[ODMOligonucleotide] = []
        for mut in mutations[:top_n]:
            all_oligos.extend(
                self.designer.design(sequence, mut, n_results=n_oligos_per_mut)
            )

        all_oligos.sort(key=lambda o: o.composite_score, reverse=True)

        # Build result rows
        rows = []
        for rank, o in enumerate(all_oligos[:top_n * 2], 1):
            m = o.mutation
            rows.append({
                "rank":                rank,
                "oligo_sequence":      o.sequence,
                "oligo_length":        o.length,
                "strand":              o.strand,
                "mutation":            f"{m.original_base}{m.position}{m.mutant_base}",
                "position":            m.position,
                "predicted_effect":    m.predicted_effect,
                "functional_region":   m.functional_region,
                "gc_pct":              o.gc_content,
                "tm_celsius":          o.tm,
                "delta_g":             o.delta_g,
                "off_target_risk":     o.off_target_risk,
                "predicted_efficiency_pct": o.predicted_efficiency,
                "success_probability": o.predicted_success_prob,
                "odm_score":           o.composite_score,
                "mutation_score":      m.final_score,
                "global_score":        round(o.composite_score * 0.6 + m.final_score * 100 * 0.4, 2),
            })

        rows.sort(key=lambda r: r["global_score"], reverse=True)
        best = rows[0] if rows else {}

        return {
            "status":   "success",
            "objective": objective_key,
            "sequence_length": len(sequence),
            "n_mutations_evaluated": len(mutations),
            "n_oligos_designed":     len(all_oligos),
            "results":  rows[:top_n],
            "summary": {
                "best_mutation":             best.get("mutation"),
                "best_oligo":               best.get("oligo_sequence"),
                "best_global_score":        best.get("global_score"),
                "best_predicted_effect":    best.get("predicted_effect"),
                "best_gc_pct":              best.get("gc_pct"),
                "best_tm":                  best.get("tm_celsius"),
                "best_success_probability": best.get("success_probability"),
            },
        }
