from datetime import datetime, timedelta
from database import get_plant_history

def compute_decision(
    stress_type : str,
    confidence  : float,
    vwc         : float,
    temperature : float,
    ec          : float,
    plant_id    : str
) -> dict:
    
    # Vérifier dernière irrigation
    history = get_plant_history(plant_id, limit=10)
    last_irrigation = None
    hours_since_irrigation = 999
    
    for reading in history:
        if reading['irrigated'] == 1:
            last_time = datetime.fromisoformat(reading['timestamp'])
            hours_since_irrigation = (
                datetime.now() - last_time
            ).total_seconds() / 3600
            last_irrigation = reading['timestamp']
            break
    
    # Score de décision
    score = 0
    reasons = []
    
    # Signal acoustique (poids 50%)
    if stress_type == 'DRY':
        score += confidence * 0.5
        reasons.append(f"Acoustic: DRY {confidence:.1f}%")
    
    # VWC (poids 30%)
    if vwc < 0.01:
        score += 30
        reasons.append(f"VWC critical: {vwc}")
    elif vwc < 0.05:
        score += 15
        reasons.append(f"VWC low: {vwc}")
    
    # Température (poids 10%)
    if temperature > 35:
        score += 10
        reasons.append(f"High temp: {temperature}°C")
    
    # EC — salinité (override)
    if ec > 2.0:
        return {
            "action"    : "DRAINAGE_NEEDED",
            "score"     : score,
            "reasons"   : ["High EC — salinity issue"],
            "water_liters": 0
        }
    
    # Anti-irrigation récente
    if hours_since_irrigation < 4:
        return {
            "action"    : "RECENTLY_IRRIGATED",
            "score"     : score,
            "reasons"   : [f"Irrigated {hours_since_irrigation:.1f}h ago"],
            "water_liters": 0
        }
    
    # Décision finale
    if score > 75:
        action = "IRRIGATE_NOW"
        water  = calculate_water_volume("tomato", vwc)
    elif score > 50:
        action = "IRRIGATE_SOON"
        water  = calculate_water_volume("tomato", vwc) * 0.5
    elif score > 30:
        action = "MONITOR"
        water  = 0
    else:
        action = "PLANT_OK"
        water  = 0
    
    return {
        "action"      : action,
        "score"       : round(score, 1),
        "reasons"     : reasons,
        "water_liters": water,
        "hours_since_irrigation": round(hours_since_irrigation, 1)
    }

def calculate_water_volume(species: str, vwc: float) -> float:
    base = {"tomato": 1.5, "tobacco": 1.0, "wheat": 0.8}
    vol  = base.get(species, 1.0)
    if vwc < 0.005:
        vol *= 1.5   # très sec → plus d'eau
    return round(vol, 2)