import base64
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def build_digital_twin_radar(traits: dict, variety_name: str) -> str:
    labels = list(traits.keys())
    values = list(traits.values())
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.set_facecolor("#f8f9fa")
    fig.patch.set_facecolor("#ffffff")
    ax.plot(angles, values, "o-", linewidth=2, color="#2563eb")
    ax.fill(angles, values, alpha=0.25, color="#2563eb")
    ax.set_thetagrids(np.degrees(angles[:-1]), labels, fontsize=12)
    ax.set_ylim(0, 1)
    ax.set_title(f"Digital Twin — {variety_name}", pad=18, fontsize=13, fontweight="bold")
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def build_montecarlo_chart(mc_result: dict) -> str:
    dist = mc_result["distribution"]
    traits = ["drought", "salt", "yield", "disease", "score_composite"]
    colors = ["#2563eb", "#16a34a", "#dc2626", "#d97706", "#7c3aed"]
    fig, axes = plt.subplots(1, 5, figsize=(16, 4))
    fig.patch.set_facecolor("#ffffff")
    for ax, trait, color in zip(axes, traits, colors):
        ax.hist(dist[trait], bins=30, color=color, alpha=0.75, edgecolor="white")
        ax.axvline(mc_result["mean"][trait], color="black", linestyle="--", linewidth=1.5, label=f"μ={mc_result['mean'][trait]:.3f}")
        ax.set_title(trait, fontsize=11, fontweight="bold")
        ax.set_xlabel("valeur prédite", fontsize=9)
        ax.legend(fontsize=8)
        ax.set_facecolor("#f8f9fa")
    plt.suptitle("Distribution Monte Carlo des traits", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def is_pareto_efficient(scores: np.ndarray) -> np.ndarray:
    n = scores.shape[0]
    eff = np.ones(n, dtype=bool)
    for i in range(n):
        eff[i] = not np.any(np.all(scores >= scores[i], axis=1) & np.any(scores > scores[i], axis=1))
    return eff


def build_pareto_chart(crossings_df: pd.DataFrame) -> str:
    cdf = crossings_df.copy()
    cdf["yield"] = cdf.get("yield", cdf["pred_yield"])
    cdf["drought"] = cdf.get("drought", cdf["pred_drought"])
    cdf["salt"] = cdf.get("salt", cdf["pred_salt"])
    cdf["disease"] = cdf.get("disease", cdf["pred_disease"])
    cdf["score_composite"] = cdf.get("score_composite", 0.4 * cdf["drought"] + 0.3 * cdf["salt"] + 0.2 * cdf["yield"] + 0.1 * cdf["disease"])
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f8f9fa")
    sc = ax.scatter(cdf["yield"], cdf["drought"], c=cdf["score_composite"], cmap="viridis", alpha=0.6, s=18, linewidths=0)
    plt.colorbar(sc, ax=ax, label="Score composite")
    mask = is_pareto_efficient(cdf[["drought", "salt", "yield", "disease"]].values)
    p = cdf[mask]
    ax.scatter(p["yield"], p["drought"], c="red", s=40, zorder=5, label="Front de Pareto")
    ax.set_xlabel("Rendement (yield)", fontsize=11)
    ax.set_ylabel("Résistance sécheresse (drought)", fontsize=11)
    ax.set_title("Front de Pareto — Croisements blé dur", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def build_correlation_heatmap(df: pd.DataFrame, top_n: int = 20) -> str:
    snp_cols = [c for c in df.columns if c.startswith("SNP")]
    target_cols = ["drought", "salt", "yield", "disease"]
    corr = df[snp_cols + target_cols].corr()
    snp_target = corr.loc[snp_cols, target_cols].abs()
    top_snps = snp_target.max(axis=1).nlargest(top_n).index.tolist()
    heat_data = snp_target.loc[top_snps]
    fig, ax = plt.subplots(figsize=(7, top_n * 0.35 + 2))
    im = ax.imshow(heat_data.values, aspect="auto", cmap="YlOrRd", vmin=0, vmax=0.5)
    ax.set_xticks(range(4))
    ax.set_xticklabels(target_cols, fontsize=11)
    ax.set_yticks(range(top_n))
    ax.set_yticklabels(top_snps, fontsize=9)
    plt.colorbar(im, ax=ax, label="|corrélation|")
    ax.set_title(f"Top {top_n} SNPs corrélés aux traits", fontsize=12, fontweight="bold")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def build_model_comparison(metrics: dict) -> str:
    models = list(metrics.keys())
    r2s = [metrics[m]["avg_R2"] for m in models]
    maes = [metrics[m]["avg_MAE"] for m in models]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    colors = ["#2563eb", "#16a34a", "#dc2626", "#d97706", "#7c3aed", "#0891b2"][: len(models)]
    ax1.bar(models, r2s, color=colors, alpha=0.85)
    ax1.set_title("R² moyen par modèle", fontweight="bold")
    ax1.set_ylabel("R²")
    ax1.set_ylim(0, 1)
    for i, v in enumerate(r2s):
        ax1.text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)
    ax2.bar(models, maes, color=colors, alpha=0.85)
    ax2.set_title("MAE moyen par modèle", fontweight="bold")
    ax2.set_ylabel("MAE")
    for i, v in enumerate(maes):
        ax2.text(i, v + 0.001, f"{v:.3f}", ha="center", fontsize=9)
    plt.suptitle("Comparaison des modèles", fontsize=13, fontweight="bold")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def build_shap_summary(shap_vals: np.ndarray, feature_names: list, model: str, top_n: int = 15) -> str:
    importances = np.abs(shap_vals).mean(axis=0)
    idx_sorted = np.argsort(importances)[::-1][:top_n]
    top_names = [feature_names[i] for i in idx_sorted]
    top_vals = importances[idx_sorted]
    fig, ax = plt.subplots(figsize=(8, top_n * 0.4 + 1))
    ax.barh(top_names[::-1], top_vals[::-1], color="#2563eb", alpha=0.85)
    ax.set_xlabel("Importance SHAP moyenne |ϕ|", fontsize=11)
    ax.set_title(f"SHAP — Top {top_n} features ({model})", fontsize=12, fontweight="bold")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

