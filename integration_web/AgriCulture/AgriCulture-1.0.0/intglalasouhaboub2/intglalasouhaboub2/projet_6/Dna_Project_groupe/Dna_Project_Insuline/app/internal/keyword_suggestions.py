"""Local keyword suggestions for the pipeline keyword input."""

from __future__ import annotations

from typing import Dict, List


PROTEIN_KEYWORD_SUGGESTIONS: List[Dict[str, str]] = [
    {
        "keyword": "insulin",
        "description": "Small hormone protein; useful for quick demonstration runs.",
        "expected_volume": "small",
        "estimated_results": "approx. 10-50",
        "suggested_limit": "10-30",
    },
    {
        "keyword": "hemoglobin",
        "description": "Oxygen transport proteins; balanced mid-size dataset.",
        "expected_volume": "medium",
        "estimated_results": "approx. 40-120",
        "suggested_limit": "30-100",
    },
    {
        "keyword": "albumin",
        "description": "Abundant plasma protein; good mid-size dataset.",
        "expected_volume": "medium",
        "estimated_results": "approx. 40-150",
        "suggested_limit": "30-100",
    },
    {
        "keyword": "kinase",
        "description": "Large protein family; many related proteins.",
        "expected_volume": "large",
        "estimated_results": "100+",
        "suggested_limit": "100-300+",
    },
    {
        "keyword": "enzyme",
        "description": "Broad functional keyword; many results.",
        "expected_volume": "large",
        "estimated_results": "100+",
        "suggested_limit": "100-300+",
    },
    {
        "keyword": "antibody",
        "description": "Immune-related proteins; larger collections.",
        "expected_volume": "large",
        "estimated_results": "100+",
        "suggested_limit": "100-300+",
    },
    {
        "keyword": "GFP",
        "description": "Fluorescent protein; small to medium dataset.",
        "expected_volume": "small",
        "estimated_results": "approx. 15-60",
        "suggested_limit": "10-30",
    },
    {
        "keyword": "amylase",
        "description": "Enzyme family; moderate number of entries.",
        "expected_volume": "medium",
        "estimated_results": "approx. 30-120",
        "suggested_limit": "30-100",
    },
    {
        "keyword": "collagen",
        "description": "Structural proteins; moderate volume.",
        "expected_volume": "medium",
        "estimated_results": "approx. 30-120",
        "suggested_limit": "30-100",
    },
    {
        "keyword": "receptor",
        "description": "Broad membrane protein keyword; many results.",
        "expected_volume": "large",
        "estimated_results": "100+",
        "suggested_limit": "100-300+",
    },
    {
        "keyword": "transporter",
        "description": "Membrane transport proteins; many results.",
        "expected_volume": "large",
        "estimated_results": "100+",
        "suggested_limit": "100-300+",
    },
    {
        "keyword": "glucose",
        "description": "Glucose-associated proteins and transport/metabolism entries.",
        "expected_volume": "medium",
        "estimated_results": "approx. 30-120",
        "suggested_limit": "30-100",
    },
    {
        "keyword": "glucagon",
        "description": "Peptide hormone involved in glucose regulation.",
        "expected_volume": "small",
        "estimated_results": "approx. 10-50",
        "suggested_limit": "10-30",
    },
    {
        "keyword": "glutathione",
        "description": "Redox and detoxification related enzymes and binding proteins.",
        "expected_volume": "medium",
        "estimated_results": "approx. 30-120",
        "suggested_limit": "30-100",
    },
    {
        "keyword": "growth factor",
        "description": "Cell signaling proteins that regulate growth and differentiation.",
        "expected_volume": "medium",
        "estimated_results": "approx. 40-150",
        "suggested_limit": "30-100",
    },
    {
        "keyword": "cytochrome",
        "description": "Electron transport and heme-containing protein families.",
        "expected_volume": "large",
        "estimated_results": "100+",
        "suggested_limit": "100-300+",
    },
    {
        "keyword": "oxidase",
        "description": "Oxidation-reduction enzymes across diverse organisms.",
        "expected_volume": "large",
        "estimated_results": "100+",
        "suggested_limit": "100-300+",
    },
    {
        "keyword": "polymerase",
        "description": "DNA and RNA polymerization enzymes.",
        "expected_volume": "large",
        "estimated_results": "100+",
        "suggested_limit": "100-300+",
    },
    {
        "keyword": "protease",
        "description": "Protein-cleaving enzymes; broad but biologically focused.",
        "expected_volume": "large",
        "estimated_results": "100+",
        "suggested_limit": "100-300+",
    },
    {
        "keyword": "lipase",
        "description": "Lipid-hydrolyzing enzymes; useful medium-to-large query.",
        "expected_volume": "medium",
        "estimated_results": "approx. 40-150",
        "suggested_limit": "30-100",
    },
    {
        "keyword": "cellulase",
        "description": "Cellulose-degrading enzyme family common in microbial datasets.",
        "expected_volume": "medium",
        "estimated_results": "approx. 30-120",
        "suggested_limit": "30-100",
    },
    {
        "keyword": "keratin",
        "description": "Structural intermediate filament proteins.",
        "expected_volume": "medium",
        "estimated_results": "approx. 30-120",
        "suggested_limit": "30-100",
    },
    {
        "keyword": "elastin",
        "description": "Extracellular matrix protein involved in tissue elasticity.",
        "expected_volume": "small",
        "estimated_results": "approx. 10-50",
        "suggested_limit": "10-30",
    },
    {
        "keyword": "fibrinogen",
        "description": "Blood clotting protein family; focused medium dataset.",
        "expected_volume": "medium",
        "estimated_results": "approx. 30-100",
        "suggested_limit": "30-100",
    },
    {
        "keyword": "casein",
        "description": "Milk protein family; useful compact protein query.",
        "expected_volume": "small",
        "estimated_results": "approx. 10-50",
        "suggested_limit": "10-30",
    },
]


def get_all_keyword_suggestions() -> List[Dict[str, str]]:
    return list(PROTEIN_KEYWORD_SUGGESTIONS)


def _suggestion_rank(suggestion: Dict[str, str], query_text: str) -> tuple[int, str]:
    keyword = suggestion.get("keyword", "").lower()
    description = suggestion.get("description", "").lower()
    if keyword.startswith(query_text):
        return (0, keyword)
    if query_text in keyword:
        return (1, keyword)
    if query_text in description:
        return (2, keyword)
    return (3, keyword)


def get_keyword_suggestions(query: str) -> List[Dict[str, str]]:
    query_text = (query or "").strip().lower()
    if not query_text:
        return []

    suggestions: List[Dict[str, str]] = []
    for suggestion in PROTEIN_KEYWORD_SUGGESTIONS:
        keyword = suggestion.get("keyword", "").lower()
        description = suggestion.get("description", "").lower()
        if query_text in keyword or query_text in description:
            suggestions.append(suggestion)
    return sorted(suggestions, key=lambda suggestion: _suggestion_rank(suggestion, query_text))


def estimate_keyword_volume(keyword: str) -> str:
    keyword_text = (keyword or "").strip().lower()
    for suggestion in PROTEIN_KEYWORD_SUGGESTIONS:
        if suggestion.get("keyword", "").lower() == keyword_text:
            return suggestion.get("expected_volume", "unknown")
    return "unknown"
