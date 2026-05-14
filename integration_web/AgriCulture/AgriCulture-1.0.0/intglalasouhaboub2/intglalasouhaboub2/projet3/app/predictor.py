"""
predictor.py — Logique centrale de prédiction et génération de graphiques

Expose :
  - GxEPredictor : classe principale (chargement modèle + prédiction + graphiques)
"""
import io
import pickle
import base64
import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Optional, List, Dict, Any

from app.config import (
    MODEL_WEIGHTS_PATH, ARTIFACTS_PATH,
    TRAITS, TRAIT_LABELS_FR, COLORS_TRAITS,
    STADES_LABELS, SEQ_LEN, PRED_LEN, N_STADES, DEV_CURVE,
    RENDEMENT_MOYEN_TUNISIE, RENDEMENT_POTENTIEL_MAX,
)
from app.models.wheat import load_model
from app.utils.preprocessing import (
    build_lstm_input, build_gxe_targets,
    extract_all_parents, find_variety_approx, parse_parents_from_cross,
)


class GxEPredictor:
    """
    Classe centrale du pipeline G×E.
    Chargée une seule fois au démarrage de l'API (singleton via app.state).
    """

    def __init__(self):
        # ── Chargement des artefacts ──────────────────────────────────
        with open(ARTIFACTS_PATH, "rb") as f:
            artifacts = pickle.load(f)

        self.scaler_X                = artifacts["scaler_X"]
        self.scaler_y                = artifacts["scaler_y"]
        self.clim_par_stade          = artifacts["clim_par_stade"]
        self.env_scores_par_stade    = artifacts["env_scores_par_stade"]
        self.crossings_df            = artifacts["crossings_df"]
        self.predictions_by_crossing = artifacts["predictions_by_crossing"]
        self.best_model_name         = artifacts["best_model_name"]
        self.CALIB_SLOPE             = float(artifacts["CALIB_SLOPE"])
        self.CALIB_INTERCEPT         = float(artifacts["CALIB_INTERCEPT"])

        # Index rapide des prédictions par nom de croisement
        self.pred_map = {p["croisement"]: p for p in self.predictions_by_crossing}

        # ── Chargement du modèle ──────────────────────────────────────
        self.model = load_model(
            model_name=self.best_model_name,
            weights_path=str(MODEL_WEIGHTS_PATH),
            device="cpu",
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    def score_to_kgha(self, score: float) -> float:
        return float(np.clip(
            score * self.CALIB_SLOPE + self.CALIB_INTERCEPT,
            0, RENDEMENT_POTENTIEL_MAX,
        ))

    def _fig_to_base64(self, fig) -> str:
        """Convertit une figure matplotlib en PNG base64."""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    # ── Prédiction d'un croisement custom ────────────────────────────────

    def predict_custom(self, pred_drought: float, pred_salt: float,
                        pred_yield: float, pred_disease: float,
                        croisement_name: str = "Custom") -> Dict[str, Any]:
        """
        Prédit la trajectoire G×E T6–T7 pour un croisement donné par ses traits.
        """
        row = {
            "pred_drought": pred_drought, "pred_salt": pred_salt,
            "pred_yield": pred_yield,     "pred_disease": pred_disease,
        }
        X_raw  = build_lstm_input(row, self.clim_par_stade)
        X_norm = self.scaler_X.transform(X_raw)
        X_t    = torch.FloatTensor(X_norm).unsqueeze(0)

        with torch.no_grad():
            pred_norm = self.model(X_t).cpu().numpy()

        pred_inv = self.scaler_y.inverse_transform(
            pred_norm.reshape(-1, len(TRAITS))
        ).reshape(PRED_LEN, len(TRAITS))
        pred_inv = np.clip(pred_inv, 0, 1)

        gxe_full = build_gxe_targets(row, self.env_scores_par_stade)

        return {
            "croisement":      croisement_name,
            "modele_utilise":  self.best_model_name,
            "yield_kg_ha":     round(self.score_to_kgha(pred_yield), 0),
            "predictions_T6_T7": {
                t: {"T6": round(float(pred_inv[0, i]), 4),
                    "T7": round(float(pred_inv[1, i]), 4)}
                for i, t in enumerate(TRAITS)
            },
            "trajectoire_complete": {
                t: [round(float(gxe_full[s, i]), 4) for s in range(N_STADES)]
                for i, t in enumerate(TRAITS)
            },
        }

    # ── Recommandation par variété ────────────────────────────────────────

    def recommend(self, variete_cible: str,
                  poids: Dict[str, float],
                  top_n: int = 5) -> Dict[str, Any]:
        """
        Retourne les top_n meilleurs croisements pour une variété donnée.
        """
        variete_trouvee, score_match = find_variety_approx(
            variete_cible, self.crossings_df)

        if variete_trouvee is None:
            parents = extract_all_parents(self.crossings_df)
            return {"error": f"Variété '{variete_cible}' introuvable",
                    "suggestions": parents[:20]}

        import re
        mask = self.crossings_df["Croisement"].str.contains(
            re.escape(variete_trouvee), case=False, na=False)
        df = self.crossings_df[mask].copy()

        if len(df) == 0:
            return {"error": f"Aucun croisement pour '{variete_trouvee}'"}

        df["score_reco"] = df.apply(
            lambda r: sum(poids.get(t, 0) * float(r[f"pred_{t}"]) for t in TRAITS), axis=1)
        df["yield_kg_ha"] = df["pred_yield"].apply(self.score_to_kgha)
        top = df.nlargest(top_n, "score_reco").reset_index(drop=True)

        return {
            "variete":        variete_trouvee,
            "score_match":    score_match,
            "total_trouves":  int(len(df)),
            "top_recommandations": [
                {
                    "rang":                 i + 1,
                    "croisement":           row["Croisement"],
                    "score_recommandation": round(float(row["score_reco"]), 4),
                    "yield_kg_ha":          round(float(row["yield_kg_ha"]), 0),
                    "pred_drought":         round(float(row["pred_drought"]), 4),
                    "pred_salt":            round(float(row["pred_salt"]), 4),
                    "pred_yield":           round(float(row["pred_yield"]), 4),
                    "pred_disease":         round(float(row["pred_disease"]), 4),
                }
                for i, (_, row) in enumerate(top.iterrows())
            ],
        }

    # ════════════════════════════════════════════════════════════════════
    #  GRAPHIQUES
    # ════════════════════════════════════════════════════════════════════

    def plot_trajectoire(self, croisement_name: str) -> Optional[str]:
        """
        Graphique 2×2 — trajectoire G×E T0→T7 pour un croisement existant.
        Retourne l'image en base64 PNG.
        """
        pdata = self.pred_map.get(croisement_name)
        if pdata is None:
            return None

        row = self.crossings_df[
            self.crossings_df["Croisement"] == croisement_name
        ].iloc[0]

        x          = np.arange(N_STADES)
        x_obs      = x[:SEQ_LEN]
        x_pred_idx = x[SEQ_LEN:]

        fig, axes = plt.subplots(2, 2, figsize=(14, 9))
        fig.suptitle(
            f"Trajectoire phénologique G×E\n{croisement_name[:70]}\n"
            f"Score = {row['score_fixe']:.4f}  |  "
            f"Rendement estimé = {self.score_to_kgha(row['pred_yield']):.0f} kg/ha",
            fontsize=10, fontweight="bold",
        )

        for t_idx, (trait, ax) in enumerate(zip(TRAITS, axes.flatten())):
            col       = COLORS_TRAITS[trait]
            base_val  = float(row[f"pred_{trait}"])
            full_mat  = np.array(pdata["full"])
            pred_mat  = np.array(pdata["predicted"])
            true_mat  = np.array(pdata["true_final"])

            ax.hlines(base_val, 0, N_STADES - 1, colors="gray",
                      linestyles="--", lw=1.2, alpha=0.6, label="Potentiel génétique brut")
            ax.plot(x_obs, full_mat[:SEQ_LEN, t_idx], "o-", color=col, lw=2.5,
                    markersize=7, label="G×E observé (T0–T5)", zorder=4)
            ax.plot(x_pred_idx, true_mat[:, t_idx], "s--", color=col,
                    lw=1.5, markersize=7, alpha=0.55, label="G×E réel (T6–T7)")
            ax.plot(x_pred_idx, pred_mat[:, t_idx], "*-", color="black",
                    lw=2.0, markersize=11,
                    label=f"Prédit {self.best_model_name} (T6–T7)", zorder=5)
            ax.fill_between(x, [base_val] * N_STADES, full_mat[:, t_idx],
                            alpha=0.10, color=col, label="Δ stress")
            ax.axvspan(SEQ_LEN - 0.5, N_STADES - 0.5, alpha=0.06, color="gray")

            # Hétérosis
            f1_fin = full_mat[-1, t_idx]
            if base_val > 0.01:
                vigor = (f1_fin - base_val) / base_val * 100
                sign  = "+" if vigor >= 0 else ""
                ax.annotate(
                    f"Hétérosis F1\n{sign}{vigor:.1f}%",
                    xy=(N_STADES - 1, f1_fin),
                    xytext=(N_STADES - 2.6, min(f1_fin + 0.09, 1.0)),
                    fontsize=8, color=col, fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color=col, lw=1.2),
                )

            ax.set_title(TRAIT_LABELS_FR[trait], fontsize=11, fontweight="bold")
            ax.set_xticks(x)
            ax.set_xticklabels(STADES_LABELS, rotation=30, ha="right", fontsize=9)
            ax.set_ylim(0, 1.18)
            ax.set_ylabel("Score G×E normalisé [0-1]")
            ax.legend(fontsize=7, loc="upper left")
            ax.grid(alpha=0.3)
            ax.set_facecolor("#fafafa")

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def plot_top5_maturite(self) -> str:
        """
        Graphique barres — comparaison des Top 5 croisements à maturité (T7).
        """
        top5 = sorted(self.predictions_by_crossing,
                      key=lambda p: p["score_fixe"], reverse=True)[:5]

        fig, ax = plt.subplots(figsize=(13, 6))
        bar_width = 0.18
        x_pos     = np.arange(len(top5))

        for t_idx, trait in enumerate(TRAITS):
            vals = [np.array(p["full"])[-1, t_idx] for p in top5]
            ax.bar(x_pos + t_idx * bar_width, vals, bar_width,
                   label=TRAIT_LABELS_FR[trait],
                   color=list(COLORS_TRAITS.values())[t_idx],
                   edgecolor="white", linewidth=1)

        ax.set_xticks(x_pos + bar_width * 1.5)
        ax.set_xticklabels(
            [f"#{i+1}\n{p['croisement'][:22]}…" for i, p in enumerate(top5)],
            fontsize=8,
        )
        ax.set_ylabel("Score G×E à maturité (T7) [0-1]")
        ax.set_title("Top 5 croisements — Traits à maturité (T7)", fontsize=12, fontweight="bold")
        ax.legend(loc="upper right", fontsize=9)
        ax.set_ylim(0, 1.1)
        ax.grid(axis="y", alpha=0.3)
        ax.set_facecolor("#fafafa")
        plt.tight_layout()
        return self._fig_to_base64(fig)

    def plot_distribution_rendement(self) -> str:
        """
        Histogramme de distribution des rendements estimés (kg/ha) pour tous les croisements.
        """
        df = self.crossings_df
        fig, ax = plt.subplots(figsize=(11, 5))

        ax.hist(df["yield_kg_ha"], bins=35, color="#1D9E75",
                edgecolor="white", linewidth=0.8, alpha=0.85)
        ax.axvline(RENDEMENT_MOYEN_TUNISIE, color="red", linestyle="--",
                   lw=1.8, label=f"Moy. nationale ({RENDEMENT_MOYEN_TUNISIE} kg/ha)")
        mediane = float(df["yield_kg_ha"].median())
        ax.axvline(mediane, color="#EF9F27", linestyle="-",
                   lw=1.8, label=f"Médiane ({mediane:.0f} kg/ha)")

        ax.set_xlabel("Rendement estimé (kg/ha)", fontsize=11)
        ax.set_ylabel("Nombre de croisements", fontsize=11)
        ax.set_title(
            f"Distribution des {len(df)} croisements — Calibration WOFOST",
            fontsize=12, fontweight="bold",
        )
        ax.legend(fontsize=10)
        ax.grid(alpha=0.3, axis="y")
        ax.set_facecolor("#fafafa")
        plt.tight_layout()
        return self._fig_to_base64(fig)

    def plot_top10_rendement(self) -> str:
        """
        Graphique barres horizontales — Top 10 croisements par rendement kg/ha.
        """
        df   = self.crossings_df
        top10 = df.nlargest(10, "yield_kg_ha").reset_index(drop=True)
        q75   = float(df["yield_kg_ha"].quantile(0.75))

        fig, ax = plt.subplots(figsize=(13, 6))
        colors_bar = ["#1D9E75" if v > q75 else "#EF9F27"
                      for v in top10["yield_kg_ha"]]
        bars = ax.barh(range(10), top10["yield_kg_ha"].values,
                       color=colors_bar, edgecolor="white", linewidth=1)
        ax.axvline(RENDEMENT_MOYEN_TUNISIE, color="red", linestyle="--",
                   lw=1.2, alpha=0.8, label="Moy. nationale")
        ax.set_yticks(range(10))
        ax.set_yticklabels([f"#{i+1} — {row['Croisement'][:35]}…"
                            for i, (_, row) in enumerate(top10.iterrows())], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("Rendement estimé (kg/ha)", fontsize=11)
        ax.set_title("Top 10 croisements — Rendement calibré (kg/ha)",
                     fontsize=12, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3, axis="x")
        for bar, val in zip(bars, top10["yield_kg_ha"].values):
            ax.text(bar.get_width() + 10, bar.get_y() + bar.get_height() / 2,
                    f"{val:.0f} kg/ha", va="center", fontsize=8, fontweight="bold")
        plt.tight_layout()
        return self._fig_to_base64(fig)

    def plot_synthese_variete(self, variete_name: str,
                               poids: Dict[str, float],
                               trait_focus: str = "yield") -> Optional[str]:
        """
        Vue synthétique : trajectoires des Top-5 croisements d'une variété
        pour un trait donné (T0→T7).
        """
        import re
        mask = self.crossings_df["Croisement"].str.contains(
            re.escape(variete_name), case=False, na=False)
        df = self.crossings_df[mask].copy()
        if len(df) == 0:
            return None

        df["score_reco"] = df.apply(
            lambda r: sum(poids.get(t, 0) * float(r[f"pred_{t}"]) for t in TRAITS), axis=1)
        top5  = df.nlargest(5, "score_reco").reset_index(drop=True)
        t_idx = TRAITS.index(trait_focus)

        x          = np.arange(N_STADES)
        x_obs      = x[:SEQ_LEN]
        x_pred_idx = x[SEQ_LEN:]
        palette    = plt.cm.tab10(np.linspace(0, 0.8, len(top5)))

        fig, ax = plt.subplots(figsize=(14, 7))
        ax.set_title(
            f"Série temporelle G×E — Trait : {TRAIT_LABELS_FR[trait_focus]}\n"
            f"Variété : {variete_name} — Top 5 croisements recommandés",
            fontsize=12, fontweight="bold",
        )

        for i, (_, row) in enumerate(top5.iterrows()):
            cross = row["Croisement"]
            pdata = self.pred_map.get(cross)
            if pdata is None:
                continue
            col   = palette[i]
            label = f"#{i+1} {cross[:28]} | sc={row['score_reco']:.3f}"
            obs  = np.array(pdata["observed"])
            pred = np.array(pdata["predicted"])
            ax.plot(x_obs, obs[:, t_idx], "o-", color=col, lw=2.2,
                    markersize=6, label=label)
            ax.plot(x_pred_idx, pred[:, t_idx], "*--", color=col,
                    lw=2.2, markersize=9)
            ax.plot([x_obs[-1], x_pred_idx[0]],
                    [obs[-1, t_idx], pred[0, t_idx]],
                    ":", color=col, lw=1.2, alpha=0.6)
            ax.annotate(f"#{i+1}", xy=(N_STADES - 1, np.array(pdata["full"])[-1, t_idx]),
                        xytext=(N_STADES - 0.5, np.array(pdata["full"])[-1, t_idx]),
                        fontsize=8, color=col, fontweight="bold", va="center")

        ax.axvspan(SEQ_LEN - 0.5, N_STADES - 0.5, alpha=0.05, color="gray")
        ax.axvline(SEQ_LEN - 0.5, color="gray", lw=1.2, linestyle="--", alpha=0.7)
        ax.text(SEQ_LEN - 0.3, 1.12, "← Zone prédiction", fontsize=8,
                color="gray", fontstyle="italic")
        ax.set_xticks(x)
        ax.set_xticklabels(STADES_LABELS, rotation=25, ha="right", fontsize=10)
        ax.set_ylim(0, 1.18)
        ax.set_ylabel("Score G×E normalisé [0-1]", fontsize=11)
        ax.set_xlabel("Stade phénologique", fontsize=11)
        ax.legend(fontsize=8, loc="upper left", framealpha=0.9)
        ax.grid(alpha=0.3)
        ax.set_facecolor("#fafafa")
        plt.tight_layout()
        return self._fig_to_base64(fig)
