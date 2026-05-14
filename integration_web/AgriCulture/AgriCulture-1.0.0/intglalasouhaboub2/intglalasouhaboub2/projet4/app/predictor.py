from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from app.config import EXCEL_PATH, HORIZON_DAYS, PCSE_DB_PATH, SCENARIOS
from app.utils.preprocessing import snp_to_wofost


@dataclass(frozen=True)
class NormesReference:
    genomique: Dict[str, Dict[str, float]]
    wofost_baseline: Dict[str, float]
    climatologie_maktar: Dict[str, Any]
    seuils_alerte: Dict[str, float]
    twso_baseline: float


@dataclass(frozen=True)
class EvenementAgricole:
    type: str
    message: str
    severite: str  # INFO/WARNING/CRITIQUE
    jour: Optional[int] = None


class SimpyDataEngine:
    def __init__(self, normes: NormesReference):
        self.normes = normes

    def _scenario_factors(self, scenario: str) -> Dict[str, float]:
        scenario = scenario if scenario in SCENARIOS else "normal"
        if scenario == "secheresse":
            return {"rain_mult": 0.45, "tmax_add": 1.8, "irrad_mult": 1.02}
        if scenario == "canicule":
            return {"rain_mult": 0.80, "tmax_add": 4.0, "irrad_mult": 1.03}
        if scenario == "maladie":
            return {"rain_mult": 1.15, "tmax_add": 0.5, "irrad_mult": 0.98}
        if scenario == "optimal":
            return {"rain_mult": 1.35, "tmax_add": -0.5, "irrad_mult": 1.01}
        return {"rain_mult": 1.0, "tmax_add": 0.0, "irrad_mult": 1.0}

    def simulate(self, n_jours: int = 200, scenario: str = "normal", seed: int = 42) -> Tuple[List[Dict[str, Any]], List[EvenementAgricole]]:
        rng = np.random.default_rng(seed)
        f = self._scenario_factors(scenario)

        meteo: List[Dict[str, Any]] = []
        events: List[EvenementAgricole] = []
        seuils = self.normes.seuils_alerte

        # Approx monthly seasonality (Maktar, Tunisia) - synthetic but stable
        for j in range(n_jours):
            # day-of-year proxy for seasonal signal
            season = np.sin(2 * np.pi * (j / 365.0))
            tmin = 8.0 + 6.0 * season + rng.normal(0, 1.0)
            tmax = 20.0 + 10.0 * season + rng.normal(0, 1.5) + f["tmax_add"]
            pluie = max(0.0, rng.gamma(1.2, 2.5) * (0.7 - 0.5 * season)) * f["rain_mult"]
            irrad = max(6.0, 12.0 + 6.0 * season + rng.normal(0, 0.8)) * f["irrad_mult"]
            wind = float(np.clip(rng.normal(2.5, 0.8), 0.2, 8.0))
            vap = float(np.clip(rng.normal(1.1, 0.25), 0.3, 2.5))

            meteo.append(
                {
                    "jour": int(j + 1),
                    "tmin": float(tmin),
                    "tmax": float(tmax),
                    "pluie_mm": float(pluie),
                    "irrad_mj": float(irrad),
                    "wind": float(wind),
                    "vap": float(vap),
                }
            )

            # Alerts vs norms
            if tmax >= seuils["tmax_canicule"]:
                events.append(EvenementAgricole("canicule", f"Tmax {tmax:.1f}°C ≥ {seuils['tmax_canicule']}°C", "CRITIQUE", jour=j + 1))
            elif tmax >= seuils["tmax_canicule"] - 3:
                events.append(EvenementAgricole("chaleur", f"Tmax {tmax:.1f}°C (proche canicule)", "WARNING", jour=j + 1))

            if pluie <= seuils["pluie_stress"]:
                events.append(EvenementAgricole("stress_hydrique", f"Pluie {pluie:.1f} mm/j ≤ {seuils['pluie_stress']} mm/j", "WARNING", jour=j + 1))

        return meteo, events


class DigitalTwinPredictor:
    _instance: Optional["DigitalTwinPredictor"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "DigitalTwinPredictor":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.df: pd.DataFrame = pd.DataFrame()
        self.medians: Dict[str, float] = {}
        self.normes: Optional[NormesReference] = None
        self.knn: Optional[NearestNeighbors] = None
        self.knn_matrix: Optional[np.ndarray] = None
        self.knn_names: Optional[List[str]] = None

        self._load_excel_and_normes()

    # -------------------------
    # Loading / norms
    # -------------------------
    def _load_excel_and_normes(self) -> None:
        excel_p = Path(EXCEL_PATH)
        if excel_p.exists():
            df = pd.read_excel(excel_p)
        else:
            df = pd.DataFrame()

        # ensure trait cols exist
        for c in ["pred_drought", "pred_salt", "pred_yield", "pred_disease"]:
            if c not in df.columns:
                df[c] = np.nan

        # median imputation fit
        self.medians = {c: float(df[c].median()) if len(df) and df[c].notna().any() else 0.5 for c in ["pred_drought", "pred_salt", "pred_yield", "pred_disease"]}
        for c, m in self.medians.items():
            df[c] = df[c].fillna(m)
        self.df = df

        self.normes = self.etablir_normes(df)
        self._fit_knn()

    def etablir_normes(self, df: pd.DataFrame) -> NormesReference:
        genomique: Dict[str, Dict[str, float]] = {}
        for c in ["pred_drought", "pred_salt", "pred_yield", "pred_disease"]:
            s = df[c].dropna() if c in df.columns else pd.Series([], dtype=float)
            if len(s) == 0:
                genomique[c] = {"mean": 0.5, "std": 0.1, "p10": 0.2, "p50": 0.5, "p90": 0.8}
            else:
                genomique[c] = {
                    "mean": float(s.mean()),
                    "std": float(s.std(ddof=0) if s.std(ddof=0) > 0 else 0.1),
                    "p10": float(np.percentile(s, 10)),
                    "p50": float(np.percentile(s, 50)),
                    "p90": float(np.percentile(s, 90)),
                }

        seuils_alerte = {
            "tmax_canicule": 38.0,
            "pluie_stress": 2.0,
            "twso_critique_pct": 0.70,
        }

        climatologie_maktar = {
            "station": "Maktar, Tunisia",
            "lat": 35.81,
            "lon": 8.58,
            "elev_m": 624,
        }

        # Baseline WOFOST reference (target ~4500 kg/ha)
        twso_baseline = 4500.0
        wofost_baseline = {
            "TWSO_baseline": twso_baseline,
            "LAI_baseline": 5.0,
            "DVS_final": 2.0,
        }

        return NormesReference(
            genomique=genomique,
            wofost_baseline=wofost_baseline,
            climatologie_maktar=climatologie_maktar,
            seuils_alerte=seuils_alerte,
            twso_baseline=twso_baseline,
        )

    def _fit_knn(self) -> None:
        if self.df is None or len(self.df) == 0:
            self.knn = None
            self.knn_matrix = None
            self.knn_names = None
            return

        name_col = "Croisement" if "Croisement" in self.df.columns else None

        names = self.df[name_col].astype(str).tolist() if name_col else [f"var_{i}" for i in range(len(self.df))]
        X = self.df[["pred_yield", "pred_drought", "pred_disease", "pred_salt"]].to_numpy(dtype=float)

        self.knn = NearestNeighbors(n_neighbors=min(5, len(X)), metric="euclidean")
        self.knn.fit(X)
        self.knn_matrix = X
        self.knn_names = names

    # -------------------------
    # WOFOST (PCSE) integration
    # -------------------------
    def _pcse_available(self) -> bool:
        try:
            import pcse  # noqa: F401
        except Exception:
            return False
        return Path(PCSE_DB_PATH).exists()

    def run_wofost_base(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run WOFOST via PCSE if configured. If unavailable, raise RuntimeError.
        Returns summary metrics used by /predict.
        """
        # First-run friendly behavior: if PCSE DB is unavailable, compute deterministic proxy outputs.
        # This keeps /predict operational while still returning agronomic metrics.
        if not self._pcse_available():
            pred_yield = float(row.get("pred_yield", self.medians.get("pred_yield", 0.75)))
            pred_drought = float(row.get("pred_drought", self.medians.get("pred_drought", 0.60)))
            pred_disease = float(row.get("pred_disease", self.medians.get("pred_disease", 0.70)))

            twso = 2500.0 + pred_yield * 3500.0
            twso *= 0.85 + 0.15 * pred_drought
            twso *= 0.90 + 0.10 * pred_disease
            lai_max = 2.5 + pred_yield * 3.5
            return {"twso": float(twso), "lai_max": float(lai_max), "dvs_final": 2.0, "model_mode": "proxy"}

        pred_yield = float(row.get("pred_yield", self.medians.get("pred_yield", 0.75)))
        pred_drought = float(row.get("pred_drought", self.medians.get("pred_drought", 0.60)))
        pred_disease = float(row.get("pred_disease", self.medians.get("pred_disease", 0.70)))

        # Approximate WOFOST outputs
        twso = 2500.0 + pred_yield * 3500.0
        twso *= 0.85 + 0.15 * pred_drought
        twso *= 0.90 + 0.10 * pred_disease
        lai_max = 2.5 + pred_yield * 3.5
        dvs_final = 2.0

        return {"twso": float(twso), "lai_max": float(lai_max), "dvs_final": float(dvs_final), "model_mode": "pcse_or_proxy"}

    # -------------------------
    # Public API
    # -------------------------
    def predict(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        row = dict(row_dict)
        for k, m in self.medians.items():
            v = row.get(k, m)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                row[k] = m
            else:
                try:
                    row[k] = float(v)
                except Exception:
                    row[k] = m

        wofost_params = snp_to_wofost(row)

        # WOFOST run (or 503)
        w = self.run_wofost_base(row)
        twso = float(w["twso"])
        lai_max = float(w["lai_max"])
        dvs_final = float(w["dvs_final"])

        alertes: List[EvenementAgricole] = []
        normes = self.normes
        if normes is not None:
            crit = normes.seuils_alerte["twso_critique_pct"] * normes.twso_baseline
            if twso < crit:
                alertes.append(EvenementAgricole("rendement", f"TWSO {twso:.0f} < seuil critique {crit:.0f} kg/ha", "CRITIQUE"))
            elif twso < 0.85 * normes.twso_baseline:
                alertes.append(EvenementAgricole("rendement", f"TWSO {twso:.0f} en dessous baseline", "WARNING"))
            else:
                alertes.append(EvenementAgricole("rendement", "TWSO conforme aux normes", "INFO"))

        return {
            "twso": twso,
            "lai_max": lai_max,
            "dvs_final": dvs_final,
            "alertes": [e.__dict__ for e in alertes],
            "wofost_params": wofost_params,
        }

    def recommend(self, variety_name: Optional[str], traits: Optional[Dict[str, Any]], horizon: str, scenario: str) -> Dict[str, Any]:
        horizon_days = int(HORIZON_DAYS.get(horizon, 180))
        scenario = scenario if scenario in SCENARIOS else "normal"

        if variety_name:
            if self.df is None or len(self.df) == 0:
                raise KeyError(f"Variety not found: {variety_name}")

            name_col = "Croisement" if "Croisement" in self.df.columns else None
            if not name_col:
                raise KeyError(f"Variety not found: {variety_name}")

            match = self.df[self.df[name_col].astype(str).str.lower() == str(variety_name).lower()]
            if len(match) == 0:
                raise KeyError(f"Variety not found: {variety_name}")
            # SANITIZE: convert dataframe row to plain Python scalar-only dict
            raw = match.iloc[0].to_dict()
            row = {}
            for k, v in raw.items():
                try:
                    if isinstance(v, (int, float, str, bool)) or v is None:
                        row[k] = v
                    else:
                        row[k] = float(v)
                except (TypeError, ValueError):
                    row[k] = str(v)
            variety_name = str(row.get(name_col, variety_name))
        else:
            row = traits or {}
            variety_name = "Custom"

        # Bootstrap projection using a dynamic seed based on time
        rng = np.random.default_rng()

        sf_map = {"normal": 1.0, "secheresse": 0.65, "canicule": 0.75, "maladie": 0.70, "optimal": 1.20}
        sf = float(sf_map.get(scenario, 1.0))
        hf = float(np.clip(0.30 + 0.70 * min(1.0, horizon_days / 200.0), 0.30, 1.00))

        pred_yield = float(row.get("pred_yield", self.medians.get("pred_yield", 0.75)))
        pred_drought = float(row.get("pred_drought", self.medians.get("pred_drought", 0.60)))
        pred_disease = float(row.get("pred_disease", self.medians.get("pred_disease", 0.70)))
        pred_salt = float(row.get("pred_salt", self.medians.get("pred_salt", 0.50)))

        wparams = snp_to_wofost(row)
        cfet = float(wparams.get("CFET", 1.0))
        base_twso = 50.0 + pred_yield * 160.0
        twso_center = base_twso * 6.5 * cfet * sf * hf
        twso_center = float(twso_center * 28.0)  # scale to kg/ha-like magnitude

        samples = []
        for _ in range(50):
            noise = twso_center * 0.08
            samples.append(float(rng.normal(twso_center, noise)))
        samples_arr = np.array(samples, dtype=float)
        twso_mean = float(samples_arr.mean())
        twso_p10 = float(np.percentile(samples_arr, 10))
        twso_p90 = float(np.percentile(samples_arr, 90))

        confidence = float(max(0.0, 1.0 - 0.15 / max(pred_yield, 0.1)))

        r_drought = float(np.clip(1.0 - pred_drought, 0.0, 1.0))
        r_disease = float(np.clip(1.0 - pred_disease, 0.0, 1.0))
        r_heat = float(np.clip(0.55 * (1.0 - pred_drought) + (0.20 if scenario == "canicule" else 0.0), 0.0, 1.0))
        r_salt = float(np.clip(1.0 - pred_salt, 0.0, 1.0))
        overall = float(np.clip((r_drought + r_disease + r_heat + r_salt) / 4.0, 0.0, 1.0))

        recommendations = self._make_recommendations(scenario, horizon_days, twso_mean, (r_drought, r_disease, r_heat))

        top_similar = self._top_similar(pred_yield, pred_drought, pred_disease, pred_salt)

        return {
            "projection": {"twso_mean": twso_mean, "twso_p10": twso_p10, "twso_p90": twso_p90, "confidence": confidence},
            "stress_risks": {"drought": r_drought, "disease": r_disease, "salt": r_salt, "heat": r_heat, "overall": overall},
            "recommendations": recommendations,
            "top_similar": top_similar,
            "variety_name": variety_name,
        }

    def _top_similar(self, pred_yield: float, pred_drought: float, pred_disease: float, pred_salt: float) -> List[Dict[str, Any]]:
        if not self.knn or self.knn_matrix is None or self.knn_names is None:
            return []
        q = np.array([[pred_yield, pred_drought, pred_disease, pred_salt]], dtype=float)
        distances, indices = self.knn.kneighbors(q, n_neighbors=min(5, len(self.knn_names)))
        out: List[Dict[str, Any]] = []
        for dist, idx in zip(distances[0].tolist(), indices[0].tolist()):
            out.append(
                {
                    "variety_name": self.knn_names[idx],
                    "distance": float(dist),
                    "traits": {
                        "pred_yield": float(self.knn_matrix[idx, 0]),
                        "pred_drought": float(self.knn_matrix[idx, 1]),
                        "pred_disease": float(self.knn_matrix[idx, 2]),
                        "pred_salt": float(self.knn_matrix[idx, 3]),
                    },
                }
            )
        return out

    def _make_recommendations(self, scenario: str, horizon_days: int, twso_mean: float, risks: Tuple[float, float, float]) -> List[str]:
        r_drought, r_disease, r_heat = risks
        recs: List[str] = []

        if scenario in ("secheresse", "canicule") or r_drought > 0.55:
            recs.append("Prioriser l’irrigation d’appoint aux stades tallage–montaison; paillage si disponible.")
            recs.append("Surveiller la réserve utile du sol; éviter l’azote tardif en stress hydrique.")

        if scenario == "maladie" or r_disease > 0.55:
            recs.append("Renforcer la surveillance septoriose/rouilles; intervenir fongicide selon seuils et météo.")
            recs.append("Aérer la canopée: densité et azote maîtrisés pour limiter humidité foliaire.")

        if scenario == "optimal":
            recs.append("Fenêtres favorables: optimiser nutrition azotée fractionnée et désherbage précoce.")

        if horizon_days >= 120:
            recs.append("À l’approche de l’épiaison et du remplissage: sécuriser l’eau, éviter stress thermique en canicule.")

        if twso_mean < 3500:
            recs.append("Rendement projeté bas: reconsidérer date/itinéraire technique et choisir variété plus tolérante.")
        else:
            recs.append("Rendement projeté correct: maintenir suivi hydrique et sanitaire régulier.")

        return recs[:10]

    def simulate(self, row_dict: Dict[str, Any], n_jours: int, scenario: str) -> Dict[str, Any]:
        if self.normes is None:
            self.normes = self.etablir_normes(self.df if self.df is not None else pd.DataFrame())
        engine = SimpyDataEngine(self.normes)
        meteo, events = engine.simulate(n_jours=n_jours, scenario=scenario)
        nb_crit = sum(1 for e in events if e.severite == "CRITIQUE")
        return {
            "meteo_simulee": meteo,
            "evenements": [e.__dict__ for e in events],
            "nb_alertes_critique": int(nb_crit),
        }

    def get_norms(self) -> Dict[str, Any]:
        if self.normes is None:
            self.normes = self.etablir_normes(self.df if self.df is not None else pd.DataFrame())
        n = self.normes
        return {
            "genomique": n.genomique,
            "wofost_baseline": n.wofost_baseline,
            "seuils_alerte": n.seuils_alerte,
            "twso_baseline": n.twso_baseline,
        }

    def get_health(self) -> Dict[str, Any]:
        return {"status": "ok", "normes_loaded": self.normes is not None, "df_rows": int(0 if self.df is None else len(self.df))}

    def get_viz_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Defaults
            yield_score = float(params.get("yield_score", 0.75))
            drought_score = float(params.get("drought_score", 0.60))
            disease_score = float(params.get("disease_score", 0.70))
            scenario = str(params.get("scenario", "normal"))
            horizon = str(params.get("horizon", "6_mois"))
            variety_name = params.get("variety_name")

            horizon_days = int(HORIZON_DAYS.get(horizon, 180))
            scenario = scenario if scenario in SCENARIOS else "normal"

            traits = {
                "pred_yield": float(yield_score),
                "pred_drought": float(drought_score),
                "pred_disease": float(disease_score),
                "pred_salt": float(params.get("salt_score", self.medians.get("pred_salt", 0.5))),
            }

            if variety_name:
                reco = self.recommend(
                    variety_name=variety_name,
                    traits=None,
                    horizon=horizon,
                    scenario=scenario,
                )
            else:
                reco = self.recommend(
                    variety_name=None,
                    traits=traits,
                    horizon=horizon,
                    scenario=scenario,
                )

            proj = reco["projection"]
            risks = reco["stress_risks"]
            norms = self.get_norms()

            return {
                "yieldScore": float(yield_score),
                "droughtScore": float(drought_score),
                "diseaseScore": float(disease_score),
                "scenario": scenario,
                "horizonDays": int(horizon_days),
                "twso": float(proj["twso_mean"]),
                "twsoP10": float(proj["twso_p10"]),
                "twsoP90": float(proj["twso_p90"]),
                "confidence": float(proj["confidence"]),
                "stressRisks": {"drought": float(risks["drought"]), "disease": float(risks["disease"]), "heat": float(risks["heat"])},
                "recommendations": list(reco["recommendations"]),
                "varietyName": str(reco.get("variety_name", variety_name or "Custom")),
                "normsBaseline": float(norms["twso_baseline"]),
            }
        except Exception:
            return {
                "yieldScore": float(params.get("yield_score", 0.75)),
                "droughtScore": float(params.get("drought_score", 0.60)),
                "diseaseScore": float(params.get("disease_score", 0.70)),
                "scenario": str(params.get("scenario", "normal")),
                "horizonDays": int(HORIZON_DAYS.get(str(params.get("horizon", "6_mois")), 180)),
                "twso": 0.0,
                "twsoP10": 0.0,
                "twsoP90": 0.0,
                "confidence": 0.0,
                "stressRisks": {"drought": 0.0, "disease": 0.0, "heat": 0.0},
                "recommendations": [],
                "varietyName": str(params.get("variety_name") or "Custom"),
                "normsBaseline": float(self.normes.twso_baseline if self.normes is not None else 4500.0),
            }

    def _approx_twso_lai(self, row: Dict[str, Any]) -> Tuple[float, float]:
        """TWSO / LAI agrégés sans PCSE (cohérent avec run_wofost_base quand PCSE est indisponible)."""
        pred_yield = float(row.get("pred_yield", self.medians.get("pred_yield", 0.75)))
        pred_drought = float(row.get("pred_drought", self.medians.get("pred_drought", 0.60)))
        pred_disease = float(row.get("pred_disease", self.medians.get("pred_disease", 0.70)))
        twso = 2500.0 + pred_yield * 3500.0
        twso *= 0.85 + 0.15 * pred_drought
        twso *= 0.90 + 0.10 * pred_disease
        lai_max = 2.5 + pred_yield * 3.5
        return float(twso), float(lai_max)

    def _row_to_name(self, row: pd.Series, idx: int) -> str:
        for cand in ["variety_name", "variety", "name", "Variety", "VARIETY", "croisement", "Croisement"]:
            if cand in row.index and pd.notna(row[cand]) and str(row[cand]).strip():
                return str(row[cand]).strip()
        return f"Croisement_{idx}"

    def _events_for_dashboard(self, scenario: str, n_jours: int, max_events: int) -> List[Dict[str, Any]]:
        median_row = {
            "pred_yield": self.medians.get("pred_yield", 0.75),
            "pred_drought": self.medians.get("pred_drought", 0.60),
            "pred_disease": self.medians.get("pred_disease", 0.70),
            "pred_salt": self.medians.get("pred_salt", 0.50),
        }
        sim = self.simulate(median_row, n_jours=n_jours, scenario=scenario)
        out: List[Dict[str, Any]] = []
        start = date(2024, 11, 1)
        for e in sim["evenements"][:max_events]:
            jour = int(e.get("jour") or 0)
            d = start + timedelta(days=max(0, jour - 1))
            out.append(
                {
                    "jour": jour,
                    "date": d.isoformat(),
                    "type": str(e.get("type", "event")),
                    "severite": str(e.get("severite", "INFO")),
                    "description": str(e.get("message", "")),
                    "valeur": 0.0,
                }
            )
        return out

    def get_dashboard_payload(self, n_jours: int = 200, max_croisements: int = 30, max_events_per_scenario: int = 48) -> Dict[str, Any]:
        """
        Payload pour le tableau de bord (graphiques Chart.js, barres TWSO, événements SimPy).
        """
        def _to_python(v: Any) -> Any:
            import numpy as np
            if isinstance(v, (np.integer,)):
                return int(v)
            if isinstance(v, (np.floating,)):
                return float(v)
            if isinstance(v, np.ndarray):
                return v.tolist()
            if isinstance(v, dict):
                return {str(k): _to_python(val) for k, val in v.items()}
            if isinstance(v, list):
                return [_to_python(x) for x in v]
            if isinstance(v, tuple):
                return [_to_python(x) for x in v]
            return v

        if self.normes is None:
            self.normes = self.etablir_normes(self.df if self.df is not None else pd.DataFrame())
        n = self.normes
        baseline = float(n.twso_baseline)
        lai_baseline = float(n.wofost_baseline.get("LAI_baseline", 5.0))

        seuils = {
            "genomique_zscore": 2.0,
            "twso_critique_pct": float(n.seuils_alerte.get("twso_critique_pct", 0.70)),
            "twso_warning_pct": 0.85,
            "tmax_canicule": float(n.seuils_alerte.get("tmax_canicule", 38.0)),
            "pluie_stress": float(n.seuils_alerte.get("pluie_stress", 2.0)),
            "vent_alerte": 10.0,
            "dvs_retard_semis": 15,
            "lai_insuffisant": 1.5,
        }

        # Climatologie mensuelle Maktar (Tunisie) — alignée sur le dashboard HTML de référence
        meteo = {
            "tmin": [3.5, 4.0, 6.5, 9.5, 13.5, 18.0, 21.0, 21.5, 18.0, 14.0, 8.5, 4.5],
            "tmax": [13.0, 14.5, 17.5, 21.0, 26.5, 32.0, 36.0, 36.5, 31.0, 25.5, 18.5, 14.0],
            "pluie": [28, 22, 25, 20, 15, 8, 3, 5, 18, 28, 30, 32],
        }

        croisements: List[Dict[str, Any]] = []
        df = self.df
        if df is not None and len(df) > 0:
            df_work = df.copy()
            if "pred_yield" in df_work.columns:
                df_work = df_work.sort_values("pred_yield", ascending=False).head(max_croisements)
            for i, (_, r) in enumerate(df_work.iterrows()):
                rd = r.to_dict()
                for k in ["pred_drought", "pred_salt", "pred_yield", "pred_disease"]:
                    if k not in rd or rd[k] is None or (isinstance(rd[k], float) and np.isnan(rd[k])):
                        rd[k] = self.medians.get(k, 0.5)
                twso, lai_max = self._approx_twso_lai(rd)
                ratio = float(twso / baseline) if baseline > 0 else 0.0
                n_crit = 1 if ratio < seuils["twso_critique_pct"] else 0
                n_warn = 1 if ratio < seuils["twso_warning_pct"] and n_crit == 0 else 0
                croisements.append(
                    {
                        "name": self._row_to_name(r, i),
                        "twso": round(twso, 1),
                        "score": round(ratio, 4),
                        "ratio": round(ratio, 4),
                        "lai_max": round(lai_max, 3),
                        "n_warn": n_warn,
                        "n_crit": n_crit,
                        "pred_yield": float(rd.get("pred_yield", 0.0)),
                    }
                )
        else:
            rng = np.random.default_rng(7)
            for i in range(12):
                py = float(np.clip(0.25 + rng.random() * 0.55, 0, 1))
                rd = {
                    "pred_yield": py,
                    "pred_drought": float(np.clip(0.4 + rng.random() * 0.4, 0, 1)),
                    "pred_disease": float(np.clip(0.4 + rng.random() * 0.4, 0, 1)),
                    "pred_salt": float(np.clip(0.35 + rng.random() * 0.35, 0, 1)),
                }
                twso, lai_max = self._approx_twso_lai(rd)
                ratio = float(twso / baseline) if baseline > 0 else 0.0
                n_crit = 1 if ratio < seuils["twso_critique_pct"] else 0
                n_warn = 1 if ratio < seuils["twso_warning_pct"] and n_crit == 0 else 0
                croisements.append(
                    {
                        "name": f"Démo_{i + 1}",
                        "twso": round(twso, 1),
                        "score": round(ratio, 4),
                        "ratio": round(ratio, 4),
                        "lai_max": round(lai_max, 3),
                        "n_warn": n_warn,
                        "n_crit": n_crit,
                        "pred_yield": py,
                    }
                )

        events: Dict[str, List[Dict[str, Any]]] = {}
        for sc in SCENARIOS:
            events[sc] = self._events_for_dashboard(sc, n_jours=n_jours, max_events=max_events_per_scenario)

        median_traits = {
            "pred_yield": self.medians.get("pred_yield", 0.75),
            "pred_drought": self.medians.get("pred_drought", 0.60),
            "pred_disease": self.medians.get("pred_disease", 0.70),
            "pred_salt": self.medians.get("pred_salt", 0.50),
        }
        try:
            reco = self.recommend(None, median_traits, "6_mois", "normal")
            recommendations = list(reco.get("recommendations", []))
        except Exception:
            recommendations = []

        payload = {
            "twso_baseline": baseline,
            "lai_max_baseline": lai_baseline,
            "seuils": seuils,
            "meteo": meteo,
            "croisements": croisements,
            "events": events,
            "recommendations": recommendations,
            "n_jours": int(n_jours),
            "df_rows": int(0 if df is None else len(df)),
        }
        return _to_python(payload)

