"""Protein structural heuristics and AlphaFold integration utilities."""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any, Dict, Optional, Tuple

import requests

KYTE_DOOLITTLE: Dict[str, float] = {
    "A": 1.8,
    "C": 2.5,
    "D": -3.5,
    "E": -3.5,
    "F": 2.8,
    "G": -0.4,
    "H": -3.2,
    "I": 4.5,
    "K": -3.9,
    "L": 3.8,
    "M": 1.9,
    "N": -3.5,
    "P": -1.6,
    "Q": -3.5,
    "R": -4.5,
    "S": -0.8,
    "T": -0.7,
    "V": 4.2,
    "W": -0.9,
    "Y": -1.3,
}

HELIX_PROPENSITY: Dict[str, float] = {
    "A": 1.45,
    "C": 0.77,
    "D": 0.98,
    "E": 1.53,
    "F": 1.12,
    "G": 0.53,
    "H": 1.24,
    "I": 1.00,
    "K": 1.07,
    "L": 1.34,
    "M": 1.20,
    "N": 0.73,
    "P": 0.59,
    "Q": 1.17,
    "R": 0.79,
    "S": 0.79,
    "T": 0.82,
    "V": 1.14,
    "W": 1.14,
    "Y": 0.61,
}

SHEET_PROPENSITY: Dict[str, float] = {
    "A": 0.97,
    "C": 1.30,
    "D": 0.80,
    "E": 0.26,
    "F": 1.28,
    "G": 0.81,
    "H": 0.71,
    "I": 1.60,
    "K": 0.74,
    "L": 1.22,
    "M": 1.67,
    "N": 0.65,
    "P": 0.62,
    "Q": 1.23,
    "R": 0.90,
    "S": 0.72,
    "T": 1.20,
    "V": 1.65,
    "W": 1.19,
    "Y": 1.29,
}

AA_TO_THREE = {
    "A": "ALA",
    "C": "CYS",
    "D": "ASP",
    "E": "GLU",
    "F": "PHE",
    "G": "GLY",
    "H": "HIS",
    "I": "ILE",
    "K": "LYS",
    "L": "LEU",
    "M": "MET",
    "N": "ASN",
    "P": "PRO",
    "Q": "GLN",
    "R": "ARG",
    "S": "SER",
    "T": "THR",
    "V": "VAL",
    "W": "TRP",
    "Y": "TYR",
}

THREE_TO_ONE = {v: k for k, v in AA_TO_THREE.items()}

STABILIZING_AA = set("AVILMFWYC")
DESTABILIZING_AA = set("GPDENQKRST")


@dataclass(frozen=True)
class StructureAnnotation:
    helix_ratio: float
    sheet_ratio: float
    coil_ratio: float
    hydrophobicity_score: float
    stability_score: float
    protein_length: int
    pdb_url: str
    pdb_id: str
    structure_confidence: Optional[float]
    structure_source: str


class ProteinStructureAnnotator:
    """Annotate proteins with deterministic structural heuristics and AlphaFold links."""

    def __init__(
        self,
        use_alphafold: bool = True,
        timeout_sec: int = 20,
        max_retries: int = 2,
        user_agent: str = "dna-project-insuline/1.0",
    ) -> None:
        self.use_alphafold = use_alphafold
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        self.user_agent = user_agent
        self._cache: Dict[str, StructureAnnotation] = {}
        self._session = requests.Session()

    def annotate(self, accession: str, protein_sequence: str) -> StructureAnnotation:
        accession_key = accession.strip().upper()
        if accession_key in self._cache:
            return self._cache[accession_key]

        seq = _clean_sequence(protein_sequence)
        helix_ratio, sheet_ratio, coil_ratio = predict_secondary_structure_ratios(seq)
        hydrophobicity = mean_hydrophobicity_kd(seq)
        stability = composition_stability_score(seq)

        pdb_url = ""
        pdb_id = ""
        structure_confidence: Optional[float] = None
        structure_source = "mock"

        if self.use_alphafold and accession_key:
            af = self._fetch_alphafold(accession_key)
            if af:
                pdb_url = af.get("pdb_url", "")
                pdb_id = af.get("pdb_id", "")
                structure_confidence = af.get("structure_confidence")
                structure_source = "alphafold"

        if not pdb_id:
            pdb_id = f"MOCK-{accession_key or 'UNKNOWN'}"

        annotation = StructureAnnotation(
            helix_ratio=helix_ratio,
            sheet_ratio=sheet_ratio,
            coil_ratio=coil_ratio,
            hydrophobicity_score=hydrophobicity,
            stability_score=stability,
            protein_length=len(seq),
            pdb_url=pdb_url,
            pdb_id=pdb_id,
            structure_confidence=structure_confidence,
            structure_source=structure_source,
        )
        self._cache[accession_key] = annotation
        return annotation

    def _fetch_alphafold(self, accession: str) -> Optional[Dict[str, Any]]:
        payload = self._request_json(f"https://alphafold.ebi.ac.uk/api/prediction/{accession}")

        if isinstance(payload, list) and payload:
            entry = payload[0] if isinstance(payload[0], dict) else {}
            pdb_url = str(entry.get("pdbUrl") or "").strip()
            latest_version = entry.get("latestVersion")
            if not pdb_url and isinstance(latest_version, int):
                pdb_url = _alphafold_direct_url(accession, latest_version)

            pdb_id = str(entry.get("entryId") or f"AF-{accession}-F1").strip()
            confidence = _extract_confidence(entry)

            if pdb_url:
                return {
                    "pdb_url": pdb_url,
                    "pdb_id": pdb_id,
                    "structure_confidence": confidence,
                }

        for version in (4, 3, 2, 1):
            candidate = _alphafold_direct_url(accession, version)
            if self._url_exists(candidate):
                return {
                    "pdb_url": candidate,
                    "pdb_id": f"AF-{accession}-F1",
                    "structure_confidence": None,
                }

        return None

    def _request_json(self, url: str) -> Optional[Any]:
        headers = {"User-Agent": self.user_agent}
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._session.get(url, headers=headers, timeout=self.timeout_sec)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                try:
                    return response.json()
                except ValueError:
                    return None
            except requests.RequestException:
                if attempt < self.max_retries:
                    time.sleep(float(attempt))
        return None

    def _url_exists(self, url: str) -> bool:
        headers = {"User-Agent": self.user_agent}
        try:
            head = self._session.head(url, headers=headers, allow_redirects=True, timeout=self.timeout_sec)
            if head.status_code == 200:
                return True
            if head.status_code in (403, 405):
                probe = self._session.get(
                    url,
                    headers={**headers, "Range": "bytes=0-256"},
                    timeout=self.timeout_sec,
                )
                return probe.status_code in (200, 206)
        except requests.RequestException:
            return False
        return False


def predict_secondary_structure_ratios(protein_sequence: str) -> Tuple[float, float, float]:
    seq = _clean_sequence(protein_sequence)
    if not seq:
        return 0.0, 0.0, 0.0

    labels = []
    for index, _ in enumerate(seq):
        helix_score = _window_average(seq, index, HELIX_PROPENSITY, radius=2)
        sheet_score = _window_average(seq, index, SHEET_PROPENSITY, radius=2)

        if helix_score >= 1.03 and helix_score >= sheet_score + 0.08:
            labels.append("H")
        elif sheet_score >= 1.00 and sheet_score >= helix_score + 0.05:
            labels.append("E")
        else:
            labels.append("C")

    labels = _smooth_secondary_labels(labels)

    length = len(labels)
    helix_ratio = round(labels.count("H") / length, 4)
    sheet_ratio = round(labels.count("E") / length, 4)
    coil_ratio = round(max(0.0, 1.0 - helix_ratio - sheet_ratio), 4)
    return helix_ratio, sheet_ratio, coil_ratio


def mean_hydrophobicity_kd(protein_sequence: str) -> float:
    seq = _clean_sequence(protein_sequence)
    if not seq:
        return 0.0
    values = [KYTE_DOOLITTLE.get(aa, 0.0) for aa in seq]
    return round(sum(values) / len(values), 4)


def composition_stability_score(protein_sequence: str) -> float:
    seq = _clean_sequence(protein_sequence)
    if not seq:
        return 0.0

    length = len(seq)
    stabilizing_fraction = sum(1 for aa in seq if aa in STABILIZING_AA) / length
    destabilizing_fraction = sum(1 for aa in seq if aa in DESTABILIZING_AA) / length
    cysteine_fraction = seq.count("C") / length

    score = (
        0.7 * stabilizing_fraction
        + 0.2 * (1.0 - destabilizing_fraction)
        + 0.1 * min(cysteine_fraction * 4.0, 1.0)
    )
    return round(_clip(score, 0.0, 1.0), 4)


def generate_mock_pdb(protein_sequence: str, accession: str = "UNKNOWN") -> str:
    """Generate a deterministic alpha-helix-like fallback PDB from sequence."""
    seq = _clean_sequence(protein_sequence)
    if not seq:
        seq = "A"

    lines = [
        f"HEADER    MOCK STRUCTURE                           {accession[:20]}",
        "TITLE     DETERMINISTIC FALLBACK MODEL",
    ]

    radius = 4.4
    rise = 1.5
    angle_step_deg = 100.0

    for idx, aa in enumerate(seq, start=1):
        angle = math.radians((idx - 1) * angle_step_deg)
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        z = rise * (idx - 1)

        residue = AA_TO_THREE.get(aa, "ALA")
        bfactor = hydrophobicity_to_bfactor(KYTE_DOOLITTLE.get(aa, 0.0))

        atom_line = (
            f"ATOM  {idx:5d}  CA  {residue:>3s} A{idx:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00{bfactor:6.2f}           C"
        )
        lines.append(atom_line)

    lines.append("TER")
    lines.append("END")
    return "\n".join(lines) + "\n"


def generate_mock_pdb_from_length(protein_length: int, accession: str = "UNKNOWN") -> str:
    pattern = "ACDEFGHIKLMNPQRSTVWY"
    safe_length = max(1, int(protein_length))
    seq = "".join(pattern[i % len(pattern)] for i in range(safe_length))
    return generate_mock_pdb(seq, accession=accession)


def fetch_pdb_text(pdb_url: str, timeout_sec: int = 20) -> str:
    if not pdb_url:
        return ""
    try:
        response = requests.get(
            pdb_url,
            headers={"User-Agent": "dna-project-insuline/1.0"},
            timeout=timeout_sec,
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return ""


def apply_hydrophobicity_bfactor(pdb_text: str) -> str:
    if not pdb_text:
        return ""

    updated_lines = []
    for raw_line in pdb_text.splitlines():
        line = raw_line
        if (line.startswith("ATOM") or line.startswith("HETATM")) and len(line) >= 66:
            residue = line[17:20].strip().upper()
            aa = THREE_TO_ONE.get(residue, "A")
            kd_value = KYTE_DOOLITTLE.get(aa, 0.0)
            bfactor = hydrophobicity_to_bfactor(kd_value)
            line = f"{line[:60]}{bfactor:6.2f}{line[66:]}"
        updated_lines.append(line)

    return "\n".join(updated_lines) + "\n"


def hydrophobicity_to_bfactor(kd_value: float) -> float:
    return _clip(((kd_value + 4.5) / 9.0) * 100.0, 0.0, 100.0)


def _smooth_secondary_labels(labels: list[str]) -> list[str]:
    if len(labels) < 3:
        return labels

    smoothed = labels[:]
    for i in range(1, len(labels) - 1):
        left = labels[i - 1]
        center = labels[i]
        right = labels[i + 1]
        if center != left and center != right and left == right:
            smoothed[i] = left
    return smoothed


def _window_average(sequence: str, index: int, scale: Dict[str, float], radius: int = 2) -> float:
    start = max(0, index - radius)
    end = min(len(sequence), index + radius + 1)
    window = sequence[start:end]
    if not window:
        return 0.0
    values = [scale.get(aa, 1.0) for aa in window]
    return sum(values) / len(values)


def _clean_sequence(protein_sequence: str) -> str:
    sequence = (protein_sequence or "").strip().upper()
    return "".join(aa for aa in sequence if aa in KYTE_DOOLITTLE)


def _alphafold_direct_url(accession: str, version: int) -> str:
    return f"https://alphafold.ebi.ac.uk/files/AF-{accession}-F1-model_v{version}.pdb"


def _extract_confidence(entry: Dict[str, Any]) -> Optional[float]:
    for key in ("globalMetricValue", "confidenceScore", "ptm", "iptm", "plddt"):
        value = entry.get(key)
        if isinstance(value, (int, float)):
            return round(float(value), 4)
        if isinstance(value, dict):
            nested = value.get("value")
            if isinstance(nested, (int, float)):
                return round(float(nested), 4)
    return None


def _clip(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))
