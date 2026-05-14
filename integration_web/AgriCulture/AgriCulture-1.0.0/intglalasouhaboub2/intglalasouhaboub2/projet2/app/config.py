from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models_weights"
TMP_FASTA_DIR = BASE_DIR / "tmp" / "fasta_output"

DATA_PATH = DATA_DIR / "finalfinal.csv"
GENOTYPE_PATH = DATA_DIR / "original_genotype_data.xlsx"

N_CLUSTERS = 5
TOP_N_PER_CLUSTER = 18
SEED = 42

TARGET_COLS = ["drought", "salt", "yield", "disease"]
CNN_COLS = ["snp_activity", "health_score_cnn", "leaf_surface_cnn", "plant_size_cnn"]

N_SIMULATIONS_DEFAULT = 1000
NOISE_STD = 0.05
THRESHOLDS = {"drought": 0.70, "salt": 0.65, "yield": 0.55, "disease": 0.75}
CV_STABLE = 10.0
CV_MODERATE = 20.0

WEIGHTS_DEFAULT = {"drought": 0.40, "salt": 0.30, "yield": 0.20, "disease": 0.10}
MODEL_WEIGHTS_DEFAULT = {"ridge": 0.2, "rf": 0.2, "xgb": 0.2, "lgbm": 0.2, "mlp": 0.2}

PROFILES = {
    "drought_max": {"drought": 0.5, "salt": 0.3, "yield": 0.1, "disease": 0.1},
    "yield_max": {"drought": 0.1, "salt": 0.1, "yield": 0.7, "disease": 0.1},
    "balanced": {"drought": 0.25, "salt": 0.25, "yield": 0.25, "disease": 0.25},
}

OLIGO_MIN_LEN = 25
OLIGO_MAX_LEN = 35
GC_OPTIMAL = (40, 60)
TM_OPTIMAL = (55, 65)
FLANKING_BP = 100
ENSEMBL_SPECIES = "triticum_turgidum"
TOP_N_SNPS_ODM = 10
TOP_N_PER_TRAIT = 5

MLP_ARCHITECTURE = {
    "layers": [256, 128, 64],
    "activation": "relu",
    "batch_norm": True,
}
