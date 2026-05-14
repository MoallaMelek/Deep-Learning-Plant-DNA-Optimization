"""
Streamlit frontend for the backend-aligned proxy-expression pipeline.

Run with:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import html
import json
import sys
from itertools import product
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

try:
    import py3Dmol  # type: ignore[import-not-found]
except ImportError:
    py3Dmol = None

try:
    from streamlit_searchbox import st_searchbox  # type: ignore[import-not-found]
except ImportError:
    st_searchbox = None

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

for p in (ROOT_DIR, SRC_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from main import run_pipeline
from dataset_builder import PipelineConfig
from dataset_builder.protein_structure import (
    apply_hydrophobicity_bfactor,
    fetch_pdb_text,
    generate_mock_pdb_from_length,
)
from app.internal.artifacts import (
    abs_path as _artifact_abs_path,
    clear_loaded_artifacts as _clear_loaded_artifacts_impl,
    init_session_state as _init_session_state_impl,
    load_artifacts_from_manifest as _load_artifacts_from_manifest_impl,
    load_json as _load_json_impl,
    resolve_manifest_path as _resolve_manifest_path_impl,
    resolve_manifest_relative_path as _resolve_manifest_relative_path_impl,
    store_artifacts as _store_artifacts_impl,
)
from app.internal.keyword_suggestions import (
    estimate_keyword_volume as _estimate_keyword_volume_impl,
    get_all_keyword_suggestions as _get_all_keyword_suggestions_impl,
    get_keyword_suggestions as _get_keyword_suggestions_impl,
)
from app.internal.metrics_dashboard import (
    baseline_model_name as _baseline_model_name_impl,
    best_model_name as _best_model_name_impl,
    compute_shap_values as _compute_shap_values_impl,
    display_feature_types as _display_feature_types_impl,
    extract_importance_from_model as _extract_importance_from_model_impl,
    generate_metrics_conclusion as _generate_metrics_conclusion_impl,
    importance_dataframe_from_metrics as _importance_dataframe_from_metrics_impl,
    load_best_model as _load_best_model_impl,
    load_metrics as _load_metrics_impl,
    load_metrics_dataset as _load_metrics_dataset_impl,
    model_comparison_dataframe as _model_comparison_dataframe_impl,
    plot_feature_importance as _plot_feature_importance_impl,
    plot_model_vs_baseline as _plot_model_vs_baseline_impl,
    plot_predictions_vs_real as _plot_predictions_vs_real_impl,
    plot_residuals as _plot_residuals_impl,
    plot_shap_global_summary as _plot_shap_global_summary_impl,
    plot_shap_local_explanation as _plot_shap_local_explanation_impl,
    render_metrics_tab as _render_metrics_tab_impl,
    resolve_model_path_for_metrics as _resolve_model_path_for_metrics_impl,
)


st.set_page_config(
    page_title="Plant DNA Intelligence - Backend Pipeline",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.main-header {
    font-size: 2.2rem;
    font-weight: 700;
    color: #1b5e20;
    margin-bottom: 0.35rem;
}
.sub-header {
    color: #4b5563;
    margin-bottom: 1.2rem;
}
.info-box {
    background-color: #eef7ef;
    border: 1px solid #9ccc9c;
    border-radius: 8px;
    padding: 0.75rem;
}
.ux-card {
    background-color: #f8fafc;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 0.85rem 0.9rem;
    height: 100%;
}
.ux-card-title {
    font-size: 0.98rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.55rem;
}
.card-row {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.38rem;
    font-size: 0.92rem;
}
.card-key {
    color: #475569;
}
.card-value {
    color: #111827;
    font-weight: 600;
    text-align: right;
    max-width: 68%;
    word-break: break-word;
}
.impact-stage {
    border: 1px solid #dbeafe;
    border-radius: 14px;
    background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%);
    padding: 0.8rem 0.9rem;
    min-height: 470px;
}
.impact-stage-title {
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.5rem;
}
.impact-arrow {
    text-align: center;
    font-size: 2rem;
    font-weight: 700;
    color: #334155;
    margin-top: 9rem;
    animation: impactFlow 1.6s ease-in-out infinite;
}
.impact-codon-track {
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 0.55rem;
    background: #ffffff;
    line-height: 1.9;
    min-height: 180px;
}
.impact-codon {
    display: inline-block;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 0.78rem;
    color: #0f172a;
    border-radius: 6px;
    padding: 0.12rem 0.32rem;
    margin: 0.12rem;
}
.impact-naive {
    background: linear-gradient(90deg, #fdba74 0%, #fb7185 100%);
}
.impact-optimized {
    background: linear-gradient(90deg, #6ee7b7 0%, #7dd3fc 100%);
}
.impact-diff {
    outline: 2px solid #f59e0b;
    transform: translateY(-1px);
}
.impact-legend-row {
    display: flex;
    gap: 0.45rem;
    flex-wrap: wrap;
    margin-top: 0.4rem;
    margin-bottom: 0.2rem;
}
.impact-chip {
    display: inline-block;
    border-radius: 999px;
    padding: 0.2rem 0.55rem;
    font-size: 0.76rem;
    font-weight: 600;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    background: #f8fafc;
}
.impact-concept {
    border: 1px solid #bfdbfe;
    border-radius: 12px;
    padding: 0.75rem 0.9rem;
    background: linear-gradient(120deg, #eef2ff 0%, #ecfeff 100%);
    animation: impactPulse 2.4s ease-in-out infinite;
}
.impact-concept-title {
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.3rem;
}
.impact-concept-line {
    color: #334155;
    font-size: 0.9rem;
    margin-bottom: 0.2rem;
}
@keyframes impactPulse {
    0% { box-shadow: 0 0 0 rgba(37, 99, 235, 0.0); }
    50% { box-shadow: 0 0 16px rgba(37, 99, 235, 0.12); }
    100% { box-shadow: 0 0 0 rgba(37, 99, 235, 0.0); }
}
@keyframes impactFlow {
    0% { transform: translateX(0); opacity: 0.55; }
    50% { transform: translateX(6px); opacity: 1.0; }
    100% { transform: translateX(0); opacity: 0.55; }
}
</style>
""",
    unsafe_allow_html=True,
)


def _abs_path(path_text: str) -> Path:
    return _artifact_abs_path(path_text)


def _load_json(path: Path) -> Dict[str, Any]:
    return _load_json_impl(path)


def _resolve_manifest_relative_path(manifest_path: Optional[Path], value: Optional[str]) -> Optional[Path]:
    return _resolve_manifest_relative_path_impl(manifest_path, value)


def _resolve_manifest_path(
    output_dir: Optional[str],
    explicit_manifest: Optional[str] = None,
    strict_explicit: bool = False,
) -> Optional[Path]:
    return _resolve_manifest_path_impl(
        output_dir,
        explicit_manifest=explicit_manifest,
        strict_explicit=strict_explicit,
    )


def _load_artifacts_from_manifest(manifest_path: Path) -> Dict[str, Any]:
    return _load_artifacts_from_manifest_impl(manifest_path)


def init_session_state() -> None:
    _init_session_state_impl(st.session_state)


def _store_artifacts(payload: Dict[str, Any], load_mode: str = "manual_load") -> None:
    _store_artifacts_impl(st.session_state, payload, load_mode=load_mode)


def _clear_loaded_artifacts() -> None:
    _clear_loaded_artifacts_impl(st.session_state)


def _render_metadata_panel(metadata: Dict[str, Any]) -> None:
    st.markdown("### Metadata Snapshot")
    if not metadata:
        st.info("Metadata file not loaded yet.")
        return

    keyword = metadata.get("keyword", "N/A")
    rows_generated = metadata.get("rows_generated", "N/A")
    plant_hosts = metadata.get("plant_hosts", [])
    proxy_weights = metadata.get("proxy_weights", {})
    model_input_columns = metadata.get("model_input_columns", [])
    categorical_model_columns = metadata.get("categorical_model_columns", [])
    model_target_column = metadata.get("model_target_column", "target_expression_score")
    model_group_column = metadata.get("model_group_column", "N/A")
    non_model_columns = metadata.get("non_model_columns", [])
    proxy_note = metadata.get("proxy_note")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Keyword", keyword)
        st.metric("Rows Generated", rows_generated)
        st.write("Plant Hosts")
        if plant_hosts:
            st.write(", ".join(plant_hosts))
        else:
            st.write("N/A")
        st.metric("ML Target", model_target_column)

    with col2:
        st.metric("Group Split Column", model_group_column)
        st.write("Proxy Weights")
        if proxy_weights:
            st.json(proxy_weights)
        else:
            st.write("N/A")

        st.write("Model Input Columns")
        if model_input_columns:
            st.caption(", ".join(model_input_columns))
        else:
            st.caption("N/A")

        st.write("Categorical Model Columns")
        if categorical_model_columns:
            st.caption(", ".join(categorical_model_columns))
        else:
            st.caption("N/A")

    with st.expander("Additional metadata fields", expanded=False):
        st.write("Non-Model Columns")
        if non_model_columns:
            st.caption(", ".join(non_model_columns))
        else:
            st.caption("N/A")

        st.write("Proxy Note")
        if proxy_note:
            st.caption(proxy_note)
        else:
            st.caption("N/A")


def _json_download_payload(data: Dict[str, Any]) -> str:
    if not data:
        return "{}"
    return json.dumps(data, indent=2, ensure_ascii=False)


def _ethics_kmer_columns(k: int = 4) -> List[str]:
    """Return 4-mer columns in the same order as the ethics model CSV."""
    return ["".join(parts) for parts in product("ACGT", repeat=k)]


def _build_ethics_csv_from_dataset(df: pd.DataFrame) -> Tuple[Optional[str], str]:
    """
    Convert optimized DNA rows into the colleague ethics-model input format.

    Expected schema:
    fichier,id,label,split,longueur,AAAA,AAAC,...,TTTT
    """
    if df.empty:
        return None, "No dataset is loaded."
    if "dna_sequence" not in df.columns:
        return None, "The loaded dataset has no dna_sequence column."

    kmer_columns = _ethics_kmer_columns(k=4)
    output_rows: List[Dict[str, Any]] = []
    keyword = str((st.session_state.get("metadata") or {}).get("keyword") or "optimized_dna")

    for export_id, (_, row) in enumerate(df.iterrows()):
        sequence = "".join(base for base in str(row.get("dna_sequence", "")).upper() if base in "ACGT")
        if not sequence:
            continue

        kmer_total = max(len(sequence) - 3, 0)
        kmer_counts = {kmer: 0 for kmer in kmer_columns}
        for pos in range(kmer_total):
            kmer = sequence[pos : pos + 4]
            if kmer in kmer_counts:
                kmer_counts[kmer] += 1

        export_row: Dict[str, Any] = {
            "fichier": f"{keyword}_optimized_dna.fna",
            "id": export_id,
            "label": -1,
            "split": "test_unknown",
            "longueur": len(sequence),
        }
        if kmer_total > 0:
            export_row.update({kmer: kmer_counts[kmer] / kmer_total for kmer in kmer_columns})
        else:
            export_row.update({kmer: 0.0 for kmer in kmer_columns})
        output_rows.append(export_row)

    if not output_rows:
        return None, "No valid optimized DNA sequence was found in the loaded dataset."

    ethics_df = pd.DataFrame(output_rows, columns=["fichier", "id", "label", "split", "longueur"] + kmer_columns)
    return ethics_df.to_csv(index=False), f"{len(ethics_df)} optimized DNA rows exported."


def _is_non_informative_series(series: pd.Series) -> bool:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return True
    return cleaned.nunique() <= 1


def _is_host_invariant_target(df: pd.DataFrame) -> bool:
    if df.empty or "plant_host" not in df.columns or "target_expression_score" not in df.columns:
        return False
    host_means = (
        df.groupby("plant_host")["target_expression_score"]
        .mean()
        .round(8)
    )
    return host_means.nunique() <= 1


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 1) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_percent(value: Any, default: float = 0.0) -> float:
    numeric = _safe_float(value, default=default)
    return numeric * 100.0 if numeric <= 1.5 else numeric


def _gc_stability_score(
    gc_content: Any,
    optimal_min_percent: float = 45.0,
    optimal_max_percent: float = 60.0,
) -> float:
    gc_percent = _to_percent(gc_content, default=0.0)
    if optimal_min_percent <= gc_percent <= optimal_max_percent:
        return 100.0

    if gc_percent < optimal_min_percent:
        distance = optimal_min_percent - gc_percent
    else:
        distance = gc_percent - optimal_max_percent

    return max(0.0, min(100.0, 100.0 - (distance * 4.0)))


def _normalize_with_fixed_bounds(value: Any, lower_bound: float, upper_bound: float) -> float:
    numeric = _safe_float(value, default=lower_bound)
    if upper_bound <= lower_bound:
        return 0.0
    normalized = ((numeric - lower_bound) / (upper_bound - lower_bound)) * 100.0
    return max(0.0, min(100.0, normalized))


def _format_time_duration(minutes_value: Any) -> str:
    total_minutes = max(0, _safe_int(minutes_value, default=0))

    if total_minutes < 60:
        return f"{total_minutes} min"

    if total_minutes < 24 * 60:
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours} h" if minutes == 0 else f"{hours} h {minutes} min"

    days, remaining_minutes = divmod(total_minutes, 24 * 60)
    hours = remaining_minutes // 60
    day_label = "day" if days == 1 else "days"
    return f"{days} {day_label}" if hours == 0 else f"{days} {day_label} {hours} h"


def _accession_column_name(df: pd.DataFrame) -> Optional[str]:
    for candidate in ("accession", "protein_accession"):
        if candidate in df.columns:
            return candidate
    return None


def _dna_preview(sequence: str, width: int = 60) -> str:
    seq = (sequence or "").strip().upper()
    if not seq:
        return "N/A"
    return f"{seq[:width]}..." if len(seq) > width else seq


def _codon_difference_score(seq_a: str, seq_b: str) -> float:
    a = (seq_a or "").strip().upper()
    b = (seq_b or "").strip().upper()
    common_len = min(len(a), len(b))
    common_len -= common_len % 3
    if common_len <= 0:
        return 0.0

    different = 0
    codon_total = common_len // 3
    for i in range(0, common_len, 3):
        if a[i : i + 3] != b[i : i + 3]:
            different += 1
    return round(different / codon_total, 4)


def _render_improvement_indicator(label: str, delta_value: float) -> None:
    if delta_value > 0:
        st.success(f"{label}: optimized is higher ({delta_value:+.4f})")
    elif delta_value < 0:
        st.error(f"{label}: optimized is lower ({delta_value:+.4f})")
    else:
        st.info(f"{label}: no change")


def _codon_diff_indexes(seq_a: str, seq_b: str) -> Tuple[List[int], int]:
    a = (seq_a or "").strip().upper()
    b = (seq_b or "").strip().upper()
    common_len = min(len(a), len(b))
    common_len -= common_len % 3
    if common_len <= 0:
        return [], 0

    diff_indexes: List[int] = []
    for i in range(0, common_len, 3):
        codon_index = i // 3
        if a[i : i + 3] != b[i : i + 3]:
            diff_indexes.append(codon_index)
    return diff_indexes, common_len // 3


def _render_stylized_dna_track(
    title: str,
    dna_sequence: str,
    tone: str,
    diff_indexes: Optional[List[int]] = None,
    max_codons: int = 48,
) -> None:
    seq = (dna_sequence or "").strip().upper()
    codons = [seq[i : i + 3] for i in range(0, len(seq) - (len(seq) % 3), 3)]
    shown_codons = codons[:max_codons]
    diff_set = set(diff_indexes or [])

    tone_class = "impact-optimized" if tone == "optimized" else "impact-naive"
    span_html_parts: List[str] = []
    for idx, codon in enumerate(shown_codons):
        css_classes = f"impact-codon {tone_class}"
        if idx in diff_set:
            css_classes += " impact-diff"
        span_html_parts.append(f"<span class='{css_classes}'>{html.escape(codon)}</span>")

    st.markdown(
        (
            "<div class='impact-stage'>"
            f"<div class='impact-stage-title'>{html.escape(title)}</div>"
            "<div class='impact-codon-track'>"
            f"{''.join(span_html_parts) if span_html_parts else 'N/A'}"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if len(codons) > max_codons:
        st.caption(f"Showing first {max_codons} codons for readability.")


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_download_pdb(pdb_url: str) -> str:
    return fetch_pdb_text(pdb_url, timeout_sec=20)


def _build_3d_view_html(pdb_text: str, color_by_hydrophobicity: bool) -> Optional[str]:
    if py3Dmol is None or not pdb_text:
        return None

    view = py3Dmol.view(width=900, height=520)
    view.addModel(pdb_text, "pdb")

    if color_by_hydrophobicity:
        view.setStyle(
            {
                "cartoon": {
                    "colorscheme": {
                        "prop": "b",
                        "gradient": "roygb",
                        "min": 0,
                        "max": 100,
                    }
                }
            }
        )
    else:
        view.setStyle({"cartoon": {"color": "spectrum"}})

    view.setBackgroundColor("white")
    view.zoomTo()
    return view._make_html()


def _build_impact_3d_view_html(
    pdb_text: str,
    color_by_hydrophobicity: bool,
) -> Optional[str]:
    if py3Dmol is None or not pdb_text:
        return None

    view = py3Dmol.view(width=420, height=420)
    view.addModel(pdb_text, "pdb")

    if color_by_hydrophobicity:
        view.setStyle(
            {
                "cartoon": {
                    "colorscheme": {
                        "prop": "b",
                        "gradient": "roygb",
                        "min": 0,
                        "max": 100,
                    },
                    "opacity": 0.95,
                }
            }
        )
    else:
        view.setStyle({"cartoon": {"color": "#cbd5e1", "opacity": 0.9}})
        view.addStyle({"ss": "h"}, {"cartoon": {"color": "#ef4444"}})
        view.addStyle({"ss": "s"}, {"cartoon": {"color": "#2563eb"}})
        view.addStyle({"ss": "c"}, {"cartoon": {"color": "#10b981"}})

    view.setBackgroundColor("#f8fafc")
    view.zoomTo()
    model_html = view._make_html()
    return (
        "<div style='width:100%; display:flex; justify-content:center; align-items:center;'>"
        f"{model_html}"
        "</div>"
    )


def _safe_text(value: Any, default: str = "N/A") -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return default
    return text


def _first_non_empty_text(series: pd.Series, default: str = "N/A") -> str:
    for value in series.tolist():
        if value is None or pd.isna(value):
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return default


def _confidence_band(confidence_value: Any) -> str:
    confidence = _safe_float(confidence_value, default=-1.0)
    if confidence < 0:
        return "Unknown"
    if confidence >= 80:
        return "High"
    if confidence >= 60:
        return "Moderate"
    if confidence >= 40:
        return "Low-moderate"
    return "Low"


def _render_info_card(title: str, fields: List[Tuple[str, str]]) -> None:
    rows_html = "".join(
        (
            "<div class='card-row'>"
            f"<span class='card-key'>{html.escape(label)}</span>"
            f"<span class='card-value'>{html.escape(value)}</span>"
            "</div>"
        )
        for label, value in fields
    )
    st.markdown(
        (
            "<div class='ux-card'>"
            f"<div class='ux-card-title'>{html.escape(title)}</div>"
            f"{rows_html}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _suggested_limit_value(expected_volume: str, fallback: int) -> int:
    volume = (expected_volume or "").strip().lower()
    return {"small": 20, "medium": 60, "large": 150}.get(volume, fallback)


def _get_keyword_suggestions(query: str) -> List[Dict[str, str]]:
    return _get_keyword_suggestions_impl(query)


def _get_all_keyword_suggestions() -> List[Dict[str, str]]:
    return _get_all_keyword_suggestions_impl()


def _estimate_keyword_volume(keyword: str) -> str:
    return _estimate_keyword_volume_impl(keyword)


_KEYWORD_SEARCHBOX_STYLE = {
    "clear": {
        "clearable": "always",
        "width": 18,
        "height": 18,
    },
    "dropdown": {
        "width": 24,
        "height": 24,
        "rotate": True,
        "fill": "#5f6368",
    },
    "searchbox": {
        "control": {
            "backgroundColor": "#ffffff",
            "borderColor": "#dadce0",
            "borderRadius": 22,
            "boxShadow": "0 1px 2px rgba(60, 64, 67, 0.15)",
            "minHeight": 44,
        },
        "input": {
            "color": "#202124",
            "fontSize": 15,
        },
        "menu": {
            "backgroundColor": "#ffffff",
            "borderColor": "#e5e7eb",
            "borderRadius": 12,
            "boxShadow": "0 8px 24px rgba(60, 64, 67, 0.18)",
            "marginTop": 4,
            "overflow": "hidden",
        },
        "menuList": {
            "backgroundColor": "#ffffff",
            "paddingTop": 4,
            "paddingBottom": 4,
        },
        "option": {
            "backgroundColor": "#ffffff",
            "color": "#111827",
            "fontSize": 14,
            "lineHeight": 1.35,
            "minHeight": 52,
            "padding": "9px 14px",
            "whiteSpace": "pre-line",
            "highlightColor": "#0f172a",
        },
        "placeholder": {
            "color": "#6b7280",
        },
        "singleValue": {
            "color": "#202124",
            "fontSize": 15,
        },
    },
}


def _format_keyword_suggestion_label(suggestion: Dict[str, str]) -> str:
    keyword = suggestion.get("keyword", "").strip()
    description = suggestion.get("description", "No description available.").strip()
    expected_volume = suggestion.get("expected_volume", "unknown").strip()
    suggested_limit = suggestion.get("suggested_limit", "N/A").strip()
    return f"{keyword}\n{description} | {expected_volume} volume | limit {suggested_limit}"


def _find_keyword_suggestion(keyword: str) -> Optional[Dict[str, str]]:
    keyword_text = (keyword or "").strip().lower()
    if not keyword_text:
        return None
    for suggestion in _get_all_keyword_suggestions():
        if suggestion.get("keyword", "").strip().lower() == keyword_text:
            return suggestion
    return None


def _search_protein_suggestions(searchterm: str) -> List[Tuple[str, Dict[str, str]]]:
    term = (searchterm or "").strip()
    suggestions = _get_keyword_suggestions(term)
    st.session_state["pipeline_keyword_search_query"] = term
    st.session_state["pipeline_keyword_search_match_count"] = len(suggestions)
    return [(_format_keyword_suggestion_label(suggestion), suggestion) for suggestion in suggestions]


def _coerce_keyword_searchbox_value(selected: Any) -> Tuple[str, Optional[Dict[str, str]], bool]:
    if isinstance(selected, dict):
        keyword = str(selected.get("keyword", "")).strip()
        return keyword, selected if keyword else None, bool(keyword)

    selected_text = str(selected or "").strip()
    if not selected_text:
        return "", None, False

    keyword = selected_text.splitlines()[0].split(" | ", 1)[0].strip()
    suggestion = _find_keyword_suggestion(keyword)
    return keyword, suggestion, False


def _rerun_streamlit_app() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def _render_keyword_no_match_message() -> None:
    query = str(st.session_state.get("pipeline_keyword_search_query", "")).strip()
    match_count = int(st.session_state.get("pipeline_keyword_search_match_count", 0) or 0)
    if len(query) >= 2 and match_count == 0:
        st.caption("No local suggestion found. You can still run a custom UniProt query.")


def _store_pipeline_keyword(
    keyword: str,
    suggestion: Optional[Dict[str, str]],
    keyword_state_key: str,
    limit_state_key: str,
    default_limit: int,
    update_limit: bool,
) -> None:
    keyword = (keyword or "").strip()
    if not keyword:
        return

    st.session_state[keyword_state_key] = keyword
    if suggestion:
        expected_volume = suggestion.get("expected_volume", "")
        st.session_state["keyword_suggestion_volume"] = _estimate_keyword_volume(keyword)
        st.session_state["keyword_suggestion_selected"] = keyword
        if update_limit:
            st.session_state[limit_state_key] = _suggested_limit_value(expected_volume, default_limit)


def _render_keyword_selectbox_fallback(
    keyword_state_key: str,
    limit_state_key: str,
    default_limit: int,
) -> str:
    suggestions = _get_all_keyword_suggestions()
    options = [suggestion.get("keyword", "") for suggestion in suggestions if suggestion.get("keyword")]
    suggestion_by_keyword = {option.lower(): _find_keyword_suggestion(option) for option in options}
    current_keyword = str(st.session_state.get(keyword_state_key, "") or "").strip()
    selected_index = next(
        (idx for idx, option in enumerate(options) if option.lower() == current_keyword.lower()),
        None,
    )

    selected_keyword = st.selectbox(
        "keyword",
        options=options,
        index=selected_index,
        placeholder="Type a protein keyword...",
        key="pipeline_keyword_selectbox_fallback",
        accept_new_options=True,
        format_func=lambda option: _format_keyword_suggestion_label(
            suggestion_by_keyword.get(str(option).lower()) or {"keyword": str(option)}
        ).replace("\n", " - "),
    )
    fallback_keyword = str(selected_keyword or current_keyword).strip()
    _store_pipeline_keyword(
        fallback_keyword,
        suggestion_by_keyword.get(fallback_keyword.lower()),
        keyword_state_key=keyword_state_key,
        limit_state_key=limit_state_key,
        default_limit=default_limit,
        update_limit=bool(suggestion_by_keyword.get(fallback_keyword.lower())),
    )
    st.caption("Autocomplete package is not installed yet; using Streamlit's searchable dropdown fallback.")
    return str(st.session_state.get(keyword_state_key, fallback_keyword))


def _render_keyword_searchbox(
    keyword_state_key: str,
    limit_state_key: str,
    default_limit: int,
) -> str:
    if st_searchbox is None:
        return _render_keyword_selectbox_fallback(
            keyword_state_key=keyword_state_key,
            limit_state_key=limit_state_key,
            default_limit=default_limit,
        )

    current_keyword = str(st.session_state.get(keyword_state_key, "") or "").strip()
    nonce = int(st.session_state.get("pipeline_keyword_searchbox_nonce", 0) or 0)
    selected = st_searchbox(
        _search_protein_suggestions,
        label="keyword",
        placeholder="Type a protein keyword...",
        key=f"pipeline_keyword_searchbox_{nonce}",
        default=current_keyword,
        default_searchterm=current_keyword,
        default_use_searchterm=True,
        clear_on_submit=False,
        edit_after_submit="option",
        debounce=100,
        style_overrides=_KEYWORD_SEARCHBOX_STYLE,
    )

    keyword, suggestion, clicked_suggestion = _coerce_keyword_searchbox_value(selected)
    _store_pipeline_keyword(
        keyword,
        suggestion,
        keyword_state_key=keyword_state_key,
        limit_state_key=limit_state_key,
        default_limit=default_limit,
        update_limit=clicked_suggestion,
    )

    if clicked_suggestion:
        st.session_state["pipeline_keyword_searchbox_nonce"] = nonce + 1
        _rerun_streamlit_app()

    _render_keyword_no_match_message()
    return str(st.session_state.get(keyword_state_key, current_keyword))


def _infer_lightweight_structure_annotations(
    protein_length: int,
    helix_ratio: float,
    sheet_ratio: float,
    coil_ratio: float,
) -> List[Tuple[str, str]]:
    length = max(int(protein_length), 1)
    annotations: List[Tuple[str, str]] = []

    if helix_ratio >= 0.35 and helix_ratio >= sheet_ratio:
        helix_end = max(1, int(length * min(0.8, 0.35 + helix_ratio * 0.45)))
        annotations.append(
            (
                "Helix-rich region",
                f"Likely helical dominance around residues 1-{helix_end}.",
            )
        )

    if sheet_ratio >= 0.25 and sheet_ratio >= helix_ratio:
        sheet_start = max(1, int(length * 0.2))
        sheet_end = max(sheet_start + 1, int(length * min(0.9, 0.4 + sheet_ratio * 0.55)))
        annotations.append(
            (
                "Sheet-rich region",
                f"Likely sheet-enriched segment around residues {sheet_start}-{sheet_end}.",
            )
        )

    if coil_ratio >= 0.3:
        tail_start = max(1, int(length * 0.78))
        annotations.append(
            (
                "Flexible tail / loop-rich region",
                f"Higher flexibility is expected near residues {tail_start}-{length}.",
            )
        )

    core_start = max(1, int(length * 0.12))
    core_end = max(core_start + 1, int(length * max(0.55, 0.82 - min(coil_ratio, 0.5) * 0.3)))
    annotations.append(
        (
            "Structured core",
            f"Most compact structural core is expected around residues {core_start}-{core_end}.",
        )
    )

    if len(annotations) == 1:
        annotations.insert(
            0,
            (
                "Loop",
                "No strong helix/sheet bias detected; fold appears mixed with loop transitions.",
            ),
        )

    return annotations


def _render_result_interpretation_note() -> None:
    st.markdown("### Result Interpretation Note")
    st.info(
        "This is a proxy model combining sequence and structural descriptors. "
        "Outputs are exploratory computational signals and not wet-lab validated biological prediction."
    )


def _render_dataset_scope_warning(df: pd.DataFrame, manifest: Dict[str, Any]) -> None:
    if df.empty:
        return

    keyword = str(manifest.get("keyword", "")).strip().lower()
    unique_accessions = df["protein_accession"].nunique() if "protein_accession" in df.columns else 0
    unique_names = df["protein_name"].nunique() if "protein_name" in df.columns else 0

    broad_terms = {"glucose", "metabolism", "enzyme", "receptor", "protein"}
    broad_keyword = keyword in broad_terms
    heterogeneous = unique_accessions >= 10 or unique_names >= 8

    if broad_keyword or heterogeneous:
        st.warning(
            "Dataset scope warning: this run appears heterogeneous (many distinct proteins). "
            "Use conclusions as exploratory trend analysis, not target-specific biological inference."
        )


def render_home_tab() -> None:
    st.markdown("<div class='main-header'>Plant DNA Intelligence Platform</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='sub-header'>Module 5 | Backend-Aligned Proxy Expression Workflow</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class='info-box'>
<strong>Scientific scope:</strong> This application analyzes sequence-derived proxy outputs from the backend pipeline.
It is for computational decision support and is <strong>not</strong> a wet-lab validated predictor.
</div>
""",
        unsafe_allow_html=True,
    )
    st.caption("This version integrates structural features directly into the ML model.")
    st.caption("Some host differences are simulated using predefined compatibility assumptions to create a realistic proxy-learning task.")
    st.caption("Model evaluation uses protein-grouped splits when regenerated with the current backend, avoiding the same protein in train and test.")
    st.caption("This interface focuses on end-to-end decision support from dataset generation to host recommendation.")

    with st.expander("How to read this app", expanded=True):
        st.markdown(
            """
1. A protein is a chain of amino acids with biological function.
2. A feature is a numeric descriptor extracted from DNA, codons, or structure.
3. The model predicts a simulated proxy expression score, not experimental biology.
4. Protein-grouped validation is used to make the ML evaluation more credible.
5. Use model comparison and feature importances to interpret trends, not to claim lab-level causality.
"""
        )

    info1, info2, info3 = st.columns(3)
    with info1:
        st.info(
            "Protein: sequence of amino acids. In this app, proteins come from UniProt and are the biological input."
        )
    with info2:
        st.info(
            "Feature: measurable descriptor. We combine codon metrics, protein chemistry, and 3D structure-derived signals."
        )
    with info3:
        st.info(
            "Prediction: simulated proxy expression score to compare design options across hosts under consistent assumptions."
        )

    st.markdown("### Workflow Overview")
    st.markdown(
        """
1. Run backend pipeline (keyword, protein limit, training options).
2. Load artifacts from latest_run_manifest.json.
3. Review quality checks and dataset structure.
4. Inspect model metrics when training is enabled.
5. Compare host recommendations using biologically grounded production scoring.
"""
    )

    st.markdown("### Artifacts This App Uses")
    st.markdown(
        """
- dataset_<keyword>.csv and dataset_<keyword>.json
- metadata_<keyword>.json
- metrics_<keyword>.json (when training is enabled)
- data_quality_report_<keyword>.json
- latest_run_manifest.json
"""
    )

    _render_result_interpretation_note()


def render_execution_tab() -> None:
    cfg = PipelineConfig()
    st.subheader("Pipeline Execution")

    keyword_key = "pipeline_keyword"
    limit_key = "pipeline_protein_limit"
    if keyword_key not in st.session_state:
        st.session_state[keyword_key] = cfg.default_keyword
    if limit_key not in st.session_state:
        st.session_state[limit_key] = cfg.default_protein_limit

    col1, col2, col3 = st.columns(3)
    with col1:
        keyword = _render_keyword_searchbox(
            keyword_state_key=keyword_key,
            limit_state_key=limit_key,
            default_limit=cfg.default_protein_limit,
        )
        protein_limit = st.number_input(
            "protein_limit",
            min_value=5,
            max_value=5000,
            step=5,
            key=limit_key,
        )
    with col2:
        output_dir = st.text_input("output_dir", value=cfg.output_dir)
        random_seed = st.number_input("random_seed", min_value=0, max_value=10_000_000, value=cfg.random_seed, step=1)
    with col3:
        train_enabled = st.checkbox("Enable model training", value=True)
        st.caption("Disable for faster artifact generation when metrics are not required.")

    st.caption(
        "This is a simulated proxy model, not experimental biology. "
        "DNA/codons affect translational efficiency, while 3D descriptors capture structural constraints."
    )
    st.caption(f"Reproducibility seed: {int(random_seed)}")

    resolved_output_dir = str(_abs_path(output_dir))
    st.caption(f"Resolved output directory: {resolved_output_dir}")

    run_col, load_col = st.columns([2, 1])

    with run_col:
        if st.button("Run Backend Pipeline", type="primary", use_container_width=True):
            with st.spinner("Running backend pipeline..."):
                try:
                    result = run_pipeline(
                        keyword=keyword,
                        protein_limit=int(protein_limit),
                        output_dir=resolved_output_dir,
                        random_seed=int(random_seed),
                        train=train_enabled,
                    )
                    st.session_state.pipeline_result = result

                    manifest_guess = result.get("manifest")
                    manifest_path = _resolve_manifest_path(
                        resolved_output_dir,
                        explicit_manifest=manifest_guess,
                        strict_explicit=True,
                    )
                    if not manifest_path:
                        st.error(
                            "Pipeline finished, but the explicit manifest returned by the run could not be found. "
                            f"Expected manifest path: {manifest_guess}"
                        )
                    else:
                        artifacts = _load_artifacts_from_manifest(manifest_path)
                        _store_artifacts(artifacts, load_mode="pipeline_run")
                        st.session_state.active_pipeline_params = {
                            "keyword": keyword,
                            "protein_limit": int(protein_limit),
                            "output_dir": resolved_output_dir,
                            "random_seed": int(random_seed),
                            "training_enabled": bool(train_enabled),
                        }
                        st.success("Pipeline completed and artifacts loaded.")
                except Exception as exc:
                    st.error(f"Pipeline execution failed: {exc}")

    with load_col:
        if st.button("Load Manifest", use_container_width=True):
            try:
                manifest_path = _resolve_manifest_path(
                    resolved_output_dir,
                    explicit_manifest=None,
                    strict_explicit=False,
                )
                if not manifest_path:
                    st.warning("No manifest found. Run the pipeline first.")
                else:
                    artifacts = _load_artifacts_from_manifest(manifest_path)
                    _store_artifacts(artifacts, load_mode="explicit_manifest_load")
                    st.session_state.active_pipeline_params = {
                        "keyword": artifacts.get("metadata", {}).get("keyword", "N/A"),
                        "protein_limit": artifacts.get("metadata", {}).get("protein_limit", "N/A"),
                        "output_dir": resolved_output_dir,
                        "random_seed": artifacts.get("metadata", {}).get("random_seed", "N/A"),
                        "training_enabled": artifacts.get("metadata", {}).get("training_enabled", "N/A"),
                    }
                    st.success(f"Loaded manifest: {manifest_path}")
            except Exception as exc:
                st.error(f"Failed to load artifacts: {exc}")

    if st.button("Clear loaded artifacts", use_container_width=True):
        _clear_loaded_artifacts()
        st.success("Loaded artifacts cleared for this session.")

    st.markdown("### Generated Artifacts")
    result = st.session_state.pipeline_result or {}
    manifest = st.session_state.manifest or {}
    artifact_paths = st.session_state.artifact_paths or {}

    if not result and not manifest:
        st.info("No pipeline run or artifact load in this session yet.")
        return

    rows = [
        {"artifact": "dataset_csv", "path": artifact_paths.get("dataset") or result.get("csv")},
        {"artifact": "dataset_json", "path": manifest.get("latest_json_path") or result.get("json")},
        {"artifact": "metadata_json", "path": artifact_paths.get("metadata") or result.get("metadata")},
        {"artifact": "metrics_json", "path": artifact_paths.get("metrics") or manifest.get("latest_metrics_path")},
        {"artifact": "quality_report_json", "path": artifact_paths.get("quality") or result.get("quality")},
        {"artifact": "manifest_json", "path": st.session_state.manifest_path or result.get("manifest")},
        {"artifact": "model_path", "path": manifest.get("latest_model_path")},
    ]

    artifact_df = pd.DataFrame(rows)
    artifact_df["path"] = artifact_df["path"].apply(lambda x: str(x) if x else "N/A")
    artifact_df["status"] = artifact_df["path"].apply(
        lambda p: "available" if p != "N/A" else "missing"
    )
    artifact_df["status"] = artifact_df["status"].map(
        {"available": "✅ available", "missing": "⚠ missing"}
    )
    artifact_df["filename"] = artifact_df["path"].apply(
        lambda p: Path(p).name if p != "N/A" else "N/A"
    )
    artifact_df = artifact_df[["artifact", "status", "filename", "path"]]
    st.dataframe(artifact_df, use_container_width=True, hide_index=True)

    st.markdown("### Loaded Paths")
    st.caption(f"Loaded manifest path: {st.session_state.manifest_path or 'N/A'}")
    st.caption(f"Loaded dataset path: {(artifact_paths or {}).get('dataset') or 'N/A'}")

    st.markdown("### Optional Downloads")
    dl_col1, dl_col2 = st.columns(2)

    dataset_file_path = artifact_paths.get("dataset")
    dataset_json_file_path = _resolve_manifest_relative_path(
        st.session_state.manifest_path,
        (st.session_state.manifest or {}).get("latest_json_path"),
    )
    metadata_file_path = artifact_paths.get("metadata")
    metrics_file_path = artifact_paths.get("metrics")
    quality_file_path = artifact_paths.get("quality")
    manifest_file_path = st.session_state.manifest_path

    with dl_col1:
        if dataset_file_path and Path(dataset_file_path).exists():
            st.download_button(
                label="Download dataset CSV",
                data=Path(dataset_file_path).read_bytes(),
                file_name=Path(dataset_file_path).name,
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.caption("Dataset CSV unavailable")

        if dataset_json_file_path and Path(dataset_json_file_path).exists():
            st.download_button(
                label="Download dataset JSON",
                data=Path(dataset_json_file_path).read_bytes(),
                file_name=Path(dataset_json_file_path).name,
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.caption("Dataset JSON unavailable")

        metadata_payload = _json_download_payload(st.session_state.metadata)
        st.download_button(
            label="Download metadata JSON",
            data=metadata_payload,
            file_name=Path(metadata_file_path).name if metadata_file_path else "metadata.json",
            mime="application/json",
            use_container_width=True,
        )

    with dl_col2:
        metrics_payload = _json_download_payload(st.session_state.metrics)
        st.download_button(
            label="Download metrics JSON",
            data=metrics_payload,
            file_name=Path(metrics_file_path).name if metrics_file_path else "metrics.json",
            mime="application/json",
            use_container_width=True,
        )

        quality_payload = _json_download_payload(st.session_state.quality)
        st.download_button(
            label="Download quality report JSON",
            data=quality_payload,
            file_name=Path(quality_file_path).name if quality_file_path else "quality_report.json",
            mime="application/json",
            use_container_width=True,
        )

        if manifest_file_path and Path(manifest_file_path).exists():
            st.download_button(
                label="Download run manifest JSON",
                data=Path(manifest_file_path).read_bytes(),
                file_name=Path(manifest_file_path).name,
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.caption("Run manifest unavailable")

    st.markdown("### Ethics Gate Export")
    st.caption(
        "Exports each optimized DNA sequence as 4-mer frequencies with the same columns as your colleague's "
        "ethics-model CSV: fichier, id, label, split, longueur, then AAAA through TTTT."
    )
    ethics_csv, ethics_message = _build_ethics_csv_from_dataset(st.session_state.get("dataset", pd.DataFrame()))
    if ethics_csv:
        st.download_button(
            label="Download ethics.csv",
            data=ethics_csv,
            file_name="ethics.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.caption(ethics_message)
        st.caption(
            "Note: label is set to -1 and split to test_unknown because these optimized DNA rows are meant "
            "to be predicted by the ethics model."
        )
    else:
        st.warning(ethics_message)

    _render_metadata_panel(st.session_state.metadata)


def render_quality_tab() -> None:
    st.subheader("Data Quality")

    quality = st.session_state.quality
    df = st.session_state["dataset"]

    if not quality and df.empty:
        st.info("Load artifacts first from the Pipeline Execution tab.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fetched Proteins", quality.get("fetched_proteins", "N/A"))
    col2.metric("Rows Generated", quality.get("rows_generated", len(df) if not df.empty else "N/A"))
    col3.metric("Rejected Proteins", quality.get("rejected_proteins_total", "N/A"))
    col4.metric("Rejection Rate", quality.get("rejection_rate", "N/A"))

    summary = quality.get("summary", {}) if quality else {}
    if summary:
        st.markdown("### Structured Quality Summary")
        sq1, sq2, sq3 = st.columns(3)
        with sq1:
            st.markdown("**Protein Filtering**")
            st.json(summary.get("protein_filtering", {}))
        with sq2:
            st.markdown("**DNA QC**")
            st.json(summary.get("dna_qc", {}))
        with sq3:
            st.markdown("**Output Summary**")
            st.json(summary.get("output_summary", {}))

    st.markdown("### Host-Level Row Summary")
    rows_per_host = quality.get("rows_per_plant_host", {}) if quality else {}
    if rows_per_host:
        host_df = pd.DataFrame(
            [{"plant_host": host, "rows": count} for host, count in rows_per_host.items()]
        ).sort_values("rows", ascending=False)
    elif not df.empty and "plant_host" in df.columns:
        host_df = (
            df.groupby("plant_host", as_index=False)
            .size()
            .rename(columns={"size": "rows"})
            .sort_values("rows", ascending=False)
        )
    else:
        host_df = pd.DataFrame()

    if host_df.empty:
        st.info("No host-level rows available.")
    else:
        st.dataframe(host_df, use_container_width=True, hide_index=True)
        fig = px.bar(host_df, x="plant_host", y="rows", title="Rows per Host")
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Show raw quality JSON"):
        if quality:
            st.json(quality)
        else:
            st.info("No quality JSON loaded.")


def render_dataset_tab() -> None:
    st.subheader("Dataset Analysis")
    if "dataset" not in st.session_state:
        st.warning("Dataset not loaded. Run the pipeline or load a manifest first.")
        return

    df = st.session_state["dataset"]
    if df is None or df.empty:
        st.warning("Dataset is empty or unavailable. Check manifest paths and rerun pipeline.")
        return

    st.markdown("### Preview")
    st.dataframe(df.head(25), use_container_width=True)

    required = {"plant_host", "target_expression_score", "cai", "gc_content"}
    if not required.issubset(df.columns):
        st.warning(f"Missing required analysis columns: {sorted(required - set(df.columns))}")
        return

    _render_dataset_scope_warning(df, st.session_state.manifest or {})
    _render_result_interpretation_note()

    if _is_host_invariant_target(df):
        st.info(
            "The current target_expression_score is the same across hosts in this run. "
            "Host comparison on this metric is descriptive only and not evidence of host-specific biology."
        )

    filtered_df = df.copy()
    with st.expander("Optional dataset filters", expanded=False):
        host_options = sorted(filtered_df["plant_host"].dropna().unique().tolist())
        selected_hosts = st.multiselect(
            "plant_host",
            options=host_options,
            default=host_options,
        )

        score_series = pd.to_numeric(filtered_df["target_expression_score"], errors="coerce").dropna()
        if not score_series.empty:
            min_score = float(score_series.min())
            max_score = float(score_series.max())
            selected_range = st.slider(
                "target_expression_score range",
                min_value=min_score,
                max_value=max_score,
                value=(min_score, max_score),
            )
        else:
            selected_range = (None, None)

    if selected_hosts:
        filtered_df = filtered_df[filtered_df["plant_host"].isin(selected_hosts)].copy()

    if selected_range[0] is not None:
        filtered_df = filtered_df[
            filtered_df["target_expression_score"].between(selected_range[0], selected_range[1])
        ].copy()

    st.caption(f"Rows after filters: {len(filtered_df)}")

    if filtered_df.empty:
        st.warning("No rows match current filters. Adjust filters to continue analysis.")
        return

    st.markdown("### Host Comparison")
    summary = (
        filtered_df.groupby("plant_host", as_index=False)
        .agg(
            rows=("plant_host", "count"),
            mean_proxy_target=("target_expression_score", "mean"),
            mean_cai=("cai", "mean"),
            mean_gc_content=("gc_content", "mean"),
        )
        .sort_values("mean_proxy_target", ascending=False)
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)

    if summary["mean_proxy_target"].round(8).nunique() <= 1:
        st.info("Host mean target score is constant in this run and is not informative for comparison.")
    else:
        fig1 = px.bar(
            summary,
            x="plant_host",
            y="mean_proxy_target",
            title="Mean Proxy Target by Host",
            labels={"mean_proxy_target": "target_expression_score"},
        )
        st.plotly_chart(fig1, use_container_width=True)

    cai_constant = _is_non_informative_series(filtered_df["cai"])
    target_constant = _is_non_informative_series(filtered_df["target_expression_score"])
    if cai_constant or target_constant:
        st.info("CAI vs target scatter is suppressed because one axis is constant in the current run.")
    else:
        fig2 = px.scatter(
            filtered_df,
            x="cai",
            y="target_expression_score",
            color="plant_host",
            hover_data=["protein_accession"] if "protein_accession" in filtered_df.columns else None,
            title="CAI vs Proxy Target by Host",
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### Additional Distributions")
    if target_constant:
        st.info("Target score distribution is constant in the current run and is not informative for comparison.")
    else:
        fig3 = px.histogram(
            filtered_df,
            x="target_expression_score",
            nbins=25,
            color="plant_host",
            title="Distribution of Target Expression Score",
        )
        st.plotly_chart(fig3, use_container_width=True)

    if cai_constant:
        st.info("CAI is constant in the current run and is not informative for comparison.")
    else:
        fig4 = px.box(
            filtered_df,
            x="plant_host",
            y="cai",
            color="plant_host",
            title="CAI Distribution by Host",
        )
        st.plotly_chart(fig4, use_container_width=True)

    if {"gc_content", "gc3_content"}.issubset(filtered_df.columns):
        gc_constant = _is_non_informative_series(filtered_df["gc_content"])
        gc3_constant = _is_non_informative_series(filtered_df["gc3_content"])
        if gc_constant or gc3_constant:
            st.info("GC vs GC3 scatter is suppressed because one axis is constant in the current run.")
        else:
            fig5 = px.scatter(
                filtered_df,
                x="gc_content",
                y="gc3_content",
                color="plant_host",
                title="GC Content vs GC3 Content",
            )
            st.plotly_chart(fig5, use_container_width=True)


def render_structure_tab() -> None:
    st.subheader("3D Protein Structure")
    st.info("This version integrates structural features directly into the ML model.")
    st.caption(
        "Role of structure in this app: secondary-structure and stability descriptors are used as ML inputs alongside DNA/codon features."
    )

    df = st.session_state["dataset"]
    if df.empty:
        st.info("Load artifacts first from the Pipeline Execution tab.")
        return

    accession_col = _accession_column_name(df)
    if accession_col is None:
        st.warning("No accession column found. Expected accession or protein_accession.")
        return

    accessions = sorted(df[accession_col].dropna().astype(str).unique().tolist())
    if not accessions:
        st.warning("No protein accession available in dataset.")
        return

    accession_labels: Dict[str, str] = {}
    for accession in accessions:
        rows_for_accession = df[df[accession_col].astype(str) == accession]
        if "protein_name" in rows_for_accession.columns:
            protein_name = _first_non_empty_text(rows_for_accession["protein_name"], default="Unknown protein")
        else:
            protein_name = "Unknown protein"
        accession_labels[accession] = f"{accession} — {protein_name}"

    selected_accession = st.selectbox(
        "Select protein",
        options=accessions,
        format_func=lambda accession: accession_labels.get(accession, accession),
    )
    selected_rows = df[df[accession_col].astype(str) == selected_accession].copy()
    if selected_rows.empty:
        st.warning("No rows found for selected accession.")
        return

    host_options = sorted(selected_rows["plant_host"].dropna().astype(str).unique().tolist()) if "plant_host" in selected_rows.columns else []
    selected_host = (
        st.selectbox(
            "Select plant host context",
            options=host_options,
            help="Switch host to compare host-specific optimized DNA while keeping the same protein structure.",
        )
        if host_options
        else None
    )
    if selected_host:
        host_rows = selected_rows[selected_rows["plant_host"].astype(str) == selected_host]
        selected_row = host_rows.iloc[0] if not host_rows.empty else selected_rows.iloc[0]
    else:
        selected_row = selected_rows.iloc[0]

    color_by_hydrophobicity = st.checkbox("Color by hydrophobicity", value=True)

    pdb_url = str(selected_row.get("pdb_url", "") or "").strip()
    pdb_id = str(selected_row.get("pdb_id", "") or f"MOCK-{selected_accession}")
    protein_length = _safe_int(
        selected_row.get("protein_length", selected_row.get("sequence_length_aa", 1)),
        default=1,
    )
    structure_source = str(selected_row.get("structure_source", "mock") or "mock")
    structure_confidence_raw = selected_row.get("structure_confidence", "")

    protein_name = _safe_text(selected_row.get("protein_name"), default="Unknown protein")
    organism = _safe_text(selected_row.get("organism"), default="Unknown organism")
    selected_host_label = _safe_text(selected_host or selected_row.get("plant_host"), default="N/A")
    confidence_value = _safe_text(structure_confidence_raw, default="N/A")
    confidence_band = _confidence_band(structure_confidence_raw)
    structure_source_label = {
        "alphafold": "AlphaFold prediction",
        "mock_fallback": "Deterministic mock fallback",
        "mock": "Deterministic mock fallback",
    }.get(structure_source.lower(), structure_source)

    dna_sequence = str(selected_row.get("dna_sequence", "") or "").strip().upper()
    dna_length = _safe_int(selected_row.get("sequence_length_nt"), default=len(dna_sequence))
    if dna_length <= 0:
        dna_length = len(dna_sequence)
    dna_preview = f"{dna_sequence[:60]}..." if len(dna_sequence) > 60 else (dna_sequence or "N/A")

    st.info(
        "The 3D protein structure is linked to the protein itself. Changing the plant host mainly changes the optimized DNA/codon design, not the protein fold shown here."
    )

    pdb_text = _cached_download_pdb(pdb_url) if pdb_url else ""
    if not pdb_text:
        pdb_text = generate_mock_pdb_from_length(protein_length, accession=selected_accession)
        structure_source = "mock_fallback" if pdb_url else "mock"
        structure_source_label = "Deterministic mock fallback"

    if color_by_hydrophobicity:
        pdb_text = apply_hydrophobicity_bfactor(pdb_text)

    viewer_col, explainer_col = st.columns([2.2, 1.1])
    with viewer_col:
        if py3Dmol is None:
            st.error("py3Dmol is not installed. Install dependencies from requirements.txt to enable 3D viewing.")
        else:
            viewer_html = _build_3d_view_html(pdb_text, color_by_hydrophobicity=color_by_hydrophobicity)
            if viewer_html:
                components.html(viewer_html, height=540)
            else:
                st.warning("PDB content unavailable for rendering.")

    with explainer_col:
        _render_info_card(
            "3D structure guide",
            [
                ("Helix", "Spiral segment, often stable."),
                ("Sheet", "Flat beta-sheet segment."),
                ("Loop", "Connector between ordered segments."),
                ("Flexible region", "Often loop-rich and more mobile."),
                ("Structured core", "More compact and stable center."),
            ],
        )
        legend_text = (
            "Cartoon style with hydrophobicity coloring: cooler colors indicate lower hydrophobic tendency, warmer colors indicate higher tendency."
            if color_by_hydrophobicity
            else "Cartoon style with spectrum coloring: colors separate regions along the chain for readability."
        )
        st.caption(f"Legend: {legend_text}")

    source_label = structure_source.lower()
    if source_label == "alphafold":
        st.success("3D source: AlphaFold predicted structure")
    elif source_label == "mock_fallback":
        st.warning("3D source: deterministic mock fallback (AlphaFold URL unavailable or not retrievable)")
    else:
        st.warning("3D source: deterministic mock fallback (no AlphaFold structure in this run)")
    st.caption(
        "Mock fallback structures are deterministic placeholders for feature continuity and visualization; "
        "they are not experimental or high-fidelity folding predictions."
    )

    context_col1, context_col2, context_col3 = st.columns(3)
    with context_col1:
        _render_info_card(
            "Protein info",
            [
                ("Accession", selected_accession),
                ("Protein name", protein_name),
                ("Organism", organism),
            ],
        )
    with context_col2:
        _render_info_card(
            "Structure info",
            [
                ("Source", structure_source_label),
                ("PDB ID", _safe_text(pdb_id)),
                ("Confidence", f"{confidence_value} ({confidence_band})"),
            ],
        )
    with context_col3:
        _render_info_card(
            "Host-specific DNA info",
            [
                ("Selected plant host", selected_host_label),
                ("Generated DNA length", f"{dna_length} nt"),
                ("Preview", "First 60 nucleotides shown below"),
            ],
        )
        st.code(dna_preview)
        if len(host_options) > 1:
            st.caption("Tip: switch the plant host above to verify host-specific DNA redesign.")

    helix_ratio = _safe_float(selected_row.get("helix_ratio"))
    sheet_ratio = _safe_float(selected_row.get("sheet_ratio"))
    coil_ratio = _safe_float(selected_row.get("coil_ratio"))

    st.markdown("### Lightweight Structural Annotations")
    for annotation_title, annotation_text in _infer_lightweight_structure_annotations(
        protein_length=protein_length,
        helix_ratio=helix_ratio,
        sheet_ratio=sheet_ratio,
        coil_ratio=coil_ratio,
    ):
        st.markdown(f"- **{annotation_title}**: {annotation_text}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Helix ratio", f"{helix_ratio:.3f}")
    c2.metric("Sheet ratio", f"{sheet_ratio:.3f}")
    c3.metric("Hydrophobicity", f"{_safe_float(selected_row.get('hydrophobicity_score')):.3f}")
    c4.metric("Stability", f"{_safe_float(selected_row.get('stability_score')):.3f}")

    meta_left, meta_right = st.columns(2)
    with meta_left:
        st.caption(f"Structure source: {structure_source}")
        st.caption(f"PDB URL: {pdb_url if pdb_url else 'N/A'}")
    with meta_right:
        st.caption(f"PDB ID: {pdb_id}")
        st.caption(f"Structure confidence: {confidence_value}")

    st.markdown("### Secondary Structure Distribution")
    secondary_df = pd.DataFrame(
        {
            "structure": ["Helix", "Sheet", "Coil"],
            "ratio": [
                _safe_float(selected_row.get("helix_ratio")),
                _safe_float(selected_row.get("sheet_ratio")),
                coil_ratio,
            ],
        }
    )
    sec_fig = px.bar(
        secondary_df,
        x="structure",
        y="ratio",
        color="structure",
        title=f"Secondary Structure Ratios for {selected_accession}",
        range_y=[0, 1],
    )
    st.plotly_chart(sec_fig, use_container_width=True)

    st.markdown("### Plant Host Comparison")
    if "plant_host" in selected_rows.columns:
        host_compare = selected_rows.groupby("plant_host", as_index=False).agg(
            mean_proxy_target=("target_expression_score", "mean") if "target_expression_score" in selected_rows.columns else ("plant_host", "count"),
            mean_cai=("cai", "mean") if "cai" in selected_rows.columns else ("plant_host", "count"),
            rows=("plant_host", "count"),
        )
        st.dataframe(host_compare, use_container_width=True, hide_index=True)

        if "target_expression_score" in selected_rows.columns:
            host_fig = px.bar(
                host_compare,
                x="plant_host",
                y="mean_proxy_target",
                color="plant_host",
                title=f"Proxy Expression Comparison Across Plants ({selected_accession})",
            )
            st.plotly_chart(host_fig, use_container_width=True)
    else:
        st.info("Plant host comparison is not available in this dataset.")


def render_dna_optimization_comparison_tab() -> None:
    st.subheader("DNA Optimization Comparison")
    st.caption("Compare naive codon translation with host-optimized DNA for one protein and one plant host.")

    df = st.session_state["dataset"]
    if df.empty:
        st.info("Load artifacts first from the Pipeline Execution tab.")
        return

    accession_col = _accession_column_name(df)
    if accession_col is None:
        st.warning("No accession column found. Expected accession or protein_accession.")
        return

    required_columns = {
        "dna_sequence",
        "naive_dna_sequence",
        "cai",
        "naive_cai",
        "gc_content",
        "naive_gc_content",
        "target_expression_score",
    }
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        st.warning("You are likely viewing an older dataset generated before naive-vs-optimized DNA comparison was added.")
        st.caption(f"Missing columns: {', '.join(missing_columns)}")
        return

    accessions = sorted(df[accession_col].dropna().astype(str).unique().tolist())
    if not accessions:
        st.warning("No protein accession available in dataset.")
        return

    accession_labels: Dict[str, str] = {}
    for accession in accessions:
        rows_for_accession = df[df[accession_col].astype(str) == accession]
        if "protein_name" in rows_for_accession.columns:
            protein_name = _first_non_empty_text(rows_for_accession["protein_name"], default="Unknown protein")
        else:
            protein_name = "Unknown protein"
        accession_labels[accession] = f"{accession} — {protein_name}"

    selector_col1, selector_col2 = st.columns(2)
    with selector_col1:
        selected_accession = st.selectbox(
            "Select protein",
            options=accessions,
            format_func=lambda accession: accession_labels.get(accession, accession),
            key="dna_compare_accession",
        )

    selected_rows = df[df[accession_col].astype(str) == selected_accession].copy()
    host_options = sorted(selected_rows["plant_host"].dropna().astype(str).unique().tolist()) if "plant_host" in selected_rows.columns else []
    with selector_col2:
        selected_host = st.selectbox(
            "Select plant host",
            options=host_options,
            key="dna_compare_host",
        ) if host_options else None

    if selected_host:
        host_rows = selected_rows[selected_rows["plant_host"].astype(str) == selected_host]
        selected_row = host_rows.iloc[0] if not host_rows.empty else selected_rows.iloc[0]
    else:
        selected_row = selected_rows.iloc[0]

    protein_name = _safe_text(selected_row.get("protein_name"), default="Unknown protein")
    organism = _safe_text(selected_row.get("organism"), default="Unknown organism")
    plant_host = _safe_text(selected_host or selected_row.get("plant_host"), default="N/A")

    naive_dna_sequence = str(selected_row.get("naive_dna_sequence", "") or "").strip().upper()
    optimized_dna_sequence = str(selected_row.get("dna_sequence", "") or "").strip().upper()

    naive_cai = _safe_float(selected_row.get("naive_cai"))
    optimized_cai = _safe_float(selected_row.get("cai"))
    naive_gc = _safe_float(selected_row.get("naive_gc_content"))
    optimized_gc = _safe_float(selected_row.get("gc_content"))

    delta_cai = _safe_float(selected_row.get("delta_cai"), default=round(optimized_cai - naive_cai, 4))
    delta_gc = _safe_float(selected_row.get("delta_gc"), default=round(optimized_gc - naive_gc, 4))

    optimized_proxy = _safe_float(selected_row.get("target_expression_score"))
    naive_proxy_raw = selected_row.get("naive_proxy_expression_score")
    if naive_proxy_raw is not None and not pd.isna(naive_proxy_raw):
        naive_proxy = _safe_float(naive_proxy_raw)
    else:
        estimated_gain = max(0.0, (0.5 * max(delta_cai, 0.0)) + (0.2 * max(delta_gc, 0.0)))
        naive_proxy = round(max(0.0, optimized_proxy - estimated_gain), 4)
    delta_proxy = _safe_float(
        selected_row.get("delta_proxy_expression"),
        default=round(optimized_proxy - naive_proxy, 4),
    )

    codon_diff_raw = selected_row.get("codon_usage_difference_score")
    if codon_diff_raw is not None and not pd.isna(codon_diff_raw):
        codon_diff_score = _safe_float(codon_diff_raw)
    else:
        codon_diff_score = _codon_difference_score(naive_dna_sequence, optimized_dna_sequence)

    card_col1, card_col2, card_col3 = st.columns(3)
    with card_col1:
        _render_info_card(
            "Protein context",
            [
                ("Accession", selected_accession),
                ("Protein", protein_name),
                ("Organism", organism),
            ],
        )
    with card_col2:
        _render_info_card(
            "Plant context",
            [
                ("Selected plant host", plant_host),
                ("Naive DNA length", f"{len(naive_dna_sequence)} nt"),
                ("Optimized DNA length", f"{len(optimized_dna_sequence)} nt"),
            ],
        )
    with card_col3:
        _render_info_card(
            "Optimization summary",
            [
                ("Codon usage difference score", f"{codon_diff_score:.4f}"),
                ("Delta CAI", f"{delta_cai:+.4f}"),
                ("Delta GC", f"{delta_gc:+.4f}"),
            ],
        )

    st.markdown("### A. DNA Sequences")
    seq_col1, seq_col2 = st.columns(2)
    with seq_col1:
        st.markdown("**Naive DNA (first 60 nt)**")
        st.code(_dna_preview(naive_dna_sequence, width=60))
    with seq_col2:
        st.markdown("**Optimized DNA (first 60 nt)**")
        st.code(_dna_preview(optimized_dna_sequence, width=60))

    st.markdown("### B. Metrics Comparison")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric("CAI (optimized)", f"{optimized_cai:.4f}", delta=f"{delta_cai:+.4f} vs naive")
        st.caption(f"Naive CAI: {naive_cai:.4f}")
    with metric_col2:
        st.metric("GC content (optimized)", f"{optimized_gc:.4f}", delta=f"{delta_gc:+.4f} vs naive")
        st.caption(f"Naive GC content: {naive_gc:.4f}")
    with metric_col3:
        st.metric("Proxy expression (optimized)", f"{optimized_proxy:.4f}", delta=f"{delta_proxy:+.4f} vs naive")
        st.caption(f"Naive proxy expression: {naive_proxy:.4f}")

    indicator_col1, indicator_col2, indicator_col3 = st.columns(3)
    with indicator_col1:
        _render_improvement_indicator("CAI", delta_cai)
    with indicator_col2:
        _render_improvement_indicator("GC content", delta_gc)
    with indicator_col3:
        _render_improvement_indicator("Proxy expression", delta_proxy)

    st.markdown("### C. Visualization")
    comparison_df = pd.DataFrame(
        {
            "metric": ["CAI", "GC content", "Proxy expression score"],
            "naive": [naive_cai, naive_gc, naive_proxy],
            "optimized": [optimized_cai, optimized_gc, optimized_proxy],
        }
    )
    plot_df = comparison_df.melt(id_vars=["metric"], var_name="design", value_name="value")
    bar_fig = px.bar(
        plot_df,
        x="metric",
        y="value",
        color="design",
        barmode="group",
        title=f"Naive vs Optimized DNA Metrics ({selected_accession} | {plant_host})",
    )
    st.plotly_chart(bar_fig, use_container_width=True)

    st.markdown("### D. Interpretation")
    st.info(
        "Naive DNA uses generic codons.\n"
        "Optimized DNA adapts codon usage to the selected plant host.\n"
        "This improves translation efficiency and increases the proxy expression score."
    )


def render_dna_protein_impact_tab() -> None:
    st.subheader("DNA -> Protein Impact")
    st.caption("Interactive story view: compare naive DNA, protein structure, and optimized DNA for one host.")

    df = st.session_state["dataset"]
    if df.empty:
        st.info("Load artifacts first from the Pipeline Execution tab.")
        return

    accession_col = _accession_column_name(df)
    if accession_col is None:
        st.warning("No accession column found. Expected accession or protein_accession.")
        return

    required_columns = {
        "dna_sequence",
        "naive_dna_sequence",
        "cai",
        "naive_cai",
        "gc_content",
        "naive_gc_content",
        "target_expression_score",
    }
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        st.warning("This view needs naive-vs-optimized DNA columns. Please rerun the pipeline and reload artifacts.")
        st.caption(f"Missing columns: {', '.join(missing_columns)}")
        return

    accessions = sorted(df[accession_col].dropna().astype(str).unique().tolist())
    if not accessions:
        st.warning("No protein accession available in dataset.")
        return

    accession_labels: Dict[str, str] = {}
    for accession in accessions:
        rows_for_accession = df[df[accession_col].astype(str) == accession]
        if "protein_name" in rows_for_accession.columns:
            protein_name = _first_non_empty_text(rows_for_accession["protein_name"], default="Unknown protein")
        else:
            protein_name = "Unknown protein"
        accession_labels[accession] = f"{accession} — {protein_name}"

    selector_col1, selector_col2, selector_col3 = st.columns([1.35, 1.25, 1.0])
    with selector_col1:
        selected_accession = st.selectbox(
            "Protein",
            options=accessions,
            format_func=lambda accession: accession_labels.get(accession, accession),
            key="impact_accession",
        )

    selected_rows = df[df[accession_col].astype(str) == selected_accession].copy()
    host_options = (
        sorted(selected_rows["plant_host"].dropna().astype(str).unique().tolist())
        if "plant_host" in selected_rows.columns
        else []
    )

    with selector_col2:
        selected_host = (
            st.selectbox("Plant host", options=host_options, key="impact_host") if host_options else None
        )

    with selector_col3:
        color_by_hydrophobicity = st.checkbox("Hydrophobicity colors", value=True, key="impact_hydro")

    if selected_host:
        host_rows = selected_rows[selected_rows["plant_host"].astype(str) == selected_host]
        selected_row = host_rows.iloc[0] if not host_rows.empty else selected_rows.iloc[0]
    else:
        selected_row = selected_rows.iloc[0]

    protein_name = _safe_text(selected_row.get("protein_name"), default="Unknown protein")
    plant_host = _safe_text(selected_host or selected_row.get("plant_host"), default="N/A")

    naive_dna_sequence = str(selected_row.get("naive_dna_sequence", "") or "").strip().upper()
    optimized_dna_sequence = str(selected_row.get("dna_sequence", "") or "").strip().upper()

    naive_cai = _safe_float(selected_row.get("naive_cai"))
    optimized_cai = _safe_float(selected_row.get("cai"))
    naive_gc = _safe_float(selected_row.get("naive_gc_content"))
    optimized_gc = _safe_float(selected_row.get("gc_content"))

    optimized_proxy = _safe_float(selected_row.get("target_expression_score"))
    naive_proxy_raw = selected_row.get("naive_proxy_expression_score")
    if naive_proxy_raw is not None and not pd.isna(naive_proxy_raw):
        naive_proxy = _safe_float(naive_proxy_raw)
    else:
        estimated_gain = max(0.0, (0.5 * max(optimized_cai - naive_cai, 0.0)) + (0.2 * max(optimized_gc - naive_gc, 0.0)))
        naive_proxy = round(max(0.0, optimized_proxy - estimated_gain), 4)

    delta_cai = round(optimized_cai - naive_cai, 4)
    delta_gc = round(optimized_gc - naive_gc, 4)
    delta_proxy = round(optimized_proxy - naive_proxy, 4)

    diff_indexes, total_codons = _codon_diff_indexes(naive_dna_sequence, optimized_dna_sequence)
    diff_percent = (len(diff_indexes) / total_codons * 100.0) if total_codons > 0 else 0.0

    st.markdown("### Visual Flow")
    flow_col1, flow_col2, flow_col3, flow_col4, flow_col5 = st.columns([1.75, 0.2, 2.3, 0.2, 1.75])
    with flow_col1:
        _render_stylized_dna_track(
            title="Naive DNA",
            dna_sequence=naive_dna_sequence,
            tone="naive",
            diff_indexes=diff_indexes,
        )
    with flow_col2:
        st.markdown("<div class='impact-arrow'>-></div>", unsafe_allow_html=True)
    with flow_col3:
        st.markdown("<div class='impact-stage-title' style='text-align:center;'>Protein 3D</div>", unsafe_allow_html=True)

        pdb_url = str(selected_row.get("pdb_url", "") or "").strip()
        protein_length = _safe_int(
            selected_row.get("protein_length", selected_row.get("sequence_length_aa", 1)),
            default=1,
        )
        pdb_text = _cached_download_pdb(pdb_url) if pdb_url else ""
        if not pdb_text:
            pdb_text = generate_mock_pdb_from_length(protein_length, accession=selected_accession)

        if color_by_hydrophobicity:
            pdb_text = apply_hydrophobicity_bfactor(pdb_text)

        if py3Dmol is None:
            st.error("py3Dmol is not installed. Install dependencies from requirements.txt to enable 3D viewing.")
        else:
            viewer_html = _build_impact_3d_view_html(
                pdb_text=pdb_text,
                color_by_hydrophobicity=color_by_hydrophobicity,
            )
            if viewer_html:
                components.html(viewer_html, height=440)
            else:
                st.warning("PDB content unavailable for rendering.")

        st.markdown(
            "<div class='impact-legend-row'>"
            "<span class='impact-chip'>Helix</span>"
            "<span class='impact-chip'>Sheet</span>"
            "<span class='impact-chip'>Loop</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    with flow_col4:
        st.markdown("<div class='impact-arrow'>-></div>", unsafe_allow_html=True)
    with flow_col5:
        _render_stylized_dna_track(
            title="Optimized DNA",
            dna_sequence=optimized_dna_sequence,
            tone="optimized",
            diff_indexes=diff_indexes,
        )

    st.markdown("### Codon Difference")
    diff_col1, diff_col2, diff_col3 = st.columns(3)
    diff_col1.metric("Different codons", f"{len(diff_indexes)} / {total_codons}")
    diff_col2.metric("Difference percentage", f"{diff_percent:.1f}%")
    diff_col3.metric("Selected host", plant_host)

    st.markdown("### DNA -> Translation -> Protein")
    st.markdown(
        (
            "<div class='impact-concept'>"
            "<div class='impact-concept-title'>DNA -> Translation -> Protein</div>"
            "<div class='impact-concept-line'>Naive DNA: low efficiency</div>"
            "<div class='impact-concept-line'>Optimized DNA: high efficiency</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown("### Metrics Comparison")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric("CAI (optimized)", f"{optimized_cai:.4f}", delta=f"{delta_cai:+.4f} vs naive")
    with metric_col2:
        st.metric("GC content (optimized)", f"{optimized_gc:.4f}", delta=f"{delta_gc:+.4f} vs naive")
    with metric_col3:
        st.metric("Proxy score (optimized)", f"{optimized_proxy:.4f}", delta=f"{delta_proxy:+.4f} vs naive")

    comparison_df = pd.DataFrame(
        {
            "metric": ["CAI", "GC content", "Proxy expression score"],
            "naive": [naive_cai, naive_gc, naive_proxy],
            "optimized": [optimized_cai, optimized_gc, optimized_proxy],
        }
    )
    plot_df = comparison_df.melt(id_vars=["metric"], var_name="design", value_name="value")
    fig = px.bar(
        plot_df,
        x="metric",
        y="value",
        color="design",
        barmode="group",
        color_discrete_map={"naive": "#fb7185", "optimized": "#22c55e"},
        title=f"Naive vs Optimized DNA ({selected_accession} | {plant_host})",
    )
    st.plotly_chart(fig, use_container_width=True)

    if abs(naive_proxy) > 1e-9:
        improvement_percent = ((optimized_proxy - naive_proxy) / abs(naive_proxy)) * 100.0
    else:
        improvement_percent = 100.0 if optimized_proxy > 0 else 0.0

    st.success(
        f"Codon optimization improved expression efficiency by {improvement_percent:.1f}% for this host."
    )
    st.caption(f"Story context: {selected_accession} — {protein_name}")


def render_dna_fusion_tab() -> None:
    st.subheader("DNA Optimization + DNA -> Protein Impact")
    st.caption("Single coherent onglet for DNA optimization metrics and DNA-to-protein visual impact.")

    df = st.session_state["dataset"]
    if df.empty:
        st.info("Load artifacts first from the Pipeline Execution tab.")
        return

    accession_col = _accession_column_name(df)
    if accession_col is None:
        st.warning("No accession column found. Expected accession or protein_accession.")
        return

    required_columns = {
        "dna_sequence",
        "naive_dna_sequence",
        "cai",
        "naive_cai",
        "gc_content",
        "naive_gc_content",
        "target_expression_score",
    }
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        st.warning("This unified view needs naive-vs-optimized DNA columns. Please rerun pipeline and reload artifacts.")
        st.caption(f"Missing columns: {', '.join(missing_columns)}")
        return

    accessions = sorted(df[accession_col].dropna().astype(str).unique().tolist())
    if not accessions:
        st.warning("No protein accession available in dataset.")
        return

    accession_labels: Dict[str, str] = {}
    for accession in accessions:
        rows_for_accession = df[df[accession_col].astype(str) == accession]
        if "protein_name" in rows_for_accession.columns:
            protein_name = _first_non_empty_text(rows_for_accession["protein_name"], default="Unknown protein")
        else:
            protein_name = "Unknown protein"
        accession_labels[accession] = f"{accession} — {protein_name}"

    selector_col1, selector_col2, selector_col3 = st.columns([1.4, 1.3, 1.0])
    with selector_col1:
        selected_accession = st.selectbox(
            "Protein",
            options=accessions,
            format_func=lambda accession: accession_labels.get(accession, accession),
            key="dna_fusion_accession",
        )

    selected_rows = df[df[accession_col].astype(str) == selected_accession].copy()
    host_options = (
        sorted(selected_rows["plant_host"].dropna().astype(str).unique().tolist())
        if "plant_host" in selected_rows.columns
        else []
    )

    with selector_col2:
        selected_host = (
            st.selectbox("Plant host", options=host_options, key="dna_fusion_host") if host_options else None
        )

    with selector_col3:
        color_by_hydrophobicity = st.checkbox("Hydrophobicity colors", value=True, key="dna_fusion_hydro")

    if selected_host:
        host_rows = selected_rows[selected_rows["plant_host"].astype(str) == selected_host]
        selected_row = host_rows.iloc[0] if not host_rows.empty else selected_rows.iloc[0]
    else:
        selected_row = selected_rows.iloc[0]

    protein_name = _safe_text(selected_row.get("protein_name"), default="Unknown protein")
    organism = _safe_text(selected_row.get("organism"), default="Unknown organism")
    plant_host = _safe_text(selected_host or selected_row.get("plant_host"), default="N/A")

    naive_dna_sequence = str(selected_row.get("naive_dna_sequence", "") or "").strip().upper()
    optimized_dna_sequence = str(selected_row.get("dna_sequence", "") or "").strip().upper()

    naive_cai = _safe_float(selected_row.get("naive_cai"))
    optimized_cai = _safe_float(selected_row.get("cai"))
    naive_gc = _safe_float(selected_row.get("naive_gc_content"))
    optimized_gc = _safe_float(selected_row.get("gc_content"))

    delta_cai = _safe_float(selected_row.get("delta_cai"), default=round(optimized_cai - naive_cai, 4))
    delta_gc = _safe_float(selected_row.get("delta_gc"), default=round(optimized_gc - naive_gc, 4))

    optimized_proxy = _safe_float(selected_row.get("target_expression_score"))
    naive_proxy_raw = selected_row.get("naive_proxy_expression_score")
    if naive_proxy_raw is not None and not pd.isna(naive_proxy_raw):
        naive_proxy = _safe_float(naive_proxy_raw)
    else:
        estimated_gain = max(0.0, (0.5 * max(delta_cai, 0.0)) + (0.2 * max(delta_gc, 0.0)))
        naive_proxy = round(max(0.0, optimized_proxy - estimated_gain), 4)

    delta_proxy = _safe_float(
        selected_row.get("delta_proxy_expression"),
        default=round(optimized_proxy - naive_proxy, 4),
    )

    codon_diff_raw = selected_row.get("codon_usage_difference_score")
    if codon_diff_raw is not None and not pd.isna(codon_diff_raw):
        codon_diff_score = _safe_float(codon_diff_raw)
    else:
        codon_diff_score = _codon_difference_score(naive_dna_sequence, optimized_dna_sequence)

    diff_indexes, total_codons = _codon_diff_indexes(naive_dna_sequence, optimized_dna_sequence)
    diff_percent = (len(diff_indexes) / total_codons * 100.0) if total_codons > 0 else 0.0

    if len(host_options) > 1:
        cai_across_hosts = pd.to_numeric(selected_rows.get("cai"), errors="coerce").dropna()
        if not cai_across_hosts.empty:
            cai_min = float(cai_across_hosts.min())
            cai_max = float(cai_across_hosts.max())
            cai_span = cai_max - cai_min
            if cai_span <= 0.01:
                st.warning(
                    "Optimized CAI is quasi-constant across hosts for this protein. "
                    "Interpret host differences with codon-difference and proxy metrics as complementary signals."
                )
                st.caption(
                    f"Optimized CAI range across hosts: {cai_min:.4f} to {cai_max:.4f} "
                    f"(span={cai_span:.4f})."
                )

    st.markdown("### A. Context and Optimization Summary")
    card_col1, card_col2, card_col3 = st.columns(3)
    with card_col1:
        _render_info_card(
            "Protein context",
            [
                ("Accession", selected_accession),
                ("Protein", protein_name),
                ("Organism", organism),
            ],
        )
    with card_col2:
        _render_info_card(
            "Plant context",
            [
                ("Selected host", plant_host),
                ("Naive DNA length", f"{len(naive_dna_sequence)} nt"),
                ("Optimized DNA length", f"{len(optimized_dna_sequence)} nt"),
            ],
        )
    with card_col3:
        _render_info_card(
            "Optimization deltas",
            [
                ("Codon difference score", f"{codon_diff_score:.4f}"),
                ("Delta CAI", f"{delta_cai:+.4f}"),
                ("Delta GC", f"{delta_gc:+.4f}"),
                ("Delta proxy", f"{delta_proxy:+.4f}"),
            ],
        )

    st.markdown("### B. Quantitative Comparison")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric("CAI (optimized)", f"{optimized_cai:.4f}", delta=f"{delta_cai:+.4f} vs naive")
        st.caption(f"Naive CAI: {naive_cai:.4f}")
    with metric_col2:
        st.metric("GC content (optimized)", f"{optimized_gc:.4f}", delta=f"{delta_gc:+.4f} vs naive")
        st.caption(f"Naive GC content: {naive_gc:.4f}")
    with metric_col3:
        st.metric("Proxy expression (optimized)", f"{optimized_proxy:.4f}", delta=f"{delta_proxy:+.4f} vs naive")
        st.caption(f"Naive proxy expression: {naive_proxy:.4f}")

    indicator_col1, indicator_col2, indicator_col3 = st.columns(3)
    with indicator_col1:
        _render_improvement_indicator("CAI", delta_cai)
    with indicator_col2:
        _render_improvement_indicator("GC content", delta_gc)
    with indicator_col3:
        _render_improvement_indicator("Proxy expression", delta_proxy)

    comparison_df = pd.DataFrame(
        {
            "metric": ["CAI", "GC content", "Proxy expression score"],
            "naive": [naive_cai, naive_gc, naive_proxy],
            "optimized": [optimized_cai, optimized_gc, optimized_proxy],
        }
    )
    plot_df = comparison_df.melt(id_vars=["metric"], var_name="design", value_name="value")
    bar_fig = px.bar(
        plot_df,
        x="metric",
        y="value",
        color="design",
        barmode="group",
        color_discrete_map={"naive": "#fb7185", "optimized": "#22c55e"},
        title=f"Naive vs Optimized DNA Metrics ({selected_accession} | {plant_host})",
    )
    st.plotly_chart(bar_fig, use_container_width=True)

    st.markdown("### C. Visual Flow: DNA -> Protein -> DNA")
    flow_col1, flow_col2, flow_col3, flow_col4, flow_col5 = st.columns([1.75, 0.2, 2.3, 0.2, 1.75])
    with flow_col1:
        _render_stylized_dna_track(
            title="Naive DNA",
            dna_sequence=naive_dna_sequence,
            tone="naive",
            diff_indexes=diff_indexes,
        )
    with flow_col2:
        st.markdown("<div class='impact-arrow'>-></div>", unsafe_allow_html=True)
    with flow_col3:
        st.markdown("<div class='impact-stage-title' style='text-align:center;'>Protein 3D</div>", unsafe_allow_html=True)

        pdb_url = str(selected_row.get("pdb_url", "") or "").strip()
        protein_length = _safe_int(
            selected_row.get("protein_length", selected_row.get("sequence_length_aa", 1)),
            default=1,
        )
        pdb_text = _cached_download_pdb(pdb_url) if pdb_url else ""
        if not pdb_text:
            pdb_text = generate_mock_pdb_from_length(protein_length, accession=selected_accession)

        if color_by_hydrophobicity:
            pdb_text = apply_hydrophobicity_bfactor(pdb_text)

        if py3Dmol is None:
            st.error("py3Dmol is not installed. Install dependencies from requirements.txt to enable 3D viewing.")
        else:
            viewer_html = _build_impact_3d_view_html(
                pdb_text=pdb_text,
                color_by_hydrophobicity=color_by_hydrophobicity,
            )
            if viewer_html:
                components.html(viewer_html, height=440)
            else:
                st.warning("PDB content unavailable for rendering.")

        st.markdown(
            "<div class='impact-legend-row'>"
            "<span class='impact-chip'>Helix</span>"
            "<span class='impact-chip'>Sheet</span>"
            "<span class='impact-chip'>Loop</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    with flow_col4:
        st.markdown("<div class='impact-arrow'>-></div>", unsafe_allow_html=True)
    with flow_col5:
        _render_stylized_dna_track(
            title="Optimized DNA",
            dna_sequence=optimized_dna_sequence,
            tone="optimized",
            diff_indexes=diff_indexes,
        )

    st.markdown("### D. Codon Difference and Interpretation")
    diff_col1, diff_col2, diff_col3 = st.columns(3)
    diff_col1.metric("Different codons", f"{len(diff_indexes)} / {total_codons}")
    diff_col2.metric("Difference percentage", f"{diff_percent:.1f}%")
    diff_col3.metric("Selected host", plant_host)

    st.markdown(
        (
            "<div class='impact-concept'>"
            "<div class='impact-concept-title'>DNA -> Translation -> Protein</div>"
            "<div class='impact-concept-line'>Naive DNA: generic codons, lower translation efficiency.</div>"
            "<div class='impact-concept-line'>Optimized DNA: host-adapted codons, improved translation efficiency.</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    if abs(naive_proxy) > 1e-9:
        improvement_percent = ((optimized_proxy - naive_proxy) / abs(naive_proxy)) * 100.0
    else:
        improvement_percent = 100.0 if optimized_proxy > 0 else 0.0

    st.success(
        f"Codon optimization improved expression efficiency by {improvement_percent:.1f}% for this host."
    )
    st.caption(f"Story context: {selected_accession} — {protein_name}")


def _render_metrics_tab_legacy() -> None:
    st.subheader("Metrics / Model Results")
    st.caption("Multi-model training, comparison, and interpretation for the proxy-expression target.")

    metrics = st.session_state.metrics
    manifest = st.session_state.manifest or {}
    dataset = st.session_state.get("dataset", pd.DataFrame())

    def _fmt_metric(value: Any, ndigits: int = 4) -> str:
        try:
            return f"{float(value):.{ndigits}f}"
        except (TypeError, ValueError):
            return "N/A"

    def _fmt_pct(value: Any, ndigits: int = 2) -> str:
        try:
            return f"{float(value):.{ndigits}f}%"
        except (TypeError, ValueError):
            return "N/A"

    def _extract_numeric_vector(keys: List[str]) -> Optional[pd.Series]:
        for key in keys:
            values = metrics.get(key)
            if isinstance(values, list) and values:
                series = pd.to_numeric(pd.Series(values), errors="coerce").dropna().reset_index(drop=True)
                if len(series) >= 5:
                    return series
        return None

    if not metrics:
        st.info("No metrics file loaded. This is expected when training was disabled.")
        if isinstance(dataset, pd.DataFrame) and not dataset.empty and len(dataset) < 25:
            st.warning("Dataset is too small for robust model comparison (recommended minimum: 25 rows).")
        return

    training_enabled = metrics.get("training_enabled")
    skipped = metrics.get("skipped", False)

    if training_enabled is False:
        st.info("Training was disabled for this run. No model metrics are available.")
        return

    if skipped:
        reason = metrics.get("reason", "Training skipped without explicit reason.")
        st.warning(f"Training skipped: {reason}")
        with st.expander("Show training metadata", expanded=False):
            st.json(metrics)
        return

    if metrics.get("error"):
        st.error(f"Training failed: {metrics.get('error')}")
        with st.expander("Show error payload", expanded=False):
            st.json(metrics)
        return

    if isinstance(dataset, pd.DataFrame) and not dataset.empty and len(dataset) < 25:
        st.warning("Dataset is small (<25 rows). Metrics can be unstable and should be interpreted cautiously.")

    unavailable_models = metrics.get("unavailable_models", [])
    if unavailable_models:
        st.caption(f"Unavailable optional models in this environment: {', '.join(unavailable_models)}")

    st.markdown("### Evaluation Protocol")
    eval_col1, eval_col2, eval_col3, eval_col4 = st.columns(4)
    eval_col1.metric("Target", str(metrics.get("target_column", "target_expression_score")))
    eval_col2.metric("Split", str(metrics.get("evaluation_protocol", "N/A")).replace("_", " "))
    eval_col3.metric("Train/Test Group Overlap", str(metrics.get("train_test_group_overlap_count", "N/A")))
    eval_col4.metric("Fit/Val Group Overlap", str(metrics.get("fit_validation_group_overlap_count", "N/A")))

    leak_passed = (metrics.get("credibility_checks") or {}).get("leakage_check_passed")
    if leak_passed is True:
        st.success("Leakage check passed: no protein accession is shared across grouped holdout splits.")
    elif leak_passed is False:
        st.warning("Leakage check failed: grouped split overlap was detected. Regenerate artifacts with the current backend.")
    else:
        st.caption("Leakage check unavailable in this metrics file. Regenerate artifacts to enable grouped evaluation metadata.")

    target_diagnostics = metrics.get("target_dependency_diagnostics", {})
    if isinstance(target_diagnostics, dict) and target_diagnostics:
        target_summary = target_diagnostics.get("target_summary", {})
        td1, td2, td3, td4 = st.columns(4)
        td1.metric("Target Version", str(target_diagnostics.get("target_version", "N/A")))
        td2.metric("Target Mean", _fmt_metric((target_summary or {}).get("mean")))
        td3.metric("Target Std", _fmt_metric((target_summary or {}).get("std")))
        td4.metric(
            "Leakage Flags",
            str(len(target_diagnostics.get("potential_target_leakage_features", []) or [])),
        )
        assumption_note = target_diagnostics.get("assumption_note")
        if assumption_note:
            st.caption(str(assumption_note))
        with st.expander("Target dependency diagnostics", expanded=False):
            correlations = target_diagnostics.get("top_abs_feature_correlations", [])
            if isinstance(correlations, list) and correlations:
                st.dataframe(pd.DataFrame(correlations), use_container_width=True, hide_index=True)
            st.json(target_diagnostics)

    st.markdown("### A. Model Performance Overview")
    model_comparison = metrics.get("model_comparison", {})
    rows = []
    if isinstance(model_comparison, dict) and model_comparison:
        for model_name, model_metrics in model_comparison.items():
            rows.append(
                {
                    "model": model_name,
                    "rmse": model_metrics.get("rmse"),
                    "mae": model_metrics.get("mae"),
                    "r2": model_metrics.get("r2"),
                    "validation_rmse": model_metrics.get("validation_rmse"),
                    "validation_mae": model_metrics.get("validation_mae"),
                    "validation_r2": model_metrics.get("validation_r2"),
                    "cv_rmse_mean": model_metrics.get("cv_rmse_mean"),
                    "cv_rmse_std": model_metrics.get("cv_rmse_std"),
                    "best_params": model_metrics.get("best_params"),
                }
            )
    else:
        best_model_name = metrics.get("best_model_name") or metrics.get("best_model") or "best_model"
        rows.append(
            {
                "model": best_model_name,
                "rmse": metrics.get("rmse"),
                "mae": metrics.get("mae"),
                "r2": metrics.get("r2"),
                "validation_rmse": metrics.get("validation_rmse"),
                "validation_mae": metrics.get("validation_mae"),
                "validation_r2": metrics.get("validation_r2"),
                "cv_rmse_mean": metrics.get("cv_rmse_mean"),
                "cv_rmse_std": metrics.get("cv_rmse_std"),
                "best_params": metrics.get("best_params"),
            }
        )

    model_df = pd.DataFrame(rows)
    if model_df.empty:
        st.warning("No model comparison data available.")
        return

    numeric_columns = [
        "rmse",
        "mae",
        "r2",
        "validation_rmse",
        "validation_mae",
        "validation_r2",
        "cv_rmse_mean",
        "cv_rmse_std",
    ]
    for col in numeric_columns:
        if col in model_df.columns:
            model_df[col] = pd.to_numeric(model_df[col], errors="coerce")

    sort_column = "validation_rmse" if model_df["validation_rmse"].notna().any() else "rmse"
    model_df = model_df.sort_values(sort_column, ascending=True).reset_index(drop=True)

    best_model_name = str(metrics.get("best_model_name") or metrics.get("best_model") or "")
    available_models = model_df["model"].astype(str).tolist()
    if not best_model_name or best_model_name not in available_models:
        best_model_name = str(model_df.iloc[0]["model"])

    best_row_df = model_df[model_df["model"].astype(str) == best_model_name]
    best_row = best_row_df.iloc[0].to_dict() if not best_row_df.empty else model_df.iloc[0].to_dict()

    top_col1, top_col2, top_col3, top_col4 = st.columns(4)
    top_col1.metric("Top-ranked model", best_model_name)
    top_col2.metric("RMSE", _fmt_metric(best_row.get("rmse")))
    top_col3.metric("MAE", _fmt_metric(best_row.get("mae")))
    top_col4.metric("R²", _fmt_metric(best_row.get("r2")))

    selection_value = best_row.get(sort_column)
    if selection_value is None or pd.isna(selection_value):
        selection_value = metrics.get("best_model_score", metrics.get("validation_rmse", metrics.get("rmse")))
    st.caption(f"Selection metric ({sort_column}): {_fmt_metric(selection_value)}")

    model_path = metrics.get("best_model_path") or metrics.get("model_path") or manifest.get("latest_model_path") or "N/A"
    st.caption(f"Primary model path: {model_path}")

    compare_cols = [m for m in ["rmse", "mae", "r2"] if model_df[m].notna().any()]
    if compare_cols:
        compare_df = model_df[["model"] + compare_cols].melt(
            id_vars="model",
            var_name="metric",
            value_name="score",
        )
        compare_df = compare_df.dropna(subset=["score"])
        metric_labels = {
            "rmse": "RMSE (lower is better)",
            "mae": "MAE (lower is better)",
            "r2": "R² (higher is better)",
        }
        compare_df["metric"] = compare_df["metric"].map(metric_labels)

        comparison_fig = px.bar(
            compare_df,
            x="score",
            y="model",
            color="metric",
            facet_col="metric",
            orientation="h",
            title="Model comparison across RMSE, MAE, and R²",
            labels={"score": "Metric value", "model": "Model", "metric": "Metric"},
            category_orders={"model": model_df["model"].astype(str).tolist()},
        )
        comparison_fig.update_layout(showlegend=False, margin=dict(t=75, l=20, r=20, b=20))
        comparison_fig.for_each_annotation(lambda ann: ann.update(text=ann.text.split("=")[-1]))
        st.plotly_chart(comparison_fig, use_container_width=True)
        st.caption("Reading guide: lower RMSE/MAE is better, higher R² is better.")

    st.dataframe(
        model_df[
            [
                "model",
                "rmse",
                "mae",
                "r2",
                "validation_rmse",
                "validation_mae",
                "validation_r2",
                "cv_rmse_mean",
                "cv_rmse_std",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### B. Model Comparison Summary")

    best_rmse_model = str(model_df.loc[model_df["rmse"].idxmin(), "model"]) if model_df["rmse"].notna().any() else "N/A"
    best_mae_model = str(model_df.loc[model_df["mae"].idxmin(), "model"]) if model_df["mae"].notna().any() else "N/A"
    best_r2_model = str(model_df.loc[model_df["r2"].idxmax(), "model"]) if model_df["r2"].notna().any() else "N/A"

    reasons = []
    if best_model_name == best_rmse_model:
        reasons.append("the lowest RMSE")
    if best_model_name == best_mae_model:
        reasons.append("the lowest MAE")
    if best_model_name == best_r2_model:
        reasons.append("the highest R²")

    if reasons:
        if len(reasons) == 1:
            reason_text = reasons[0]
        elif len(reasons) == 2:
            reason_text = f"{reasons[0]} and {reasons[1]}"
        else:
            reason_text = f"{', '.join(reasons[:-1])}, and {reasons[-1]}"
        auto_summary = (
            f"The model {best_model_name} is selected because it achieves {reason_text}. "
            "This means low error while keeping strong explained variance."
        )
    else:
        auto_summary = (
            f"The model {best_model_name} is selected based on the best available selection metric "
            f"({sort_column})."
        )

    selection_report = metrics.get("model_selection_report", {})
    if isinstance(selection_report, dict) and selection_report:
        auto_summary = str(selection_report.get("selection_reason") or auto_summary)

    summary_col1, summary_col2 = st.columns([1.0, 2.0])
    with summary_col1:
        st.metric("Selected model", best_model_name)
        st.caption(f"Lowest RMSE: {best_rmse_model}")
        st.caption(f"Lowest MAE: {best_mae_model}")
        st.caption(f"Highest R²: {best_r2_model}")
        candidate_name = metrics.get("best_candidate_model") or selection_report.get("best_candidate_model")
        if candidate_name:
            st.caption(f"Best candidate: {candidate_name}")
    with summary_col2:
        st.success(auto_summary)
        st.caption(
            "Automatic explanation based on model_comparison metrics. "
            "Lower RMSE/MAE is better; higher R² is better."
        )
        baseline_reason = selection_report.get("baseline_gate_reason") if isinstance(selection_report, dict) else None
        if baseline_reason:
            st.caption(f"Baseline gate: {baseline_reason}")

    if isinstance(selection_report, dict) and selection_report:
        with st.expander("Model selection report", expanded=False):
            st.json(selection_report)

    best_params = best_row.get("best_params") or metrics.get("best_params")
    if best_params:
        with st.expander("Best Hyperparameters", expanded=False):
            st.json(best_params)

    st.markdown("### C. Cross-Validation Robustness")
    cv_mean = metrics.get("cv_rmse_mean")
    cv_std = metrics.get("cv_rmse_std")
    c1, c2, c3 = st.columns(3)
    c1.metric("CV RMSE Mean", _fmt_metric(cv_mean))
    c2.metric("CV RMSE Std", _fmt_metric(cv_std))
    c3.metric("Validation Samples", str(metrics.get("validation_samples", "N/A")))

    st.markdown("### D. ML Credibility Checks")
    credibility = metrics.get("credibility_checks", {})
    if isinstance(credibility, dict) and credibility:
        cr1, cr2, cr3, cr4 = st.columns(4)
        cr1.metric(
            "Baseline RMSE",
            _fmt_metric(credibility.get("baseline_validation_rmse")),
        )
        cr2.metric(
            "Best RMSE",
            _fmt_metric(credibility.get("best_validation_rmse")),
        )
        cr3.metric(
            "Gain vs Baseline",
            _fmt_pct(credibility.get("validation_rmse_improvement_vs_baseline_pct")),
        )
        cr4.metric(
            "Generalization Gap",
            _fmt_metric(credibility.get("generalization_gap_abs")),
        )

        candidate_beats = credibility.get("best_candidate_beats_baseline")
        if candidate_beats is True:
            st.success("Best candidate clears the configured baseline improvement margin.")
        elif candidate_beats is False:
            st.warning("Best candidate does not clear the configured baseline improvement margin.")

        summary_text = str(credibility.get("summary") or "")
        if summary_text:
            st.info(summary_text)

        group_rows = [
            {
                "check": "train/test protein overlap",
                "value": credibility.get("train_test_group_overlap_count", metrics.get("train_test_group_overlap_count", "N/A")),
            },
            {
                "check": "fit/validation protein overlap",
                "value": credibility.get("fit_validation_group_overlap_count", metrics.get("fit_validation_group_overlap_count", "N/A")),
            },
            {
                "check": "total protein groups",
                "value": credibility.get("unique_groups_total", metrics.get("unique_group_count", "N/A")),
            },
            {
                "check": "test protein groups",
                "value": credibility.get("test_groups", metrics.get("test_group_count", "N/A")),
            },
        ]
        st.dataframe(pd.DataFrame(group_rows), use_container_width=True, hide_index=True)

        st.caption(
            "Credibility criteria: baseline comparison, validation-to-test consistency, and cross-validation stability."
        )
    else:
        st.caption("No explicit credibility payload found for this run.")

    st.markdown("### E. Feature Coverage by Case")
    feature_selection = metrics.get("feature_selection", {})
    if isinstance(feature_selection, dict) and feature_selection:
        fs1, fs2, fs3, fs4 = st.columns(4)
        fs1.metric("Candidates", str(feature_selection.get("candidate_feature_count", "N/A")))
        fs2.metric("Selected", str(feature_selection.get("selected_feature_count", "N/A")))
        fs3.metric("Excluded", str(feature_selection.get("excluded_feature_count", "N/A")))
        fs4.metric(
            "Selection metric",
            str(
                (metrics.get("credibility_checks") or {}).get("selection_metric")
                or "validation_rmse"
            ),
        )

        strategy_text = str(feature_selection.get("strategy") or "")
        if strategy_text:
            st.caption(f"Feature strategy: {strategy_text}")

        diagnostics_rows = feature_selection.get("feature_diagnostics", [])
        if isinstance(diagnostics_rows, list) and diagnostics_rows:
            diag_df = pd.DataFrame(diagnostics_rows)
            if "status" in diag_df.columns:
                diag_df["status"] = diag_df["status"].map(
                    {
                        "selected": "selected",
                        "excluded": "excluded",
                    }
                ).fillna(diag_df["status"].astype(str))

            display_columns = [
                col
                for col in [
                    "feature",
                    "status",
                    "reason",
                    "non_null_count",
                    "missing_ratio",
                    "unique_values",
                    "variance",
                ]
                if col in diag_df.columns
            ]
            st.dataframe(diag_df[display_columns], use_container_width=True, hide_index=True)

        selected_features = feature_selection.get("selected_features", [])
        excluded_features = feature_selection.get("excluded_features", [])

        with st.expander("Selected features", expanded=False):
            if selected_features:
                st.caption(", ".join(str(name) for name in selected_features))
            else:
                st.caption("No selected features listed.")

        with st.expander("Excluded features and reasons", expanded=False):
            if excluded_features:
                st.dataframe(pd.DataFrame(excluded_features), use_container_width=True, hide_index=True)
            else:
                st.caption("No excluded features listed.")

        constant_warnings = (
            feature_selection.get("constant_feature_warnings")
            or metrics.get("constant_feature_warnings")
            or []
        )
        if isinstance(constant_warnings, list) and constant_warnings:
            st.warning("Constant features were detected and excluded from training.")
            st.dataframe(pd.DataFrame(constant_warnings), use_container_width=True, hide_index=True)

        feature_roles = feature_selection.get("feature_roles") or metrics.get("feature_roles") or {}
        if isinstance(feature_roles, dict) and feature_roles:
            with st.expander("Feature roles", expanded=False):
                used_by_model = feature_roles.get("used_by_model", [])
                descriptive_only = feature_roles.get("descriptive_only", [])
                target_derived = feature_roles.get("target_derived_excluded", [])
                st.write("Used by model")
                st.caption(", ".join(str(v) for v in used_by_model) if used_by_model else "N/A")
                st.write("Descriptive only")
                st.caption(", ".join(str(v) for v in descriptive_only) if descriptive_only else "N/A")
                st.write("Target-derived and excluded")
                st.caption(", ".join(str(v) for v in target_derived) if target_derived else "N/A")
    else:
        st.caption("Feature coverage payload not available for this run.")

    st.markdown("### F. Ablation Study")
    ablation_payload = metrics.get("ablation_study", {})
    if isinstance(ablation_payload, dict) and ablation_payload:
        ablation_rows = []
        for block_name, block_metrics in ablation_payload.items():
            if not isinstance(block_metrics, dict):
                continue
            ablation_rows.append(
                {
                    "feature_block": block_name,
                    "model": block_metrics.get("model", "N/A"),
                    "validation_rmse": block_metrics.get("validation_rmse"),
                    "rmse": block_metrics.get("rmse"),
                    "r2": block_metrics.get("r2"),
                    "skipped": block_metrics.get("skipped", False),
                    "features": ", ".join(str(v) for v in block_metrics.get("features", [])),
                }
            )
        ablation_df = pd.DataFrame(ablation_rows)
        if not ablation_df.empty:
            for col in ["validation_rmse", "rmse", "r2"]:
                ablation_df[col] = pd.to_numeric(ablation_df[col], errors="coerce")
            st.dataframe(ablation_df, use_container_width=True, hide_index=True)
            chart_df = ablation_df.dropna(subset=["validation_rmse"]).sort_values("validation_rmse")
            if not chart_df.empty:
                ablation_fig = px.bar(
                    chart_df,
                    x="validation_rmse",
                    y="feature_block",
                    orientation="h",
                    title="Grouped validation RMSE by feature block",
                    labels={"validation_rmse": "Validation RMSE", "feature_block": "Feature block"},
                )
                st.plotly_chart(ablation_fig, use_container_width=True)
        else:
            st.caption("Ablation payload is empty.")
    else:
        st.caption("Ablation study unavailable in this metrics file. Regenerate artifacts with the current backend.")

    st.markdown("### G. Feature Importance Analysis")
    names = metrics.get("feature_names", [])
    importances = metrics.get("feature_importances", [])
    importance_source = metrics.get("feature_importance_source", "N/A")

    model_level_importances = None
    if isinstance(model_comparison, dict) and model_comparison:
        model_level_importances = (model_comparison.get(best_model_name) or {}).get("feature_importances")
        model_level_source = (model_comparison.get(best_model_name) or {}).get("feature_importance_source")
        if model_level_source:
            importance_source = model_level_source

    if not importances and isinstance(model_level_importances, list):
        importances = model_level_importances

    imp_df = pd.DataFrame()
    importance_table = metrics.get("feature_importance_table", [])
    if isinstance(importance_table, list) and importance_table:
        imp_df = pd.DataFrame(importance_table)
        if "feature" not in imp_df.columns and "name" in imp_df.columns:
            imp_df["feature"] = imp_df["name"]
    elif isinstance(importances, dict) and importances:
        imp_df = pd.DataFrame(
            [{"feature": str(k), "importance": v} for k, v in importances.items()]
        )
    elif isinstance(names, list) and isinstance(importances, list) and names and len(names) == len(importances):
        imp_df = pd.DataFrame({"feature": names, "importance": importances})

    if not imp_df.empty:
        imp_df["importance"] = pd.to_numeric(imp_df["importance"], errors="coerce")
        imp_df = imp_df.dropna(subset=["importance"])
        imp_df = imp_df.sort_values("importance", ascending=False).reset_index(drop=True)

        top_n = min(10, len(imp_df))
        top_imp_df = imp_df.head(top_n)

        imp_chart_df = top_imp_df.sort_values("importance", ascending=False)
        imp_chart = px.bar(
            imp_chart_df,
            y="importance",
            x="feature",
            title=f"Top {top_n} Most Important Features",
            labels={"importance": "Importance", "feature": "Feature"},
            color="importance",
            color_continuous_scale="Viridis",
        )
        imp_chart.update_layout(coloraxis_showscale=False)
        st.plotly_chart(imp_chart, use_container_width=True)

        st.dataframe(top_imp_df, use_container_width=True, hide_index=True)
        with st.expander("Show full feature importance table", expanded=False):
            st.dataframe(imp_df, use_container_width=True, hide_index=True)

        top_features = top_imp_df["feature"].head(3).tolist()
        top_features_text = ", ".join(top_features) if top_features else "N/A"
        top_features_lower = [str(f).lower() for f in top_features]

        interpretation_lines = [f"Dominant variables are: {top_features_text}."]

        if any("gc" in name for name in top_features_lower):
            interpretation_lines.append(
                "GC-related variables are influential, consistent with codon usage constraints and translation efficiency trends."
            )
        if any("codon" in name or "cai" in name for name in top_features_lower):
            interpretation_lines.append(
                "Codon-usage descriptors contribute to model decisions, which is biologically plausible for expression proxy modeling."
            )
        if any(
            marker in name
            for name in top_features_lower
            for marker in ["stability", "helix", "sheet", "coil", "hydrophobicity", "protein_length"]
        ):
            interpretation_lines.append(
                "Protein structure-related signals are also used by the model, linking sequence design to structural context."
            )

        cai_row = imp_df[imp_df["feature"].astype(str).str.lower() == "cai"]
        cai_low_importance = False
        cai_importance_value = None
        if not cai_row.empty:
            cai_importance_value = float(cai_row.iloc[0]["importance"])
            cai_low_importance = cai_importance_value <= max(0.01, float(imp_df["importance"].median()) * 0.5)

        cai_constant = (
            isinstance(dataset, pd.DataFrame)
            and not dataset.empty
            and "cai" in dataset.columns
            and _is_non_informative_series(dataset["cai"])
        )

        if cai_constant:
            interpretation_lines.append(
                "CAI appears non-informative in this run because it is nearly constant across samples."
            )
        elif cai_low_importance and cai_importance_value is not None:
            interpretation_lines.append(
                f"CAI has low contribution in this run (importance={cai_importance_value:.4f}), suggesting limited discriminative power."
            )

        st.info(" ".join(interpretation_lines))
        st.caption(f"Importance source: {importance_source}")
    else:
        st.info("No feature importance data available for this run.")

    st.markdown("### H. Model Interpretation")

    interpretation_messages = []
    interpretation_payload = metrics.get("interpretation_summary", {})
    if isinstance(interpretation_payload, dict) and interpretation_payload:
        plain_language = interpretation_payload.get("plain_language")
        caution_text = interpretation_payload.get("caution")
        if plain_language:
            interpretation_messages.append(str(plain_language))
        if caution_text:
            interpretation_messages.append(str(caution_text))

    if not imp_df.empty:
        dominant = imp_df.head(min(3, len(imp_df)))["feature"].tolist()
        weakest = imp_df.tail(min(3, len(imp_df)))["feature"].tolist()
        interpretation_messages.append(f"Dominant features: {', '.join(dominant)}.")
        interpretation_messages.append(f"Lower-impact features: {', '.join(weakest)}.")

    if isinstance(dataset, pd.DataFrame) and not dataset.empty and "cai" in dataset.columns:
        if _is_non_informative_series(dataset["cai"]):
            interpretation_messages.append(
                "CAI can be weakly informative when it is almost constant in the selected dataset."
            )

    interpretation_messages.append(
        "Biological reading: codon usage and GC-related variables often drive translation efficiency proxies."
    )
    interpretation_messages.append(
        "This is still a proxy model and should be interpreted as a ranking aid, not wet-lab evidence."
    )

    for message in interpretation_messages:
        st.markdown(f"- {message}")

    st.markdown("### I. How the model works")
    flow_col1, flow_col2, flow_col3 = st.columns([2.0, 1.4, 2.0])

    with flow_col1:
        st.markdown("**Input**")
        st.markdown("- DNA/codon features (GC, GC3, CAI, rare codons)")
        st.markdown("- Protein descriptors (length, helix/sheet/coil, stability)")

    with flow_col2:
        st.markdown("**Model**")
        st.markdown(f"- {best_model_name}")
        st.markdown("- Trained on proxy-expression target")

    with flow_col3:
        st.markdown("**Output**")
        st.markdown("- Proxy expression score")
        st.markdown("- Relative ranking of candidate DNA designs")

    st.caption("Flow: Input features -> trained model -> proxy expression score")

    st.markdown("### J. ML Pipeline Schema")
    pipeline_schema = metrics.get("ml_pipeline_schema", {})
    if isinstance(pipeline_schema, dict) and pipeline_schema:
        objective_text = pipeline_schema.get("objective")
        strategy_text = pipeline_schema.get("feature_strategy")
        selection_metric_text = pipeline_schema.get("selection_metric")

        if objective_text:
            st.caption(f"Objective: {objective_text}")
        if strategy_text:
            st.caption(f"Feature handling: {strategy_text}")
        if selection_metric_text:
            st.caption(f"Model selection criterion: {selection_metric_text}")

        st.markdown(
            "Candidate features -> Quality filtering -> Multi-model training -> "
            "Validation-based selection -> Interpretation and diagnostics"
        )

        schema_steps = pipeline_schema.get("steps", [])
        if isinstance(schema_steps, list) and schema_steps:
            for step in schema_steps:
                st.markdown(f"- {step}")
    else:
        st.caption("No ML pipeline schema provided in metrics JSON.")

    st.markdown("### K. Optional Error Diagnostics")
    y_true = _extract_numeric_vector(
        [
            "test_actual_values",
            "y_true",
            "y_test",
            "validation_y_true",
            "actual",
            "actual_values",
            "true_values",
        ]
    )
    y_pred = _extract_numeric_vector(
        [
            "test_predicted_values",
            "y_pred",
            "y_test_pred",
            "validation_y_pred",
            "predicted",
            "predictions",
            "predicted_values",
        ]
    )

    if y_true is not None and y_pred is not None:
        n = min(len(y_true), len(y_pred))
        diag_df = pd.DataFrame({"actual": y_true.iloc[:n], "predicted": y_pred.iloc[:n]})
        diag_df["residual"] = diag_df["actual"] - diag_df["predicted"]

        d1, d2 = st.columns(2)
        with d1:
            residual_fig = px.histogram(
                diag_df,
                x="residual",
                nbins=25,
                title="Residual Distribution (actual - predicted)",
            )
            st.plotly_chart(residual_fig, use_container_width=True)
        with d2:
            scatter_fig = px.scatter(
                diag_df,
                x="actual",
                y="predicted",
                title="Predicted vs Actual",
                labels={"actual": "Actual", "predicted": "Predicted"},
            )
            min_val = float(min(diag_df["actual"].min(), diag_df["predicted"].min()))
            max_val = float(max(diag_df["actual"].max(), diag_df["predicted"].max()))
            scatter_fig.add_shape(
                type="line",
                x0=min_val,
                y0=min_val,
                x1=max_val,
                y1=max_val,
                line=dict(color="#64748b", dash="dash"),
            )
            st.plotly_chart(scatter_fig, use_container_width=True)
    else:
        st.caption(
            "Residual diagnostics unavailable for this run: metrics JSON does not include per-sample actual/predicted vectors."
        )

    with st.expander("Show raw metrics JSON", expanded=False):
        st.json(metrics)


def _fmt_dashboard_metric(value: Any, ndigits: int = 4) -> str:
    return _render_metrics_tab_impl.__globals__["_fmt_dashboard_metric"](value, ndigits=ndigits)


def _fmt_dashboard_pct(value: Any, ndigits: int = 2) -> str:
    return _render_metrics_tab_impl.__globals__["_fmt_dashboard_pct"](value, ndigits=ndigits)


def load_metrics() -> Dict[str, Any]:
    return _load_metrics_impl()


def _load_metrics_dataset() -> pd.DataFrame:
    return _load_metrics_dataset_impl()


def _model_comparison_dataframe(metrics: Dict[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    model_comparison = metrics.get("model_comparison", {})
    if isinstance(model_comparison, dict) and model_comparison:
        for model_name, model_metrics in model_comparison.items():
            if not isinstance(model_metrics, dict):
                continue
            rows.append(
                {
                    "model": str(model_name),
                    "rmse": model_metrics.get("rmse"),
                    "mae": model_metrics.get("mae"),
                    "r2": model_metrics.get("r2"),
                    "validation_rmse": model_metrics.get("validation_rmse"),
                    "validation_mae": model_metrics.get("validation_mae"),
                    "validation_r2": model_metrics.get("validation_r2"),
                    "cv_rmse_mean": model_metrics.get("cv_rmse_mean"),
                    "cv_rmse_std": model_metrics.get("cv_rmse_std"),
                    "role": model_metrics.get("model_role", "model"),
                }
            )
    elif metrics:
        rows.append(
            {
                "model": str(metrics.get("best_model_name") or metrics.get("best_model") or "model"),
                "rmse": metrics.get("rmse"),
                "mae": metrics.get("mae"),
                "r2": metrics.get("r2"),
                "validation_rmse": metrics.get("validation_rmse"),
                "validation_mae": metrics.get("validation_mae"),
                "validation_r2": metrics.get("validation_r2"),
                "cv_rmse_mean": metrics.get("cv_rmse_mean"),
                "cv_rmse_std": metrics.get("cv_rmse_std"),
                "role": "model",
            }
        )

    model_df = pd.DataFrame(rows)
    for col in [
        "rmse",
        "mae",
        "r2",
        "validation_rmse",
        "validation_mae",
        "validation_r2",
        "cv_rmse_mean",
        "cv_rmse_std",
    ]:
        if col in model_df.columns:
            model_df[col] = pd.to_numeric(model_df[col], errors="coerce")
    return model_df


def _best_model_name(metrics: Dict[str, Any], model_df: pd.DataFrame) -> str:
    best_name = str(metrics.get("best_model_name") or metrics.get("best_model") or "")
    if best_name and not model_df.empty and best_name in model_df["model"].astype(str).tolist():
        return best_name
    if not model_df.empty and "validation_rmse" in model_df.columns and model_df["validation_rmse"].notna().any():
        return str(model_df.sort_values("validation_rmse").iloc[0]["model"])
    if not model_df.empty:
        return str(model_df.iloc[0]["model"])
    return "N/A"


def _baseline_model_name(metrics: Dict[str, Any], model_df: pd.DataFrame) -> str:
    baseline_name = str(metrics.get("baseline_model") or "dummy_mean_baseline")
    if not model_df.empty and baseline_name in model_df["model"].astype(str).tolist():
        return baseline_name
    baseline_rows = model_df[model_df.get("role", pd.Series(dtype=str)).astype(str).eq("baseline")]
    if not baseline_rows.empty:
        return str(baseline_rows.iloc[0]["model"])
    return baseline_name


def _model_row(model_df: pd.DataFrame, model_name: str) -> Dict[str, Any]:
    if model_df.empty or "model" not in model_df.columns:
        return {}
    row = model_df[model_df["model"].astype(str) == str(model_name)]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


def _resolve_model_path_for_metrics(
    metrics: Dict[str, Any],
    manifest: Dict[str, Any],
    manifest_path: Optional[Path],
) -> Optional[Path]:
    return _resolve_model_path_for_metrics_impl(metrics, manifest, manifest_path)


@st.cache_resource(show_spinner=False)
def load_best_model(model_path_text: str) -> Dict[str, Any]:
    return _load_best_model_impl(model_path_text)


def _feature_names_from_payload(model_payload: Dict[str, Any], metrics: Dict[str, Any]) -> List[str]:
    payload = model_payload.get("payload")
    if isinstance(payload, dict):
        feature_names = payload.get("feature_names") or payload.get("numeric_feature_names")
        if isinstance(feature_names, list) and feature_names:
            return [str(name) for name in feature_names]
    feature_names = metrics.get("feature_names", [])
    return [str(name) for name in feature_names] if isinstance(feature_names, list) else []


def _prepare_model_features(dataset: pd.DataFrame, feature_names: List[str]) -> pd.DataFrame:
    """Build the exact feature frame expected by the saved sklearn pipeline."""
    if dataset.empty or not feature_names:
        return pd.DataFrame()
    feature_frame = pd.DataFrame(index=dataset.index)
    for feature in feature_names:
        if feature in dataset.columns:
            feature_frame[feature] = dataset[feature]
        elif feature == "gc_deviation" and "gc_content" in dataset.columns:
            gc_percent = pd.to_numeric(dataset["gc_content"], errors="coerce").apply(_to_percent)
            feature_frame[feature] = (gc_percent - 52.5).abs()
        elif feature == "codon_efficiency" and {"cai", "rare_codon_ratio"}.issubset(dataset.columns):
            cai = pd.to_numeric(dataset["cai"], errors="coerce")
            rare_ratio = pd.to_numeric(dataset["rare_codon_ratio"], errors="coerce").apply(
                lambda value: max(0.0, min(1.0, value / 100.0 if value > 1.5 else value))
            )
            feature_frame[feature] = cai * (1.0 - rare_ratio)
        elif feature == "stability_index" and {"gc_content", "rare_codon_ratio"}.issubset(dataset.columns):
            gc_percent = pd.to_numeric(dataset["gc_content"], errors="coerce").apply(_to_percent)
            rare_ratio = pd.to_numeric(dataset["rare_codon_ratio"], errors="coerce").apply(
                lambda value: max(0.0, min(1.0, value / 100.0 if value > 1.5 else value))
            )
            feature_frame[feature] = gc_percent * (1.0 - rare_ratio)
        else:
            feature_frame[feature] = np.nan
    return feature_frame


def _extract_vector_from_metrics(metrics: Dict[str, Any], keys: List[str]) -> Optional[pd.Series]:
    for key in keys:
        values = metrics.get(key)
        if isinstance(values, list) and values:
            series = pd.to_numeric(pd.Series(values), errors="coerce").dropna().reset_index(drop=True)
            if len(series) >= 3:
                return series
    return None


def _importance_dataframe_from_metrics(metrics: Dict[str, Any]) -> pd.DataFrame:
    table = metrics.get("feature_importance_table", [])
    if isinstance(table, list) and table:
        df = pd.DataFrame(table)
        if "feature" in df.columns and "importance" in df.columns:
            df["importance"] = pd.to_numeric(df["importance"], errors="coerce")
            return df.dropna(subset=["importance"]).sort_values("importance", ascending=False)

    names = metrics.get("feature_names", [])
    values = metrics.get("feature_importances", [])
    if isinstance(names, list) and isinstance(values, list) and len(names) == len(values):
        df = pd.DataFrame({"feature": names, "importance": values})
        df["importance"] = pd.to_numeric(df["importance"], errors="coerce")
        return df.dropna(subset=["importance"]).sort_values("importance", ascending=False)
    return pd.DataFrame()


def _extract_importance_from_model(model_payload: Dict[str, Any], metrics: Dict[str, Any]) -> pd.DataFrame:
    """Fallback when metrics JSON does not contain permutation importance."""
    model = model_payload.get("model")
    payload = model_payload.get("payload")
    if model is None:
        return pd.DataFrame()

    final_model = model
    encoded_names = []
    if hasattr(model, "named_steps"):
        final_model = model.named_steps.get("model", model)
        preprocessor = model.named_steps.get("preprocessor")
        if preprocessor is not None and hasattr(preprocessor, "get_feature_names_out"):
            try:
                encoded_names = [str(name) for name in preprocessor.get_feature_names_out()]
            except Exception:
                encoded_names = []

    if not encoded_names and isinstance(payload, dict):
        encoded_names = [str(name) for name in payload.get("encoded_feature_names", [])]
    if not encoded_names:
        encoded_names = [str(name) for name in metrics.get("feature_names", [])]

    raw_values = None
    source = "model_artifact"
    if hasattr(final_model, "feature_importances_"):
        raw_values = np.asarray(final_model.feature_importances_, dtype=float)
        source = "model_feature_importances"
    elif hasattr(final_model, "coef_"):
        raw_values = np.abs(np.asarray(final_model.coef_, dtype=float).ravel())
        source = "model_coefficients"

    if raw_values is None or not encoded_names:
        return pd.DataFrame()
    limit = min(len(encoded_names), raw_values.size)
    df = pd.DataFrame(
        {
            "feature": encoded_names[:limit],
            "importance": raw_values[:limit],
            "source": source,
        }
    )
    total = float(df["importance"].sum())
    if total > 0:
        df["importance"] = df["importance"] / total
    return df.sort_values("importance", ascending=False)


def plot_model_vs_baseline(model_df: pd.DataFrame, metric: str, best_model: str, baseline_model: str) -> go.Figure:
    label_map = {
        "validation_rmse": "Validation RMSE",
        "rmse": "Test RMSE",
        "mae": "MAE",
        "r2": "R²",
        "validation_r2": "Validation R²",
    }
    plot_df = model_df.dropna(subset=[metric]).copy()
    ascending = metric not in {"r2", "validation_r2"}
    plot_df = plot_df.sort_values(metric, ascending=ascending)
    plot_df["kind"] = "Other model"
    plot_df.loc[plot_df["model"].astype(str) == baseline_model, "kind"] = "Dummy baseline"
    plot_df.loc[plot_df["model"].astype(str) == best_model, "kind"] = "Selected model"

    colors = {
        "Selected model": "#16a34a",
        "Dummy baseline": "#ef4444",
        "Other model": "#64748b",
    }
    fig = px.bar(
        plot_df,
        x=metric,
        y="model",
        color="kind",
        orientation="h",
        color_discrete_map=colors,
        title=f"Model comparison by {label_map.get(metric, metric)}",
        labels={metric: label_map.get(metric, metric), "model": "Model", "kind": ""},
    )
    fig.update_layout(height=360, yaxis_title="", legend_orientation="h", legend_y=-0.25)
    return fig


def plot_feature_importance(importance_df: pd.DataFrame) -> go.Figure:
    top_df = importance_df.head(10).sort_values("importance", ascending=True)
    fig = px.bar(
        top_df,
        x="importance",
        y="feature",
        orientation="h",
        color="importance",
        color_continuous_scale=["#dbeafe", "#22c55e"],
        title="Top 10 global feature importances",
        labels={"importance": "Importance", "feature": "Feature"},
    )
    fig.update_layout(height=430, coloraxis_showscale=False, yaxis_title="")
    return fig


def _automatic_feature_interpretation(features: List[str]) -> List[str]:
    messages: List[str] = []
    lowered = [feature.lower() for feature in features]
    if any("cai" in feature or "codon" in feature for feature in lowered):
        messages.append("Codon-related variables appear important, so codon adaptation contributes to the proxy score.")
    if any("gc" in feature for feature in lowered):
        messages.append("GC-related variables also matter, which means nucleotide composition helps the model.")
    if any("host" in feature for feature in lowered):
        messages.append("The plant host has influence, so the same protein can behave differently under host assumptions.")
    if any("length" in feature for feature in lowered):
        messages.append("Protein length or length penalty contributes to the prediction, but this remains a proxy signal.")
    if not messages:
        messages.append("The top variables influence the model globally, but they should not be read as experimental causes.")
    return messages


def _encoded_model_matrix(model: Any, x_frame: pd.DataFrame) -> Tuple[Optional[Any], np.ndarray, List[str]]:
    if model is None or x_frame.empty:
        return None, np.empty((0, 0)), []
    if hasattr(model, "named_steps") and "preprocessor" in model.named_steps:
        preprocessor = model.named_steps.get("preprocessor")
        estimator = model.named_steps.get("model")
        transformed = preprocessor.transform(x_frame)
        if hasattr(transformed, "toarray"):
            transformed = transformed.toarray()
        try:
            encoded_names = [str(name) for name in preprocessor.get_feature_names_out()]
        except Exception:
            encoded_names = [str(name) for name in x_frame.columns]
        return estimator, np.asarray(transformed, dtype=float), encoded_names

    numeric_frame = x_frame.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return model, numeric_frame.to_numpy(dtype=float), [str(name) for name in numeric_frame.columns]


def compute_shap_values(
    model_payload: Dict[str, Any],
    dataset: pd.DataFrame,
    metrics: Dict[str, Any],
    max_rows: int = 24,
) -> Dict[str, Any]:
    """Compute SHAP when available, otherwise produce a transparent contribution fallback."""
    model = model_payload.get("model")
    feature_names = _feature_names_from_payload(model_payload, metrics)
    x_frame = _prepare_model_features(dataset, feature_names)
    if model is None or x_frame.empty:
        return {"available": False, "reason": "Model or feature matrix unavailable."}

    x_explain = x_frame.sample(n=min(max_rows, len(x_frame)), random_state=42)
    x_background = x_frame.sample(n=min(48, len(x_frame)), random_state=7)
    estimator, encoded_explain, encoded_names = _encoded_model_matrix(model, x_explain)
    _, encoded_background, _ = _encoded_model_matrix(model, x_background)
    if estimator is None or encoded_explain.size == 0:
        return {"available": False, "reason": "Could not encode model features for explanation."}

    shap_values = None
    base_values = None
    method = "SHAP"
    warning = ""
    try:
        import shap  # type: ignore[import-not-found]

        if hasattr(estimator, "coef_"):
            explainer = shap.LinearExplainer(estimator, encoded_background)
        elif hasattr(estimator, "feature_importances_"):
            explainer = shap.TreeExplainer(estimator, data=encoded_background)
        else:
            explainer = shap.Explainer(estimator.predict, encoded_background)
        explanation = explainer(encoded_explain)
        shap_values = np.asarray(explanation.values, dtype=float)
        if shap_values.ndim == 3:
            shap_values = shap_values[:, :, 0]
        base_values = np.asarray(getattr(explanation, "base_values", []), dtype=float)
        if base_values.ndim > 1:
            base_values = base_values[:, 0]
    except Exception as exc:
        warning = str(exc)

    if shap_values is None and hasattr(estimator, "coef_"):
        # Linear fallback: centered coefficient contributions, close to SHAP for linear models.
        coef = np.asarray(estimator.coef_, dtype=float).ravel()
        center = np.asarray(encoded_background, dtype=float).mean(axis=0)
        limit = min(len(coef), encoded_explain.shape[1])
        shap_values = (encoded_explain[:, :limit] - center[:limit]) * coef[:limit]
        encoded_names = encoded_names[:limit]
        method = "Linear contribution fallback"

    if shap_values is None:
        return {
            "available": False,
            "reason": "SHAP is unavailable for this model. Install shap or use a linear/tree model artifact.",
            "warning": warning,
        }

    predictions = np.asarray(model.predict(x_explain), dtype=float)
    contribution_sums = np.asarray(shap_values, dtype=float).sum(axis=1)
    if base_values is None or len(base_values) != len(predictions):
        base_values = predictions - contribution_sums
    target_column = str(metrics.get("target_column") or "target_expression_score")
    actual_values = (
        pd.to_numeric(dataset.loc[x_explain.index, target_column], errors="coerce")
        if target_column in dataset.columns
        else pd.Series([np.nan] * len(x_explain), index=x_explain.index)
    )

    labels = []
    for idx in x_explain.index:
        row = dataset.loc[idx]
        accession = _safe_text(row.get("protein_accession", row.get("accession", idx)), default=str(idx))
        host = _safe_text(row.get("plant_host"), default="host")
        labels.append(f"Row {idx} | {accession} | {host}")

    global_df = pd.DataFrame(
        {
            "feature": encoded_names[: shap_values.shape[1]],
            "mean_abs_contribution": np.abs(shap_values).mean(axis=0),
        }
    ).sort_values("mean_abs_contribution", ascending=False)

    return {
        "available": True,
        "method": method,
        "warning": warning,
        "feature_names": encoded_names[: shap_values.shape[1]],
        "values": shap_values,
        "global_df": global_df,
        "sample_indices": list(x_explain.index),
        "sample_labels": labels,
        "sample_rule": f"Reproducible sample of {len(x_explain)} dataset rows, selected with random_state=42.",
        "predictions": predictions,
        "base_values": base_values,
        "contribution_sums": contribution_sums,
        "actual_values": actual_values.to_numpy(dtype=float),
    }


def plot_shap_global_summary(shap_payload: Dict[str, Any]) -> go.Figure:
    global_df = shap_payload.get("global_df", pd.DataFrame())
    top_df = global_df.head(10).sort_values("mean_abs_contribution", ascending=True)
    fig = px.bar(
        top_df,
        x="mean_abs_contribution",
        y="feature",
        orientation="h",
        color="mean_abs_contribution",
        color_continuous_scale=["#e0f2fe", "#2563eb"],
        title="SHAP global summary: average impact of each feature",
        labels={"mean_abs_contribution": "Average |SHAP value| (global impact)", "feature": "Feature"},
    )
    fig.update_layout(
        height=480,
        coloraxis_showscale=False,
        yaxis_title="",
        margin=dict(l=190, r=30, t=70, b=55),
    )
    return fig


def plot_shap_local_explanation(
    shap_payload: Dict[str, Any],
    sample_position: int,
    selected_label: str = "",
) -> go.Figure:
    values = np.asarray(shap_payload.get("values"), dtype=float)
    feature_names = shap_payload.get("feature_names", [])
    if values.size == 0 or not feature_names:
        return go.Figure()
    sample_position = max(0, min(sample_position, values.shape[0] - 1))
    local_df = pd.DataFrame(
        {
            "feature": feature_names[: values.shape[1]],
            "contribution": values[sample_position, :],
        }
    )
    local_df["abs_contribution"] = local_df["contribution"].abs()
    local_df = local_df.sort_values("abs_contribution", ascending=False).head(12)
    local_df = local_df.sort_values("contribution")
    local_df["direction"] = np.where(local_df["contribution"] >= 0, "Pushes prediction up", "Pushes prediction down")

    fig = px.bar(
        local_df,
        x="contribution",
        y="feature",
        color="direction",
        orientation="h",
        color_discrete_map={
            "Pushes prediction up": "#16a34a",
            "Pushes prediction down": "#ef4444",
        },
        title=(
            "SHAP local explanation: what pushes this prediction up or down"
            + (f"<br><sup>{selected_label}</sup>" if selected_label else "")
        ),
        labels={"contribution": "Contribution to prediction", "feature": "Feature", "direction": ""},
    )
    fig.add_vline(x=0, line_dash="dash", line_color="#475569")
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>Contribution: %{x:.5f}<extra></extra>",
    )
    fig.update_layout(
        height=480,
        yaxis_title="",
        legend_orientation="h",
        legend_y=-0.22,
        margin=dict(l=190, r=35, t=70, b=85),
    )
    return fig


def _summarize_local_contributions(shap_payload: Dict[str, Any], sample_position: int) -> str:
    """Return a short student-friendly explanation for one local SHAP chart."""
    values = np.asarray(shap_payload.get("values"), dtype=float)
    feature_names = shap_payload.get("feature_names", [])
    if values.size == 0 or not feature_names:
        return "No local contribution details are available for this example."

    sample_position = max(0, min(sample_position, values.shape[0] - 1))
    local_df = pd.DataFrame(
        {
            "feature": feature_names[: values.shape[1]],
            "contribution": values[sample_position, :],
        }
    )
    positive = local_df[local_df["contribution"] > 0].sort_values("contribution", ascending=False).head(3)
    negative = local_df[local_df["contribution"] < 0].sort_values("contribution", ascending=True).head(3)

    up_text = ", ".join(positive["feature"].astype(str).tolist()) if not positive.empty else "no strong positive feature"
    down_text = ", ".join(negative["feature"].astype(str).tolist()) if not negative.empty else "no strong negative feature"
    return (
        f"For this example, {up_text} push the prediction upward, while {down_text} push it downward. "
        "This explains this one row only; it is not a general biological rule."
    )


def _local_shap_equation_text(shap_payload: Dict[str, Any], sample_position: int) -> str:
    predictions = np.asarray(shap_payload.get("predictions", []), dtype=float)
    base_values = np.asarray(shap_payload.get("base_values", []), dtype=float)
    contribution_sums = np.asarray(shap_payload.get("contribution_sums", []), dtype=float)
    if sample_position >= len(predictions) or sample_position >= len(base_values) or sample_position >= len(contribution_sums):
        return "SHAP decomposes the model prediction into a reference value plus feature contributions."

    return (
        "SHAP calculation for this row: "
        f"reference prediction {_fmt_dashboard_metric(base_values[sample_position])} "
        f"+ feature contributions {_fmt_dashboard_metric(contribution_sums[sample_position])} "
        f"= model prediction {_fmt_dashboard_metric(predictions[sample_position])}."
    )


def plot_predictions_vs_real(metrics: Dict[str, Any]) -> Optional[go.Figure]:
    y_true = _extract_vector_from_metrics(metrics, ["test_actual_values", "actual_values", "validation_actual_values"])
    y_pred = _extract_vector_from_metrics(metrics, ["test_predicted_values", "predicted_values", "validation_predicted_values"])
    if y_true is None or y_pred is None:
        return None
    n = min(len(y_true), len(y_pred))
    diag_df = pd.DataFrame({"Proxy target": y_true.iloc[:n], "Prediction": y_pred.iloc[:n]})
    fig = px.scatter(
        diag_df,
        x="Proxy target",
        y="Prediction",
        title="Prediction quality: model vs proxy target",
        color_discrete_sequence=["#2563eb"],
    )
    min_val = float(min(diag_df["Proxy target"].min(), diag_df["Prediction"].min()))
    max_val = float(max(diag_df["Proxy target"].max(), diag_df["Prediction"].max()))
    fig.add_shape(
        type="line",
        x0=min_val,
        y0=min_val,
        x1=max_val,
        y1=max_val,
        line=dict(color="#64748b", dash="dash"),
    )
    fig.update_layout(height=420)
    return fig


def plot_residuals(metrics: Dict[str, Any]) -> Optional[go.Figure]:
    residuals = _extract_vector_from_metrics(metrics, ["test_residual_values", "residual_values", "validation_residual_values"])
    if residuals is None:
        y_true = _extract_vector_from_metrics(metrics, ["test_actual_values", "actual_values"])
        y_pred = _extract_vector_from_metrics(metrics, ["test_predicted_values", "predicted_values"])
        if y_true is None or y_pred is None:
            return None
        n = min(len(y_true), len(y_pred))
        residuals = y_true.iloc[:n].reset_index(drop=True) - y_pred.iloc[:n].reset_index(drop=True)
    fig = px.histogram(
        pd.DataFrame({"Residual": residuals}),
        x="Residual",
        nbins=24,
        title="Residual distribution: actual proxy - prediction",
        color_discrete_sequence=["#0f766e"],
    )
    fig.add_vline(x=0, line_dash="dash", line_color="#475569")
    fig.update_layout(height=420)
    return fig


def _plot_pipeline_schema(training_features: List[str], target_column: str) -> go.Figure:
    fig = go.Figure()

    # A custom Plotly diagram is more readable than a Sankey for short pedagogical labels.
    boxes = [
        {
            "key": "training",
            "x0": 0.04,
            "x1": 0.30,
            "y0": 0.62,
            "y1": 0.86,
            "fill": "#dbeafe",
            "line": "#2563eb",
            "title": f"Training features ({len(training_features)})",
            "body": "Used directly by the ML model",
        },
        {
            "key": "model",
            "x0": 0.39,
            "x1": 0.61,
            "y0": 0.62,
            "y1": 0.86,
            "fill": "#dcfce7",
            "line": "#16a34a",
            "title": "ML model",
            "body": "Learns patterns from features",
        },
        {
            "key": "target",
            "x0": 0.70,
            "x1": 0.96,
            "y0": 0.62,
            "y1": 0.86,
            "fill": "#fef3c7",
            "line": "#d97706",
            "title": "Predicted proxy target",
            "body": target_column,
        },
        {
            "key": "descriptive",
            "x0": 0.04,
            "x1": 0.30,
            "y0": 0.18,
            "y1": 0.40,
            "fill": "#f1f5f9",
            "line": "#64748b",
            "title": "Descriptive features",
            "body": "Kept for context, not training",
        },
        {
            "key": "context",
            "x0": 0.70,
            "x1": 0.96,
            "y0": 0.18,
            "y1": 0.40,
            "fill": "#ede9fe",
            "line": "#7c3aed",
            "title": "Biological context",
            "body": "Helps interpret the result",
        },
    ]

    centers = {}
    for box in boxes:
        centers[box["key"]] = ((box["x0"] + box["x1"]) / 2, (box["y0"] + box["y1"]) / 2)
        fig.add_shape(
            type="rect",
            xref="x",
            yref="y",
            x0=box["x0"],
            x1=box["x1"],
            y0=box["y0"],
            y1=box["y1"],
            fillcolor=box["fill"],
            line=dict(color=box["line"], width=2),
            layer="below",
        )
        fig.add_annotation(
            x=centers[box["key"]][0],
            y=centers[box["key"]][1] + 0.045,
            xref="x",
            yref="y",
            text=f"<b>{box['title']}</b>",
            showarrow=False,
            font=dict(size=15, color="#0f172a"),
        )
        fig.add_annotation(
            x=centers[box["key"]][0],
            y=centers[box["key"]][1] - 0.045,
            xref="x",
            yref="y",
            text=str(box["body"]),
            showarrow=False,
            font=dict(size=12, color="#334155"),
        )

    arrow_style = dict(arrowhead=3, arrowsize=1.2, arrowwidth=2.5)
    fig.add_annotation(
        x=0.385,
        y=centers["training"][1],
        ax=0.305,
        ay=centers["training"][1],
        xref="x",
        yref="y",
        axref="x",
        ayref="y",
        showarrow=True,
        arrowcolor="#2563eb",
        **arrow_style,
    )
    fig.add_annotation(
        x=0.695,
        y=centers["model"][1],
        ax=0.615,
        ay=centers["model"][1],
        xref="x",
        yref="y",
        axref="x",
        ayref="y",
        showarrow=True,
        arrowcolor="#16a34a",
        **arrow_style,
    )
    fig.add_annotation(
        x=0.695,
        y=centers["descriptive"][1],
        ax=0.305,
        ay=centers["descriptive"][1],
        xref="x",
        yref="y",
        axref="x",
        ayref="y",
        showarrow=True,
        arrowcolor="#64748b",
        **arrow_style,
    )
    fig.add_annotation(
        x=0.50,
        y=0.93,
        xref="x",
        yref="y",
        text="<b>Pipeline logic: what trains the model, and what only gives context</b>",
        showarrow=False,
        font=dict(size=18, color="#0f172a"),
    )
    fig.add_annotation(
        x=0.50,
        y=0.50,
        xref="x",
        yref="y",
        text="Blue path = training and prediction. Gray path = interpretation only.",
        showarrow=False,
        font=dict(size=13, color="#475569"),
    )
    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False, range=[0, 1])
    fig.update_layout(
        height=430,
        margin=dict(l=20, r=20, t=25, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
    )
    return fig


def display_feature_types(metrics: Dict[str, Any]) -> None:
    feature_roles = metrics.get("feature_roles") or (metrics.get("feature_selection") or {}).get("feature_roles") or {}
    training_features = feature_roles.get("used_by_model") or metrics.get("feature_names") or []
    descriptive_features = feature_roles.get("descriptive_only") or []
    target_features = feature_roles.get("target_derived_excluded") or [metrics.get("target_column", "target_expression_score")]
    target_column = str(metrics.get("target_column") or "target_expression_score")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### Training Features")
        st.info("These variables are used directly by the model to learn.")
        st.caption(", ".join(str(v) for v in training_features[:14]) if training_features else "N/A")
        if len(training_features) > 14:
            with st.expander("Show all training features", expanded=False):
                st.write(", ".join(str(v) for v in training_features))
    with col2:
        st.markdown("#### Descriptive Features")
        st.info("These variables describe the sequence or context but are not used as model inputs.")
        st.caption(", ".join(str(v) for v in descriptive_features[:14]) if descriptive_features else "N/A")
        if len(descriptive_features) > 14:
            with st.expander("Show all descriptive features", expanded=False):
                st.write(", ".join(str(v) for v in descriptive_features))
    with col3:
        st.markdown("#### Proxy Target")
        st.warning("This is not a real experimental measurement. It is a simulated target used for learning.")
        st.caption(", ".join(str(v) for v in target_features) if target_features else target_column)

    st.markdown("#### Visual map of the pipeline")
    st.caption(
        "The upper path shows what the model actually uses to learn and predict. "
        "The lower path shows variables kept for explanation and biological context."
    )
    st.plotly_chart(_plot_pipeline_schema([str(v) for v in training_features], target_column), use_container_width=True)


def generate_metrics_conclusion(
    metrics: Dict[str, Any],
    model_df: pd.DataFrame,
    importance_df: pd.DataFrame,
    best_model: str,
    baseline_model: str,
) -> List[str]:
    best_row = _model_row(model_df, best_model)
    baseline_row = _model_row(model_df, baseline_model)
    best_rmse = best_row.get("validation_rmse", best_row.get("rmse"))
    baseline_rmse = baseline_row.get("validation_rmse", baseline_row.get("rmse"))
    top_features = importance_df["feature"].head(3).astype(str).tolist() if not importance_df.empty else []

    conclusions: List[str] = []
    if best_rmse is not None and baseline_rmse is not None and pd.notna(best_rmse) and pd.notna(baseline_rmse):
        if float(best_rmse) < float(baseline_rmse):
            conclusions.append(
                f"{best_model} beats the dummy baseline, so the model learns more than a simple average prediction."
            )
        else:
            conclusions.append(
                "The selected model does not clearly beat the dummy baseline, so its usefulness should be treated carefully."
            )
    if top_features:
        conclusions.append(f"The strongest global signals are {', '.join(top_features)}.")
    conclusions.append("Feature importance and local contributions make the model explainable enough for a proxy-based dashboard.")
    conclusions.append("The target remains a simulated proxy, not direct experimental expression data.")
    return conclusions


def _render_metric_cards(metrics: Dict[str, Any], model_df: pd.DataFrame, best_model: str, baseline_model: str) -> None:
    best_row = _model_row(model_df, best_model)
    baseline_row = _model_row(model_df, baseline_model)
    baseline_rmse = baseline_row.get("validation_rmse", baseline_row.get("rmse"))
    best_rmse = best_row.get("validation_rmse", best_row.get("rmse"))
    gain = (metrics.get("credibility_checks") or {}).get("validation_rmse_improvement_vs_baseline_pct")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Top-ranked model", best_model)
    c2.metric("RMSE", _fmt_dashboard_metric(best_row.get("rmse")))
    c3.metric("MAE", _fmt_dashboard_metric(best_row.get("mae")))
    c4.metric("R²", _fmt_dashboard_metric(best_row.get("r2")))
    c5.metric("Baseline RMSE", _fmt_dashboard_metric(baseline_rmse))
    c6.metric("Gain", _fmt_dashboard_pct(gain))

    if best_rmse is not None and baseline_rmse is not None and pd.notna(best_rmse) and pd.notna(baseline_rmse):
        if float(best_rmse) < float(baseline_rmse):
            st.success(f"{best_model} adds value: it reduces the error compared with the dummy baseline.")
        else:
            st.warning("The selected model does not improve over the dummy baseline on the main error metric.")


def _render_active_run_context(metrics: Dict[str, Any]) -> None:
    """Show which backend run produced the currently displayed metrics."""
    metadata = st.session_state.get("metadata", {}) or {}
    manifest = st.session_state.get("manifest", {}) or {}
    requested_params = st.session_state.get("active_pipeline_params", {}) or {}
    load_mode = st.session_state.get("artifact_load_mode") or "not loaded"

    st.markdown("### Active backend run")
    st.caption(
        "Metrics below are shown only for the artifact set loaded in this Streamlit session. "
        "Run the backend pipeline or explicitly load a manifest to update this context."
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Load mode", str(load_mode).replace("_", " "))
    c2.metric("Keyword", str(metadata.get("keyword", requested_params.get("keyword", "N/A"))))
    c3.metric("Protein limit", str(metadata.get("protein_limit", requested_params.get("protein_limit", "N/A"))))
    c4.metric("Random seed", str(metadata.get("random_seed", requested_params.get("random_seed", "N/A"))))
    c5.metric("Rows", str(metadata.get("rows_generated", manifest.get("rows_generated", "N/A"))))

    st.caption(f"Manifest: {st.session_state.get('manifest_path') or 'N/A'}")
    st.caption(f"Metrics target: {metrics.get('target_column', metadata.get('model_target_column', 'N/A'))}")

    if requested_params and metadata:
        mismatches = []
        for key in ("keyword", "protein_limit", "random_seed"):
            requested = requested_params.get(key)
            actual = metadata.get(key)
            if requested not in (None, "N/A") and actual not in (None, "N/A") and str(requested) != str(actual):
                mismatches.append(f"{key}: requested={requested}, loaded={actual}")
        if mismatches:
            st.warning(
                "The loaded artifacts do not match the last requested backend parameters: "
                + "; ".join(mismatches)
            )


def render_metrics_tab() -> None:
    _render_metrics_tab_impl()


def render_production_decision_dashboard_tab() -> None:
    st.subheader("Production Decision Dashboard")
    st.caption("Business decision view derived directly from DNA optimization and protein expression data.")

    df = st.session_state["dataset"]
    required_columns = {
        "cai",
        "gc_content",
        "rare_codon_ratio",
        "target_expression_score",
        "plant_host",
    }
    if df.empty:
        st.info("Load artifacts first from the Pipeline Execution tab.")
        return
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        st.warning("Required biological columns are missing for the dashboard.")
        st.caption(f"Missing columns: {', '.join(missing_columns)}")
        return

    view_df = df.copy()
    if "protein_name" in df.columns:
        protein_options = sorted(df["protein_name"].dropna().astype(str).unique().tolist())
        selected_protein = st.selectbox(
            "Protein focus",
            options=["All proteins"] + protein_options,
            index=0,
            help="Choose one protein for host-by-host production decisions, or keep all proteins aggregated.",
        )
        if selected_protein != "All proteins":
            view_df = view_df[view_df["protein_name"].astype(str) == selected_protein].copy()
    else:
        st.caption("protein_name column not found, dashboard is aggregated across all proteins.")

    if view_df.empty:
        st.warning("No rows available after protein filtering.")
        return

    host_summary = (
        view_df.groupby("plant_host", as_index=False)
        .agg(
            cai=("cai", "mean"),
            gc_content=("gc_content", "mean"),
            rare_codon_ratio=("rare_codon_ratio", "mean"),
            target_expression_score=("target_expression_score", "mean"),
            rows=("plant_host", "count"),
        )
        .sort_values("plant_host")
        .reset_index(drop=True)
    )

    host_summary["efficiency"] = host_summary["target_expression_score"].apply(_to_percent).clip(0.0, 100.0)

    host_summary["gc_stability"] = host_summary["gc_content"].apply(_gc_stability_score)
    host_summary["rare_codon_penalty"] = host_summary["rare_codon_ratio"].apply(_to_percent).clip(0.0, 100.0)

    host_summary["estimated_cost_tnd"] = (
        80.0
        + (100.0 - host_summary["efficiency"]) * 2.0
        + host_summary["rare_codon_penalty"] * 1.5
        + (100.0 - host_summary["gc_stability"]) * 1.0
    ).clip(80.0, 400.0)

    host_summary["time_minutes"] = (
        60.0
        + (100.0 - host_summary["efficiency"]) * 2.0
        + host_summary["rare_codon_penalty"] * 1.5
    ).clip(lower=0.0)

    host_summary["estimated_time"] = host_summary["time_minutes"].apply(_format_time_duration)

    host_summary["feasibility"] = (
        0.4 * host_summary["efficiency"]
        + 0.3 * host_summary["gc_stability"]
        + 0.3 * (100.0 - host_summary["rare_codon_penalty"])
    ).clip(0.0, 100.0)

    host_summary["normalized_cost"] = host_summary["estimated_cost_tnd"].apply(
        lambda value: _normalize_with_fixed_bounds(value, lower_bound=80.0, upper_bound=400.0)
    )
    host_summary["normalized_time"] = host_summary["time_minutes"].apply(
        lambda value: _normalize_with_fixed_bounds(value, lower_bound=60.0, upper_bound=410.0)
    )

    host_summary["final_score"] = (
        0.4 * host_summary["efficiency"]
        + 0.3 * host_summary["feasibility"]
        + 0.2 * (100.0 - host_summary["normalized_cost"])
        + 0.1 * (100.0 - host_summary["normalized_time"])
    ).clip(0.0, 100.0)

    rank_df = host_summary.sort_values("final_score", ascending=False).reset_index(drop=True)
    best_row = rank_df.iloc[0]

    st.markdown("### A. Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Best Plant Host", str(best_row["plant_host"]))
    c2.metric("Final Score", f"{_safe_float(best_row['final_score']):.1f}")
    c3.metric("Estimated Cost (TND)", f"{_safe_float(best_row['estimated_cost_tnd']):.1f}")
    c4.metric("Estimated Time", str(best_row["estimated_time"]))

    st.markdown("### B. Ranking Table")
    ranking_table = rank_df[
        [
            "plant_host",
            "efficiency",
            "estimated_cost_tnd",
            "estimated_time",
            "feasibility",
            "final_score",
        ]
    ].copy()
    for col in ["efficiency", "estimated_cost_tnd", "feasibility", "final_score"]:
        ranking_table[col] = ranking_table[col].round(2)
    st.dataframe(ranking_table, use_container_width=True, hide_index=True)

    st.markdown("### C. Charts")
    bar_fig = px.bar(
        rank_df,
        x="plant_host",
        y="final_score",
        color="plant_host",
        title="Final Score by Plant Host",
        labels={"plant_host": "Plant host", "final_score": "Final score (0-100)"},
    )
    st.plotly_chart(bar_fig, use_container_width=True)

    scatter_fig = px.scatter(
        rank_df,
        x="estimated_cost_tnd",
        y="efficiency",
        size="feasibility",
        color="plant_host",
        hover_data={
            "final_score": ":.2f",
            "estimated_time": True,
            "gc_stability": ":.2f",
            "rare_codon_penalty": ":.2f",
            "cai": ":.3f",
            "gc_content": ":.3f",
            "rare_codon_ratio": ":.3f",
            "plant_host": True,
        },
        title="Estimated Cost vs Efficiency",
        labels={
            "estimated_cost_tnd": "Estimated Cost (TND)",
            "efficiency": "Efficiency score",
            "feasibility": "Feasibility",
        },
        size_max=50,
    )
    st.plotly_chart(scatter_fig, use_container_width=True)

    st.markdown("### D. Transparency")
    st.info(
        "Cost and time are simulated production-oriented estimates derived from DNA optimization metrics "
        "(CAI, GC content, codon usage). They support decision-making but are not real laboratory measurements."
    )


def main() -> None:
    init_session_state()

    with st.sidebar:
        st.markdown("### Session Status")
        has_manifest = bool(st.session_state.manifest)
        has_dataset = "dataset" in st.session_state and not st.session_state["dataset"].empty
        has_quality = bool(st.session_state.quality)
        has_metrics = bool(st.session_state.metrics)

        st.write(f"Manifest loaded: {'Yes' if has_manifest else 'No'}")
        st.write(f"Dataset loaded: {'Yes' if has_dataset else 'No'}")
        st.write(f"Quality report loaded: {'Yes' if has_quality else 'No'}")
        st.write(f"Metrics loaded: {'Yes' if has_metrics else 'No'}")

        loaded_dataset_path = (st.session_state.artifact_paths or {}).get("dataset")
        st.caption(f"Loaded manifest path: {st.session_state.manifest_path or 'N/A'}")
        st.caption(f"Loaded dataset path: {loaded_dataset_path if loaded_dataset_path else 'N/A'}")

        if has_manifest:
            m = st.session_state.manifest
            st.markdown("### Run Summary")
            st.caption(
                f"keyword={m.get('keyword', 'N/A')} | rows={m.get('rows_generated', 'N/A')} | "
                f"training={m.get('training_enabled', 'N/A')}"
            )

    tabs = st.tabs(
        [
            "Home",
            "Pipeline Execution",
            "Data Quality",
            "Dataset Analysis",
            "3D Protein Structure",
            "DNA Optimization + DNA -> Protein Impact",
            "Metrics",
            "Production Decision Dashboard",
        ]
    )

    with tabs[0]:
        render_home_tab()
    with tabs[1]:
        render_execution_tab()
    with tabs[2]:
        render_quality_tab()
    with tabs[3]:
        render_dataset_tab()
    with tabs[4]:
        render_structure_tab()
    with tabs[5]:
        render_dna_fusion_tab()
    with tabs[6]:
        render_metrics_tab()
    with tabs[7]:
        render_production_decision_dashboard_tab()


if __name__ == "__main__":
    main()
