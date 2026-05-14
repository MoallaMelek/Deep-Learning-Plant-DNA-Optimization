"""
llm_notifier.py
---------------
Notification via Twilio SMS ou WhatsApp
quand une action d'irrigation est déclenchée.
"""
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

import os
from twilio.rest import Client   # ← AJOUTE

TWILIO_SID   = os.getenv('TWILIO_SID',   '')
TWILIO_TOKEN = os.getenv('TWILIO_TOKEN', '')
TWILIO_FROM  = os.getenv('TWILIO_FROM',  '')
FARMER_PHONE = os.getenv('FARMER_PHONE', '')
USE_WHATSAPP = os.getenv('USE_WHATSAPP', '0') == '1'

print(f"[TWILIO] SID={TWILIO_SID[:10]}... FROM={TWILIO_FROM} TO={FARMER_PHONE}")

def _get_duration(action: str, vwc: float) -> int:
    """Calcule la durée d'irrigation en minutes selon le niveau de stress."""
    if vwc < 0.03:
        return 20
    elif vwc < 0.06:
        return 15
    elif vwc < 0.09:
        return 10
    else:
        return 5


async def generate_message(
    plant_id     : str,
    stress_type  : str,
    confidence   : float,
    vwc          : float,
    temperature  : float,
    action       : str,
    water_liters : float = 0,
    reasons      : list  = None,
) -> str:
    """Génère le message de notification."""
    duration = _get_duration(action, vwc)

    if action == 'IRRIGATE_NOW':
        emoji = '🚨'
        status = 'IRRIGATION DÉCLENCHÉE'
    elif action == 'IRRIGATE_SOON':
        emoji = '⚠️'
        status = 'IRRIGATION RECOMMANDÉE'
    else:
        emoji = '✅'
        status = 'SURVEILLANCE'

    msg = (
    f"IRA - فتح الصنبور\n"
    f"النبتة: {plant_id}\n"
    f"جفاف: {confidence:.0f}%\n"
    f"مدة الري: {duration} دقيقة\n"
    f"ماء: {water_liters:.1f}L"
    )
    return msg


async def send_notification(message: str, channel: str = 'sms') -> bool:
    """Envoie le message via SMS ou WhatsApp."""
    if not TWILIO_SID.startswith('AC'):
        print(f"[NOTIFY] Message (not sent):\n{message}")
        return False

    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)

        if USE_WHATSAPP or channel == 'whatsapp':
            from_num = f'whatsapp:{TWILIO_FROM}'
            to_num   = f'whatsapp:{FARMER_PHONE}'
        else:
            from_num = TWILIO_FROM
            to_num   = FARMER_PHONE

        msg = client.messages.create(
            body = message,
            from_= from_num,
            to   = to_num,
        )
        print(f"[NOTIFY] Message sent: {msg.sid}")
        return True

    except Exception as e:
        print(f"[NOTIFY] Failed: {e}")
        return False