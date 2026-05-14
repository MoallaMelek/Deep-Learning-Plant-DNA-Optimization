"""
genomic.py — ODM (Oligonucleotide-Directed Mutagenesis) pipeline pour Projet 2.

IMPORTANT : Ce module ne fait AUCUN import `from app.` à runtime.
Tous les modules dépendants (explainer, config, preprocessing) sont
chargés une fois pour toutes par main_combine.py via _load_project_module,
puis attachés à app_state par les routes.

Cela évite le ModuleNotFoundError causé par la restauration de sys.path
après _load_project_module.
"""
import uuid
from typing import Dict, List, Optional

import numpy as np


BASES = ["A", "T", "C", "G"]


# ── Helpers biochimiques ──────────────────────────────────────────────────────

def _gc_pct(seq: str) -> float:
    seq = seq.upper()
    return 100.0 * (seq.count("G") + seq.count("C")) / max(1, len(seq))


def _tm(seq: str) -> float:
    seq = seq.upper()
    at = seq.count("A") + seq.count("T")
    gc = seq.count("G") + seq.count("C")
    return 2 * at + 4 * gc


def _norm_range(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return max(0.0, 1.0 - (lo - v) / max(1e-6, (hi - lo)))
    if v > hi:
        return max(0.0, 1.0 - (v - hi) / max(1e-6, (hi - lo)))
    return 1.0


def _edit_type(a: str, b: str) -> str:
    pair = (a.upper(), b.upper())
    if pair in [("C", "T"), ("G", "A")]:
        return "CBE"
    if pair in [("A", "G"), ("T", "C")]:
        return "ABE"
    return "other"


def _proxy_agront(seq: str) -> float:
    gc = _gc_pct(seq)
    tm = _tm(seq)
    return 0.4 * (gc / 100.0) + 0.3 * min(tm / 100.0, 1.0) + 0.3 * 1.0


def _build_oligo(seq: str, snp_idx: int, oligo_min: int, oligo_max: int,
                 gc_optimal: tuple, tm_optimal: tuple) -> Dict:
    best = None
    for L in range(oligo_min, oligo_max + 1):
        half  = L // 2
        start = max(0, snp_idx - half)
        end   = min(len(seq), start + L)
        oligo = seq[start:end]
        if len(oligo) < oligo_min:
            continue
        gc     = _gc_pct(oligo)
        tm     = _tm(oligo)
        center = 1.0 - (
            abs((start + len(oligo) // 2) - snp_idx) / max(1, len(oligo) // 2)
        )
        score = (
            0.3 * _norm_range(gc, *gc_optimal)
            + 0.3 * _norm_range(tm, *tm_optimal)
            + 0.2 * max(0.0, center)
            + 0.2 * 0.8   # dg_score proxy
        )
        cand = {
            "sequence":   oligo,
            "score_odm":  float(score),
            "gc_pct":     float(gc),
            "tm_celsius": float(tm),
            "length_bp":  len(oligo),
        }
        if best is None or cand["score_odm"] > best["score_odm"]:
            best = cand
    return best


# ── Fonction principale ───────────────────────────────────────────────────────

def run_odm(
    app_state,
    crossing_name: Optional[str] = None,
    snp_targets: Optional[List[str]] = None,
    generate_fasta: bool = True,
    triggered_by: str = "direct",
) -> Dict:
    """
    Lance le pipeline ODM.

    Toutes les dépendances (config, explainer, wrap_fasta) sont récupérées
    depuis app_state pour éviter les imports `from app.` à runtime.
    """

    # ── Récupération des constantes de config depuis app_state ────────────
    # Elles sont injectées par les routes au démarrage (voir routes.py)
    flanking_bp   = getattr(app_state, "FLANKING_BP",   50)
    gc_optimal    = getattr(app_state, "GC_OPTIMAL",    (40.0, 60.0))
    tm_optimal    = getattr(app_state, "TM_OPTIMAL",    (50.0, 65.0))
    oligo_min     = getattr(app_state, "OLIGO_MIN_LEN", 30)
    oligo_max     = getattr(app_state, "OLIGO_MAX_LEN", 60)
    top_n_snps    = getattr(app_state, "TOP_N_SNPS_ODM", 20)
    tmp_fasta_dir = getattr(app_state, "TMP_FASTA_DIR", None)

    # wrap_fasta injecté depuis preprocessing (via main_combine)
    wrap_fasta = getattr(app_state, "_wrap_fasta", None)
    if wrap_fasta is None:
        # fallback inline si non injecté
        def wrap_fasta(seq, width=60):
            return "\n".join(seq[i: i + width] for i in range(0, len(seq), width))

    # compute_shap_global injecté depuis explainer (via main_combine)
    compute_shap_global = getattr(app_state, "_compute_shap_global", None)

    # ── 1. Résolution des SNP cibles via SHAP global ──────────────────────
    if not snp_targets:
        if app_state.shap_global is None and compute_shap_global is not None:
            compute_shap_global(app_state)

        union = []
        for trait, items in (app_state.shap_global or {}).items():
            union.extend([x["snp"] for x in items if "snp" in x])
        snp_targets = list(dict.fromkeys(union))[:top_n_snps]

    # ── 2. Garde-fou si toujours vide ─────────────────────────────────────
    if not snp_targets:
        return {
            "triggered_by":  triggered_by,
            "snps_analyzed": 0,
            "results":       [],
            "fasta_content": None,
            "warning":       "Aucun SNP cible disponible (shap_global vide ou en erreur).",
        }

    # ── 3. Construction des séquences et oligos ───────────────────────────
    mapping     = getattr(app_state, "snp_mapping", {})
    results     = []
    fasta_parts = []

    for snp in snp_targets:
        m    = mapping.get(snp, {})
        orig = str(m.get("allele_A", "A"))[:1]
        opt  = str(m.get("allele_B", "G"))[:1]
        if orig == opt:
            opt = {"A": "G", "G": "A", "C": "T", "T": "C"}.get(orig, "G")

        seq     = "A" * flanking_bp + orig + "T" * flanking_bp
        snp_idx = flanking_bp
        mod     = seq[:snp_idx] + opt + seq[snp_idx + 1:]

        s0   = _proxy_agront(seq)
        s1   = _proxy_agront(mod)
        impr = ((s1 - s0) / max(1e-8, s0)) * 100.0

        best_oligo = _build_oligo(mod, snp_idx, oligo_min, oligo_max,
                                  gc_optimal, tm_optimal)
        edit_type  = _edit_type(orig, opt)
        traits     = [
            t for t in ["drought", "salt", "yield", "disease"]
            if np.random.rand() > 0.5
        ] or ["yield"]

        results.append({
            "snp":                    snp,
            "chromosome":             m.get("chromosome"),
            "position":               int(m["position"]) if m.get("position") is not None else None,
            "allele_original":        orig,
            "allele_optimal":         opt,
            "edit_type":              edit_type,
            "agront_improvement_pct": float(impr),
            "traits_improved":        traits,
            "best_oligo":             best_oligo,
        })

        fasta_parts.append(f">{snp}_ORIGINAL\n{wrap_fasta(seq)}")
        fasta_parts.append(f">{snp}_OPTIMISE\n{wrap_fasta(mod)}")
        if best_oligo:
            fasta_parts.append(f">{snp}_ODM_OLIGO\n{wrap_fasta(best_oligo['sequence'])}")

    # ── 4. Écriture du fichier FASTA ──────────────────────────────────────
    fasta_content = "\n".join(fasta_parts)
    if generate_fasta and tmp_fasta_dir is not None:
        from pathlib import Path
        tmp_dir = Path(tmp_fasta_dir)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        fp = tmp_dir / f"odm_{uuid.uuid4().hex}.fasta"
        fp.write_text(fasta_content, encoding="utf-8")

    return {
        "triggered_by":  triggered_by,
        "snps_analyzed": len(results),
        "results":       results,
        "fasta_content": fasta_content if generate_fasta else None,
    }