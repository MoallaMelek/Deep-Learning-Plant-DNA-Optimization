import os
import httpx
from datetime import datetime

# Choisir : "claude" ou "openai"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "claude")

async def generate_message(
    plant_id    : str,
    stress_type : str,
    confidence  : float,
    vwc         : float,
    temperature : float,
    action      : str,
    water_liters: float,
    reasons     : list
) -> str:

    prompt = f"""
    Tu es le système de monitoring IRA pour une serre agricole
    en Tunisie. Génère un message d'alerte court et clair
    en français pour le propriétaire.

    Données capteurs :
    - Plante ID      : {plant_id}
    - Type de stress : {stress_type}
    - Confiance CNN  : {confidence:.1f}%
    - VWC (humidité) : {vwc}
    - Température    : {temperature}°C
    - Action système : {action}
    - Eau à donner   : {water_liters}L
    - Raisons        : {', '.join(reasons)}

    Format du message :
    - Commence par une icône emoji selon l'urgence
    - Maximum 4 lignes
    - Mentionne l'action prise automatiquement
    - Donne une recommandation concrète
    - Ton professionnel mais accessible

    Génère uniquement le message, sans explication.
    """

    if LLM_PROVIDER == "claude":
        return await call_claude(prompt)
    else:
        return await call_openai(prompt)

async def call_claude(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key"        : os.getenv("ANTHROPIC_API_KEY"),
                "anthropic-version": "2023-06-01",
                "content-type"     : "application/json"
            },
            json={
                "model"     : "claude-sonnet-4-20250514",
                "max_tokens": 300,
                "messages"  : [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        data = response.json()
        return data["content"][0]["text"]

async def call_openai(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type" : "application/json"
            },
            json={
                "model"   : "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300
            },
            timeout=30
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]

async def send_notification(
    message : str,
    channel : str = "email"
) -> bool:

    if channel == "whatsapp":
        return await send_whatsapp(message)
    elif channel == "email":
        return await send_email(message)
    elif channel == "sms":
        return await send_sms(message)
    return False

async def send_whatsapp(message: str) -> bool:
    # Twilio WhatsApp API
    from twilio.rest import Client
    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )
    client.messages.create(
        from_='whatsapp:+14155238886',
        to   =f'whatsapp:{os.getenv("OWNER_PHONE")}',
        body =message
    )
    return True

async def send_email(message: str) -> bool:
    import smtplib
    from email.mime.text import MIMEText
    
    msg = MIMEText(message)
    msg['Subject'] = 'IRA Plant Alert'
    msg['From']    = os.getenv("SMTP_FROM")
    msg['To']      = os.getenv("OWNER_EMAIL")
    
    with smtplib.SMTP(os.getenv("SMTP_HOST"), 587) as server:
        server.starttls()
        server.login(
            os.getenv("SMTP_USER"),
            os.getenv("SMTP_PASS")
        )
        server.send_message(msg)
    return True