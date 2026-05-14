from __future__ import annotations

import json
import warnings

warnings.filterwarnings("ignore")

import requests

BASE_URL = "http://127.0.0.1:8001"


def main() -> None:
    health = requests.get(f"{BASE_URL}/health", timeout=15)
    print("GET /health ->", health.status_code)
    print(json.dumps(health.json(), indent=2))

    train_payload = {"epochs": 5, "batch_size": 256, "learning_rate": 0.001}
    train = requests.post(f"{BASE_URL}/train", json=train_payload, timeout=600)
    print("POST /train ->", train.status_code)
    print(json.dumps(train.json(), indent=2))

    predict_payload = {
        "days": 30,
        "use_open_meteo": True,
        "auto_train_if_missing": True,
        "generate_chart": True,
        "chart_as_base64": False,
        "dna_sequence": "ATGGCTTCTTCTTCTGCTTCTCCGTTGCTGCTGCTGTTGATGGTGGTGATGCTGCTGATGATGCTGATGCTGATGTTGCTGATGATGCTGCTGCTGATGCTGATGATGCTGATGATGCTGATGATGCTGATGATGCTGATGATGCTGCTGATGATGCTGATGATGCTGCTGATGATGCTGCTGATGAT",
    }
    prediction = requests.post(f"{BASE_URL}/predict-growth", json=predict_payload, timeout=600)
    print("POST /predict-growth ->", prediction.status_code)
    data = prediction.json()
    print(
        json.dumps(
            {
                "dna_source": data.get("dna_source"),
                "climate_source": data.get("climate_source"),
                "model_status": data.get("model_status"),
                "summary": data.get("summary"),
                "chart_path": data.get("chart_path"),
                "warnings": data.get("warnings"),
            },
            indent=2,
        )
    )

    simulate_payload = predict_payload | {"generate_gif": True, "gif_filename": "latest_growth.gif"}
    simulation = requests.post(f"{BASE_URL}/simulate", json=simulate_payload, timeout=900)
    print("POST /simulate ->", simulation.status_code)
    sim_data = simulation.json()
    print(json.dumps({"gif_path": sim_data.get("gif_path"), "summary": sim_data.get("summary")}, indent=2))


if __name__ == "__main__":
    main()
