from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional
import asyncio
import os
import uuid
from datetime import datetime
import numpy as np

from xai import run_xai_pipeline
from database import (init_db, save_reading, get_all_plants_latest,
                      get_plant_history, get_dashboard_stats)
from cnn_predict import predict_stress, predict_stress_from_signal
from decision_engine import compute_decision
from llm_notifier import generate_message, send_notification
from simulator import run_simulator
from preprocessing import load_wav_signal, denoise_signal

router = APIRouter(tags=["IoT Greenhouse"])

ENABLE_DENOISE       = os.getenv("ENABLE_DENOISE", "1") == "1"
ENABLE_XAI_ON_URGENT = os.getenv("ENABLE_XAI_ON_URGENT", "1") == "1"
MODEL_VERSION        = os.getenv("MODEL_VERSION", "plant_stress_detector_IRA.keras")

active_connections: list[WebSocket] = []


@router.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast(data: dict):
    for connection in active_connections:
        try:
            await connection.send_json(data)
        except Exception:
            pass


class IoTReading(BaseModel):
    plant_id    : str
    species     : Optional[str]   = "tomato"
    wav_path    : str
    timestamp   : Optional[str]   = None
    vwc         : Optional[float] = 0.05
    temperature : Optional[float] = 25.0
    humidity    : Optional[float] = 50.0
    ec          : Optional[float] = 0.8


@router.post("/reading")
async def receive_iot_reading(reading: IoTReading):
    try:
        inference_id    = str(uuid.uuid4())
        timestamp       = reading.timestamp or datetime.now().isoformat()
        xai_enabled     = False
        gradcam_path    = None

        # 1. CNN
        try:
            if ENABLE_DENOISE:
                signal          = load_wav_signal(reading.wav_path)
                denoised_signal = denoise_signal(signal)
                cnn_result      = predict_stress_from_signal(denoised_signal)
            else:
                denoised_signal = None
                cnn_result      = predict_stress(reading.wav_path)
        except Exception as e:
            print(f"[WARN] CNN failed: {e}")
            cnn_result      = {"stress_type": "DRY", "confidence": 75.0, "raw_pred": 0.25}
            denoised_signal = np.zeros(1001, dtype=np.float32)

        # 2. Decision
        try:
            decision = compute_decision(
                stress_type = cnn_result["stress_type"],
                confidence  = cnn_result["confidence"],
                vwc         = reading.vwc,
                temperature = reading.temperature,
                ec          = reading.ec,
                plant_id    = reading.plant_id,
            )
        except Exception as e:
            print(f"[WARN] Decision failed: {e}")
            decision = {"action": "MONITOR", "score": 0,
                        "water_liters": 0, "reasons": []}

        # 3. Result
        result = {
            "plant_id":        reading.plant_id,
            "timestamp":       timestamp,
            "stress_type":     cnn_result["stress_type"],
            "confidence":      cnn_result["confidence"],
            "vwc":             reading.vwc,
            "temperature":     reading.temperature,
            "humidity":        reading.humidity,
            "ec":              reading.ec,
            "action":          decision["action"],
            "score":           decision["score"],
            "water_liters":    decision["water_liters"],
            "reasons":         decision["reasons"],
            "denoise_applied": ENABLE_DENOISE,
            "xai_enabled":     False,
            "gradcam_path":    None,
            "model_version":   MODEL_VERSION,
            "inference_id":    inference_id,
        }

        # 4. XAI
        if ENABLE_XAI_ON_URGENT and decision["action"] in [
                "IRRIGATE_NOW", "DRAINAGE_NEEDED"]:
            try:
                xai_signal   = (denoised_signal
                                if denoised_signal is not None
                                and len(denoised_signal) > 0
                                else np.zeros(1001, dtype=np.float32))
                xai_result   = run_xai_pipeline(
                    xai_signal, reading.plant_id, timestamp)
                xai_enabled  = True
                gradcam_path = xai_result["gradcam_path"]
                result.update({
                    "xai_enabled":     True,
                    "gradcam_path":    gradcam_path,
                    "peak_time_ms":    xai_result["peak_time_ms"],
                    "biological_hint": xai_result["biological_hint"],
                })
            except Exception as e:
                print(f"[WARN] XAI failed: {e}")

        # 5. Save
        result["xai_enabled"]  = xai_enabled
        result["gradcam_path"] = gradcam_path
        print(f"[IoT] {result['plant_id']} | {result['action']} | {result['confidence']}%")
        save_reading(result)

        # 6. LLM
        if decision["action"] in ["IRRIGATE_NOW", "DRAINAGE_NEEDED"]:
            try:
                message = await generate_message(
                    plant_id     = reading.plant_id,
                    stress_type  = cnn_result["stress_type"],
                    confidence   = cnn_result["confidence"],
                    vwc          = reading.vwc,
                    temperature  = reading.temperature,
                    action       = decision["action"],
                    water_liters = decision["water_liters"],
                    reasons      = decision["reasons"],
                )
                result["llm_message"] = message
                await send_notification(message, channel="sms")
            except Exception as e:
                print(f"[WARN] LLM failed: {e}")

        # 7. Broadcast
        await broadcast({"type": "plant_update", "data": result})
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@router.get("/plants")
def get_plants():
    return get_all_plants_latest()


@router.get("/plants/{plant_id}/history")
def get_history(plant_id: str, limit: int = 100):
    return get_plant_history(plant_id, limit)


@router.get("/dashboard/stats")
def get_stats():
    return get_dashboard_stats()


@router.get("/debug/latest")
def debug_latest():
    import sqlite3
    conn = sqlite3.connect("ira_plants.db")
    cursor = conn.execute(
        "SELECT plant_id, timestamp, confidence, action "
        "FROM readings ORDER BY id DESC LIMIT 20"
    )
    rows = [dict(zip([d[0] for d in cursor.description], row))
            for row in cursor.fetchall()]
    conn.close()
    return rows


simulator_task = None


@router.post("/simulate/start")
async def start_simulator():
    global simulator_task
    if simulator_task is None:
        simulator_task = asyncio.create_task(run_simulator())
        return {"status": "simulator started"}
    return {"status": "already running"}


@router.post("/simulate/stop")
async def stop_simulator():
    global simulator_task
    if simulator_task:
        simulator_task.cancel()
        simulator_task = None
        return {"status": "simulator stopped"}
    return {"status": "not running"}
