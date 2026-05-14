from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent.parent
DATA_DIR        = BASE_DIR / "data"
MODELS_DIR      = BASE_DIR / "models_weights"
OUTPUT_DIR      = BASE_DIR / "outputs"
CACHE_DIR       = BASE_DIR / ".model_cache"

ODM_DATA_DIR    = DATA_DIR / "odm"
CRISPR_PATH     = ODM_DATA_DIR / "Luo2020_Kim2019.xlsx"
METHYLATION_BED = DATA_DIR / "wheat_methylation.bed"
RNASEQ_TPM_FILE = DATA_DIR / "wheat_rnaseq_tpm.tsv"

for d in [DATA_DIR, MODELS_DIR, OUTPUT_DIR, CACHE_DIR, ODM_DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Model registry ─────────────────────────────────────────────────────────
MODEL_REGISTRY = {
    "dnabert_6": "zhihan1996/DNA_bert_6",
    "dnabert_2": "zhihan1996/DNABERT-2",
    "nt_500m":   "InstaDeepAI/nucleotide-transformer-500m-human-ref",
    "nt_2500m":  "InstaDeepAI/nucleotide-transformer-2.5b-multi-species",
}
DEFAULT_MODEL_KEY = "dnabert_6"

# ── Agronomic objectives ────────────────────────────────────────────────────
OBJECTIVE_LABELS = {
    "disease_resistance":  "Résistance fongique (rouille, oïdium) — TaMLO, TaPR1",
    "yield_improvement":   "Amélioration rendement et poids des grains — TaGW2, TaGW5",
    "herbicide_tolerance": "Tolérance aux herbicides (SU, imidazolinone) — TaALS, TaACCase",
    "drought_tolerance":   "Tolérance à la sécheresse — TaDREB1, TaABF1",
    "starch_quality":      "Modification qualité amidon — TaWaxy, TaSSIIa",
}

# ── Pipeline defaults ───────────────────────────────────────────────────────
DEFAULT_MAX_CANDIDATES      = 20
DEFAULT_N_OLIGOS_PER_MUT    = 3
DEFAULT_TOP_N               = 10
DEFAULT_MAX_OFF_TARGET_RISK = 0.35
RNASEQ_MIN_TPM              = 1.0

SEED = 42
