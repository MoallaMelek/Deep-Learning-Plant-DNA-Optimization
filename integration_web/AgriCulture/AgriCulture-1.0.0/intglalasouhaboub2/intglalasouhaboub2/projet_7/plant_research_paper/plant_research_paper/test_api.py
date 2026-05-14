from __future__ import annotations

import json
import warnings

warnings.filterwarnings("ignore")

import requests
from requests.exceptions import RequestException

BASE_URL = "http://127.0.0.1:8000"


def main() -> None:
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=15)
    except RequestException as exc:
        print("API non joignable sur http://127.0.0.1:8000.")
        print("Démarre d'abord le serveur: python run_api.py")
        print(f"Détail: {exc}")
        return

    print("GET /health ->", health.status_code)
    print(json.dumps(health.json(), indent=2))

    payload = {
        "topic": "Drought resistance genes in maize",
        "dna_sequence": "ATGCGTACGTAGCTAGCTAGCTAGATGCGTACGTAGCTAGCTAGCTAG",
        "max_revision_rounds": 2,
    }
    generation = requests.post(f"{BASE_URL}/generate", json=payload, timeout=300)
    print("POST /generate ->", generation.status_code)
    data = generation.json()
    print(
        json.dumps(
            {
                "pdf_path": data.get("pdf_path"),
                "tex_path": data.get("tex_path"),
                "json_path": data.get("json_path"),
                "figure_paths": data.get("figure_paths"),
                "warnings": data.get("warnings"),
            },
            indent=2,
        )
    )

    demo = requests.post(f"{BASE_URL}/generate/demo", timeout=300)
    print("POST /generate/demo ->", demo.status_code)
    print(json.dumps({"pdf_path": demo.json().get("pdf_path")}, indent=2))


if __name__ == "__main__":
    main()
