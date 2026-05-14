from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_endpoint():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "/predict" in body["endpoints"]


def test_predict_endpoint_first_run():
    payload = {
        "row": {
            "pred_drought": 0.60,
            "pred_salt": 0.50,
            "pred_yield": 0.75,
            "pred_disease": 0.70,
        }
    }
    r = client.post("/predict", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "twso" in data and data["twso"] > 0
    assert "alertes" in data


def test_viz_3d_endpoint():
    r = client.get("/viz/3d")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "data:image/png;base64" in r.text
