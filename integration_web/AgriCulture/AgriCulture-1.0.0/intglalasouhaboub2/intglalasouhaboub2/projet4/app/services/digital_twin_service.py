from __future__ import annotations

from typing import Any, Dict, Optional

from app.predictor import DigitalTwinPredictor


class DigitalTwinService:
    _instance: Optional["DigitalTwinService"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "DigitalTwinService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.predictor = DigitalTwinPredictor()

    def root_payload(self) -> Dict[str, Any]:
        health = self.predictor.get_health()
        return {
            "message": "Digital Twin API is running",
            "status": "ok",
            "endpoints": ["/health", "/norms", "/predict", "/recommend", "/simulate", "/viz", "/viz/3d"],
            "health": health,
        }

    def health(self) -> Dict[str, Any]:
        return self.predictor.get_health()

    def norms(self) -> Dict[str, Any]:
        return self.predictor.get_norms()

    def predict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return self.predictor.predict(row)

    def recommend(self, variety_name: Optional[str], traits: Optional[Dict[str, Any]], horizon: str, scenario: str) -> Dict[str, Any]:
        return self.predictor.recommend(variety_name, traits, horizon, scenario)

    def simulate(self, row: Dict[str, Any], n_jours: int, scenario: str) -> Dict[str, Any]:
        return self.predictor.simulate(row, n_jours=n_jours, scenario=scenario)

    def viz_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.predictor.get_viz_data(payload)

    def dashboard_data(self, n_jours: int = 200) -> Dict[str, Any]:
        return self.predictor.get_dashboard_payload(n_jours=n_jours)
