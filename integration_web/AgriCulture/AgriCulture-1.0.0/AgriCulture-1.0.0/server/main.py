import os
from pathlib import Path
import sys
import asyncio
import random
import time
import json
import subprocess
from datetime import datetime
from typing import List, Optional, Dict
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from starlette.background import BackgroundTask
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# --- ODM Project Integration ---
_odm_path = Path(__file__).parent.parent.parent / 'intglalasouhaboub2' / 'intglalasouhaboub2' / 'odm_project'
if _odm_path.exists():
    sys.path.append(str(_odm_path))
    try:
        from app.routes import router as odm_router
    except Exception as e:
        print(f"[ODM] Failed to import ODM routes: {e}")
        odm_router = None
else:
    print(f"[ODM] Path not found: {_odm_path}")
    odm_router = None

# --- RAG Project Integration (Module 7) ---
_rag_path = Path(__file__).parent.parent.parent / 'intglalasouhaboub2' / 'intglalasouhaboub2' / 'projet5'
if _rag_path.exists():
    sys.path.append(str(_rag_path))
    groq_key = os.getenv('GROQ_API_KEY') or os.getenv('GROQ_KEY')
    if groq_key:
        os.environ['GROQ_KEY'] = groq_key
else:
    print(f"[RAG] Path not found: {_rag_path}")

# Load Twilio credentials from projet5/.env
SMS_ENABLED = False # Disabled by default due to trial limits
try:
    from dotenv import load_dotenv
    env_path = _rag_path / '.env'
    load_dotenv(dotenv_path=env_path)
    
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
    USER_PHONE_NUMBER = os.getenv('USER_PHONE_NUMBER')
    
    from twilio.rest import Client as TwilioClient
    twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
except Exception as e:
    print(f"[SMS] Twilio initialization failed: {e}")
    twilio_client = None

# --- RAG Components Lazy Loaders ---
@lru_cache(maxsize=1)
def get_rag_engine():
    old_cwd = os.getcwd()
    try:
        os.chdir(str(_rag_path))
        from search_engine import DNASearchEngine
        from rag_engine import RAGEngine
        engine = DNASearchEngine()
        rag = RAGEngine(groq_key=os.environ.get('GROQ_KEY'))
        return engine, rag
    except Exception as e:
        print(f"[RAG] Failed to load engines: {e}")
        return None, None
    finally:
        os.chdir(old_cwd)

def generate_pdf_direct(html_file, pdf_file):
    """Fallback PDF generator using wkhtmltopdf binary directly"""
    wkhtml_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    if not os.path.exists(wkhtml_path):
        return False
    try:
        subprocess.run([wkhtml_path, "--enable-local-file-access", "--quiet", html_file, pdf_file], check=True)
        return True
    except Exception as e:
        print(f"[PDF] Error: {e}")
        return False

# --- Models ---
class PlantState(BaseModel):
    id: str
    name: str
    status: str
    vwc: float
    temp: float
    humidity: float
    last_updated: str

class RAGPdfRequest(BaseModel):
    sequence: str
    accession: Optional[str] = ""
    gene: Optional[str] = ""

# --- Global State ---
plants_db = {
    "P1": {"id": "P1", "name": "Wheat Alpha", "status": "HEALTHY", "vwc": 35.5, "temp": 22.4, "humidity": 45.0, "last_updated": ""},
    "P2": {"id": "P2", "name": "Barley Beta", "status": "HEALTHY", "vwc": 38.2, "temp": 21.8, "humidity": 48.2, "last_updated": ""},
    "P3": {"id": "P3", "name": "Durum Delta", "status": "DRY", "vwc": 12.4, "temp": 25.6, "humidity": 30.5, "last_updated": ""},
}

notification_cooldowns = {} # id -> timestamp

app = FastAPI(title="AgriDNA API", description="Scientific and technological platform for plant DNA analysis")

# Mount ODM Router
if odm_router:
    app.include_router(odm_router, prefix="/api/odm", tags=["ODM"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SMS Utils ---
def send_sms_sync(message: str):
    if not SMS_ENABLED or not twilio_client:
        return
    try:
        twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=USER_PHONE_NUMBER
        )
        print(f"[SMS] Sent: {message}")
    except Exception as e:
        print(f"[SMS] Error: {e}")

# --- Endpoints ---
@app.get("/api/plants")
async def get_plants():
    for p in plants_db.values():
        p["last_updated"] = datetime.now().isoformat()
    return list(plants_db.values())

# --- RAG Endpoints (Module 7) ---
@app.post("/search")
@app.post("/api/rag/search")
async def search(req: Dict, request: Request):
    engine, _ = get_rag_engine()
    if not engine: raise HTTPException(status_code=503, detail="Search Engine not initialized")
    from input_parser import InputParser
    parser = InputParser(engine)
    query = req.get("query") or req.get("question")
    results = parser.parse_and_search(query, top_k=req.get("top_k", 10))
    return {"query": query, "results": [r.to_dict() for r in results]}

@app.post("/predict")
@app.post("/api/rag/predict")
async def predict_trait(req: Dict, request: Request):
    engine, _ = get_rag_engine()
    if not engine: raise HTTPException(status_code=503, detail="Search Engine not initialized")
    return engine.predict_trait(req.get("sequence"))

@app.post("/rag")
@app.post("/api/rag/answer")
async def rag_answer(req: Dict, request: Request):
    engine, rag = get_rag_engine()
    if not engine or not rag: raise HTTPException(status_code=503, detail="RAG Engine not initialized")
    from input_parser import InputParser
    parser = InputParser(engine)
    query = req.get("query") or req.get("question")
    results = parser.parse_and_search(query, top_k=req.get("top_k", 10))
    answer = rag.answer(req.get("question") or query, results)
    return {
        "answer": answer.answer,
        "articles": [{"title": a.title, "pmid": a.pmid, "url": a.pubmed_url()} for a in answer.articles],
        "sequences": [r.to_dict() for r in results]
    }

@app.post("/api/rag/pdf")
async def rag_pdf_report(req: RAGPdfRequest):
    engine, rag = get_rag_engine()
    if not engine or not rag:
        raise HTTPException(status_code=503, detail="RAG Engine not initialized")
    try:
        from fiche_generator import generate_fiche
        print(f"[PDF] Generating report for: {req.accession or 'raw_sequence'}")
        
        # Predict trait first to populate engine state
        pred = engine.predict_trait(req.sequence)
        engine._last_xgb_prediction = pred
        
        # Absolute paths for temporary files
        tmp_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
        base_dir = Path(__file__).parent.absolute()
        html_path = str(base_dir / f"report_{tmp_id}.html")
        pdf_path = str(base_dir / f"report_{tmp_id}.pdf")
        
        print(f"[PDF] HTML Path: {html_path}")
        
        # Generate HTML fiche
        generate_fiche(
            engine=engine, 
            rag=rag, 
            sequence=req.sequence, 
            accession=req.accession, 
            gene=req.gene, 
            output_file=html_path
        )
        
        # Convert to PDF
        print(f"[PDF] Converting to PDF...")
        if generate_pdf_direct(html_path, pdf_path):
            print(f"[PDF] Success: {pdf_path}")
            # Clean up HTML
            if os.path.exists(html_path): os.remove(html_path)
            
            return FileResponse(
                path=pdf_path, 
                media_type='application/pdf', 
                filename=f"Report_{req.accession or 'Genomic'}.pdf",
                headers={"Content-Disposition": f"attachment; filename=Report_{req.accession or 'Genomic'}.pdf"},
                background=BackgroundTask(lambda: os.remove(pdf_path) if os.path.exists(pdf_path) else None)
            )
        else:
            print(f"[PDF] Conversion failed")
            raise HTTPException(status_code=500, detail="Failed to generate PDF")
    except Exception as e:
        print(f"[PDF] Critical Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Simulation Task ---
async def run_simulation():
    while True:
        await asyncio.sleep(10)
        for pid, p in plants_db.items():
            p["vwc"] += random.uniform(-2.0, 2.0)
            p["temp"] += random.uniform(-0.5, 0.5)
            p["vwc"] = max(5.0, min(50.0, p["vwc"]))
            if p["vwc"] < 15.0:
                p["status"] = "DRY"
                now = time.time()
                last = notification_cooldowns.get(pid, 0)
                if now - last > 300:
                    msg = f"\u26a0\ufe0f ALERT: Plant {p['name']} ({pid}) is critically DRY! VWC: {p['vwc']:.1f}%"
                    send_sms_sync(msg)
                    notification_cooldowns[pid] = now
            elif p["vwc"] > 40.0:
                p["status"] = "FLOODED"
            else:
                p["status"] = "HEALTHY"

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_simulation())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
