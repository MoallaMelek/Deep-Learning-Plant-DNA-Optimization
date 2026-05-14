import asyncio
import random
import numpy as np
import wave
import httpx
from pathlib import Path
from datetime import datetime

DATA_ROOT = Path(__file__).parent / "files" / "PlantSounds"
SERVER_URL = "http://localhost:8000/cropdna/api/iot/reading"

PLANTS = [
    {"id": "plant_001", "species": "tomato", "sector": "A"},
    {"id": "plant_002", "species": "tomato", "sector": "A"},
    {"id": "plant_003", "species": "tobacco","sector": "B"},
    {"id": "plant_004", "species": "tomato", "sector": "A"},
    {"id": "plant_005", "species": "tobacco","sector": "B"},
]

# Charger les vrais fichiers WAV du dataset
def load_wav_files():
    dry_path = DATA_ROOT / "Tomato Dry"
    cut_path = DATA_ROOT / "Tomato Cut"
    
    dry_files = list(dry_path.glob("*.wav"))[:50] if dry_path.exists() else []
    cut_files = list(cut_path.glob("*.wav"))[:50] if cut_path.exists() else []
    
    print(f"[SIM] DRY files: {len(dry_files)}")
    print(f"[SIM] CUT files: {len(cut_files)}")
    
    if not dry_files and not cut_files:
        print("[SIM] WARNING: No WAV files found!")
    
    return dry_files, cut_files

dry_wavs, cut_wavs = load_wav_files()

def simulate_sensors(stress_level: float) -> dict:
    """
    Simuler des capteurs réalistes basés sur le niveau de stress.
    stress_level : 0.0 = irrigué, 1.0 = très sec
    """
    # VWC diminue avec le stress
    vwc = max(0.001, 0.12 - stress_level * 0.11 
              + random.gauss(0, 0.005))
    
    # Température varie naturellement
    temperature = random.gauss(35, 3)
    
    # Humidité air
    humidity = random.gauss(45, 10)
    
    # EC (conductivité sol) — normale pour Tunisie
    ec = random.gauss(0.8, 0.2)
    
    return {
        "vwc"        : round(max(0.001, vwc), 4),
        "temperature": round(temperature, 1),
        "humidity"   : round(max(10, humidity), 1),
        "ec"         : round(max(0.1, ec), 2)
    }

async def simulate_plant(plant: dict):
    """Simuler une plante — cycle de sécheresse réaliste."""
    stress_level  = random.uniform(0, 1)
    irrigated_ago = random.randint(0, 48)  # heures depuis irrigation
    
    while True:
        # Choisir un vrai fichier WAV selon le niveau de stress
        if stress_level > 0.5:
            wav_path = str(random.choice(dry_wavs)) if dry_wavs else ""
        else:
            wav_path = str(random.choice(cut_wavs)) if cut_wavs else ""
        
        # Simuler capteurs
        sensors = simulate_sensors(stress_level)
        
        # Envoyer au server FastAPI
        try:
            async with httpx.AsyncClient() as client:
                await client.post(SERVER_URL, json={
                    "plant_id"   : plant["id"],
                    "species"    : plant["species"],
                    "wav_path"   : wav_path,
                    "timestamp"  : datetime.now().isoformat(),
                    **sensors
                })
        except Exception as e:
            print(f"[SIM] Error sending data: {e}")
        
        # Augmenter le stress progressivement
        stress_level = min(1.0, stress_level + random.uniform(0.05, 0.15))
        
        # Si irrigué → reset le stress
        if stress_level > 0.8:
            stress_level = 0.1
        
        # Attendre 10 secondes (simule 30 min en accéléré)
        await asyncio.sleep(10)

async def run_simulator():
    print("IoT Simulator started...")
    tasks = [simulate_plant(plant) for plant in PLANTS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(run_simulator())