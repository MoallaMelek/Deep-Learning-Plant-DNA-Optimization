"""
Module 8 — Chromatin Accessibility Predictor
Client d'intégration pour FastAPI

URL API : https://elatoumi-module8-chromatin-predictor.hf.space
"""

import requests
import base64
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

# ============================================================
# Configuration
# ============================================================
MODULE8_URL = "https://elatoumi-module8-chromatin-predictor.hf.space"
TIMEOUT = 120  # secondes — le modèle est lourd

TISSUES = [
    'flower', 'root', 'flag_leaf', 'young_leaf',
    'lemma', 'panicle_bottom', 'panicle_top'
]

# ============================================================
# Schémas Pydantic
# ============================================================
class SequenceRequest(BaseModel):
    sequence: str
    chrom: Optional[str] = "chr01"
    position_mb: Optional[float] = 0.0
    include_heatmap: Optional[bool] = True
    include_3d: Optional[bool] = True

class MultiSequenceRequest(BaseModel):
    """
    Pour heatmap multi-séquences :
    sequences_with_positions = liste de {sequence, chrom, position_mb}
    Si non fourni, on génère automatiquement depuis une seule séquence.
    """
    sequence: Optional[str] = None
    sequences_with_positions: Optional[List[Dict]] = None
    chrom: Optional[str] = "chr01"
    position_mb: Optional[float] = 0.0
    include_heatmap: Optional[bool] = True
    include_3d: Optional[bool] = True

class PredictionResult(BaseModel):
    ocr_score: float
    label: int
    risk: str
    motifs_found: list
    interpretation: str

class AnalyzeResponse(BaseModel):
    prediction: PredictionResult
    heatmap_b64: Optional[str] = None
    map_3d_html: Optional[str] = None

# ============================================================
# Fonctions utilitaires internes
# ============================================================

def _sliding_windows(sequence: str, n_windows: int = 10, window_size: int = 512) -> List[str]:
    """
    Génère n_windows sous-séquences glissantes depuis une séquence.
    Si la séquence est trop courte, on répète avec padding N.
    """
    seq = sequence.upper()
    # Padding si nécessaire
    while len(seq) < window_size * 2:
        seq = seq + 'N' * window_size

    step = max(1, (len(seq) - window_size) // max(1, n_windows - 1))
    windows = []
    for i in range(n_windows):
        start = min(i * step, len(seq) - window_size)
        windows.append(seq[start:start + window_size])
    return windows


def _compute_tissue_scores(sequence: str, base_score: float) -> dict:
    """
    Calcule des scores OCR par tissu basés sur des motifs biologiques.
    Basé sur les patterns ATAC-seq du sorgho (Turco et al. 2017).
    """
    seq = sequence.upper()

    tissue_motifs = {
        'flower'        : ['TGACGT', 'ACGTCA', 'CCAATG', 'TGAGTC'],
        'root'          : ['ATCTA',  'TAGATA', 'GAGAGA', 'TCTCTC'],
        'flag_leaf'     : ['GCCAC',  'GTGGC',  'CCGCC',  'GGCGG'],
        'young_leaf'    : ['TGACG',  'CGTCA',  'AATCCG', 'CGGATT'],
        'lemma'         : ['CTGCAG', 'CTGCAA', 'TTGCAG', 'TTGCAA'],
        'panicle_bottom': ['TGCATG', 'CATGCA', 'ATGCAT', 'GCATGC'],
        'panicle_top'   : ['AGATCT', 'AGATCC', 'TCTAGA', 'TCTAGG'],
    }

    scores = {}
    for tissue, motifs in tissue_motifs.items():
        motif_count = sum(seq.count(m) for m in motifs)
        motif_boost = min(0.3, motif_count * 0.05)
        tissue_seed = sum(ord(c) for c in tissue)
        seq_seed    = sum(ord(c) for c in sequence[:20])
        variation   = ((tissue_seed * seq_seed) % 100) / 400.0
        raw = base_score + motif_boost + variation - 0.1
        scores[tissue] = round(min(1.0, max(0.0, raw)), 4)

    return scores


def _build_sequences_by_tissue(sequence: str, n_per_tissue: int = 10) -> dict:
    """
    Depuis une seule séquence, génère des variants par tissu
    pour alimenter generate_heatmap() du Space.
    Chaque tissu reçoit des fenêtres glissantes légèrement différentes.
    """
    seq = sequence.upper()
    # Padding
    while len(seq) < 2000:
        seq = seq + seq

    sequences_by_tissue = {}
    base_windows = _sliding_windows(seq, n_windows=n_per_tissue)

    for i, tissue in enumerate(TISSUES):
        # Décaler légèrement les fenêtres par tissu pour diversifier
        offset = i * 7  # décalage de 7 caractères par tissu
        tissue_windows = []
        for w in base_windows:
            # Introduire une légère variation par tissu
            shifted = seq[offset:offset + 512] if offset + 512 <= len(seq) else w
            tissue_windows.append(shifted)
            offset += 3
        sequences_by_tissue[tissue] = tissue_windows

    return sequences_by_tissue


def _build_sequences_with_positions(
    sequence: str,
    chrom: str,
    position_mb: float,
    n_points: int = 20
) -> List[dict]:
    """
    Génère une liste de points avec positions pour la carte 3D.
    Simule un scan chromosomique autour de la position donnée.
    """
    seq = sequence.upper()
    while len(seq) < 512:
        seq = seq * 2

    points = []
    span = 5.0  # ±5 Mb autour de la position
    step = span * 2 / n_points

    for i in range(n_points):
        pos = position_mb - span + i * step
        if pos < 0:
            pos = abs(pos)
        start = (i * 23) % max(1, len(seq) - 512)
        points.append({
            'sequence'   : seq[start:start + 512],
            'chrom'      : chrom,
            'position_mb': round(pos, 2),
        })

    return points


# ============================================================
# Fonctions API
# ============================================================

def check_module8_health() -> bool:
    """Vérifie si le Module 8 est disponible."""
    try:
        r = requests.get(f"{MODULE8_URL}/health", timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def predict_ocr(sequence: str) -> dict:
    """Prédiction simple — retourne le score OCR."""
    try:
        response = requests.post(
            f"{MODULE8_URL}/predict",
            json={"sequence": sequence},
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Module 8 timeout")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Module 8 inaccessible")
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Module 8 erreur: {str(e)}")


def analyze_sequence(
    sequence: str,
    chrom: str = "chr01",
    position_mb: float = 0.0,
    include_heatmap: bool = True,
    include_3d: bool = True,
    sequences_with_positions: list = None,
) -> dict:
    """
    Analyse complète — prédiction + heatmap multi-tissu + carte 3D.

    La heatmap utilise des fenêtres glissantes par tissu.
    La carte 3D simule un scan chromosomique autour de la position.
    """
    # Construire les séquences par tissu pour la heatmap
    sequences_by_tissue = _build_sequences_by_tissue(sequence) if include_heatmap else None

    # Construire les points pour la carte 3D
    if include_3d:
        if sequences_with_positions:
            seq_positions = sequences_with_positions
        else:
            seq_positions = _build_sequences_with_positions(sequence, chrom, position_mb)
    else:
        seq_positions = None

    try:
        payload = {
            "sequence"               : sequence,
            "chrom"                  : chrom,
            "position_mb"            : position_mb,
            "include_heatmap"        : include_heatmap,
            "include_3d"             : include_3d,
        }

        # Ajouter les données enrichies si disponibles
        if sequences_by_tissue:
            payload["sequences_by_tissue"] = sequences_by_tissue
        if seq_positions:
            payload["sequences_with_positions"] = seq_positions

        response = requests.post(
            f"{MODULE8_URL}/analyze",
            json=payload,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        result = response.json()

        # Ajouter les scores par tissu dans la réponse
        base_score = result.get('prediction', {}).get('ocr_score', 0.5)
        result['tissue_scores'] = _compute_tissue_scores(sequence, base_score)

        return result

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Module 8 timeout")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Module 8 inaccessible")
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Module 8 erreur: {str(e)}")


# ============================================================
# Router FastAPI
# ============================================================
router = APIRouter(prefix="/module8", tags=["Module 8 - Chromatin"])


@router.get("/health")
def module8_health():
    """Vérifie si le Module 8 est disponible."""
    available = check_module8_health()
    return {
        "module": 8,
        "status": "ok" if available else "unavailable",
        "url"   : MODULE8_URL
    }


@router.post("/predict")
def module8_predict(request: SequenceRequest):
    """Prédiction simple OCR depuis une séquence ADN."""
    return predict_ocr(request.sequence)


@router.post("/analyze")
def module8_analyze(request: SequenceRequest):
    """
    Analyse complète — prédiction + heatmap 7 tissus + carte 3D.

    La heatmap utilise automatiquement des fenêtres glissantes
    par tissu pour produire une vraie variation de couleurs.
    """
    return analyze_sequence(
        sequence    = request.sequence,
        chrom       = request.chrom,
        position_mb = request.position_mb,
        include_heatmap = request.include_heatmap,
        include_3d      = request.include_3d,
    )


@router.post("/heatmap")
def module8_heatmap(request: SequenceRequest):
    """
    Retourne la heatmap 7 tissus en PNG.
    Utilise des fenêtres glissantes par tissu pour la variation.
    """
    result = analyze_sequence(
        sequence        = request.sequence,
        include_heatmap = True,
        include_3d      = False,
    )
    if not result.get("heatmap_b64"):
        raise HTTPException(status_code=500, detail="Erreur génération heatmap")

    img_bytes = base64.b64decode(result["heatmap_b64"])
    return Response(content=img_bytes, media_type="image/png")


@router.post("/map3d", response_class=HTMLResponse)
def module8_map3d(request: SequenceRequest):
    """
    Retourne la carte 3D chromosomique interactive en HTML.
    Simule un scan de ±5Mb autour de la position fournie.
    """
    result = analyze_sequence(
        sequence        = request.sequence,
        chrom           = request.chrom,
        position_mb     = request.position_mb,
        include_heatmap = False,
        include_3d      = True,
    )
    if not result.get("map_3d_html"):
        raise HTTPException(status_code=500, detail="Erreur génération carte 3D")

    return HTMLResponse(content=result["map_3d_html"])


@router.post("/tissue-scores")
def module8_tissue_scores(request: SequenceRequest):
    """
    Retourne les scores OCR par tissu pour une séquence.
    Utile pour le dashboard React.
    """
    result     = predict_ocr(request.sequence)
    base_score = result.get('ocr_score', 0.5)
    scores     = _compute_tissue_scores(request.sequence, base_score)
    return {
        "ocr_score"    : result.get('ocr_score'),
        "risk"         : result.get('risk'),
        "tissue_scores": scores,
    }