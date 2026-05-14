import sqlite3
from datetime import datetime

DB_PATH = "ira_plants.db"

def _get_conn():
    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
        timeout=30
    )
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = _get_conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_id        TEXT NOT NULL,
            timestamp       TEXT NOT NULL,
            stress_type     TEXT,
            confidence      REAL,
            vwc             REAL,
            temperature     REAL,
            humidity        REAL,
            ec              REAL,
            action          TEXT,
            irrigated       INTEGER DEFAULT 0,
            message_sent    INTEGER DEFAULT 0,
            denoise_applied INTEGER DEFAULT 0,
            xai_enabled     INTEGER DEFAULT 0,
            gradcam_path    TEXT,
            model_version   TEXT,
            inference_id    TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("[DB] Database initialized.")

def save_reading(data: dict):
    print(f"[DB] Saving: {data.get('plant_id')} | {data.get('action')}")
    conn = _get_conn()
    try:
        conn.execute('''
            INSERT INTO readings
            (plant_id, timestamp, stress_type, confidence,
             vwc, temperature, humidity, ec, action, irrigated,
             denoise_applied, xai_enabled, gradcam_path,
             model_version, inference_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['plant_id'],
            data.get('timestamp', datetime.now().isoformat()),
            data['stress_type'],
            data['confidence'],
            data.get('vwc', 0),
            data.get('temperature', 0),
            data.get('humidity', 0),
            data.get('ec', 0),
            data['action'],
            1 if data.get('action') == 'IRRIGATE_NOW' else 0,
            1 if data.get('denoise_applied') else 0,
            1 if data.get('xai_enabled') else 0,
            data.get('gradcam_path'),
            data.get('model_version', 'unknown'),
            data.get('inference_id'),
        ))
        conn.commit()
        print(f"[DB] Saved OK: {data.get('plant_id')}")
    except Exception as e:
        print(f"[DB] ERROR: {e}")
    finally:
        conn.close()

def get_all_plants_latest():
    conn = _get_conn()
    cursor = conn.execute('''
        SELECT * FROM readings
        WHERE id IN (
            SELECT MAX(id) FROM readings
            GROUP BY plant_id
        )
        AND plant_id != 'string'
        ORDER BY plant_id
    ''')
    columns = [d[0] for d in cursor.description]
    rows    = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_plant_history(plant_id: str, limit: int = 100):
    conn = _get_conn()
    cursor = conn.execute('''
        SELECT * FROM readings
        WHERE plant_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (plant_id, limit))
    columns = [d[0] for d in cursor.description]
    rows    = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_dashboard_stats():
    conn = _get_conn()
    total = conn.execute(
        "SELECT COUNT(*) FROM readings"
    ).fetchone()[0]
    irrigations = conn.execute(
        "SELECT COUNT(*) FROM readings WHERE irrigated=1"
    ).fetchone()[0]
    dry_count = conn.execute(
        "SELECT COUNT(*) FROM readings WHERE stress_type='DRY'"
    ).fetchone()[0]
    conn.close()
    return {
        "total_readings":    total,
        "total_irrigations": irrigations,
        "dry_detections":    dry_count,
        "water_saved_pct":   40,
    }

def get_debug_latest(limit: int = 20):
    conn = _get_conn()
    cursor = conn.execute('''
        SELECT plant_id, timestamp, confidence, action
        FROM readings
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    rows = [dict(zip([d[0] for d in cursor.description], row))
            for row in cursor.fetchall()]
    conn.close()
    return rows