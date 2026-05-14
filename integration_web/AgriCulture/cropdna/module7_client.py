"""
module7_client.py
-----------------
Bridge between the CropDNA gateway and Module 7 DNA Search Engine.
Module 7 runs on port 5000. This router proxies requests to it.
"""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/module7", tags=["Module 7 - DNA Search Engine"])

MODULE7_URL = "http://127.0.0.1:5000"
TIMEOUT     = 60.0


# ── Request models ────────────────────────────────────────────

class SearchRequest(BaseModel):
    query  : str
    top_k  : int = 10
    trait  : Optional[str] = None

class RAGRequest(BaseModel):
    question : str
    query    : str
    top_k    : int = 10
    trait    : Optional[str] = None
    gene     : Optional[str] = None

class AgentRequest(BaseModel):
    question : str

class PredictRequest(BaseModel):
    sequence : str

class FicheRequest(BaseModel):
    sequence  : str
    accession : Optional[str] = ''
    species   : Optional[str] = 'Triticum aestivum'
    gene      : Optional[str] = ''


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/health")
async def health():
    """Check Module 7 status."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{MODULE7_URL}/health")
            return r.json()
    except:
        raise HTTPException(503, "Module 7 offline")


@router.get("/stats")
async def stats():
    """Get Module 7 database statistics."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{MODULE7_URL}/stats")
        return r.json()


@router.post("/search")
async def search(req: SearchRequest):
    """Hybrid DNA sequence search (DNABERT + k-mer + RRF)."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{MODULE7_URL}/search", json=req.dict())
        return r.json()


@router.post("/predict")
async def predict(req: PredictRequest):
    """Trait prediction via XGBoost Module 1."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{MODULE7_URL}/predict", json=req.dict())
        return r.json()


@router.post("/rag")
async def rag(req: RAGRequest):
    """RAG answer with Europe PMC articles."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{MODULE7_URL}/rag", json=req.dict())
        return r.json()


@router.post("/agent")
async def agent(req: AgentRequest):
    """LangGraph ReAct agent with memory."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{MODULE7_URL}/agent", json=req.dict())
        return r.json()


@router.post("/a2a")
async def a2a(req: AgentRequest):
    """Agent-to-Agent dynamic system."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{MODULE7_URL}/a2a", json=req.dict())
        return r.json()


@router.post("/fiche")
async def fiche(req: FicheRequest):
    """Generate HTML genomic report."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{MODULE7_URL}/fiche", json=req.dict())
        return r.text


@router.get("/agent/memory")
async def agent_memory():
    """Get agent conversation history."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{MODULE7_URL}/agent/memory")
        return r.json()


@router.delete("/agent/memory")
async def clear_memory():
    """Clear agent memory."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.delete(f"{MODULE7_URL}/agent/memory")
        return r.json()
    
@router.post("/pdf")
async def pdf(req: FicheRequest):
    """Generate PDF genomic report."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{MODULE7_URL}/pdf", json=req.dict())
        return Response(
            content    = r.content,
            media_type = "application/pdf",
            headers    = {"Content-Disposition": "attachment; filename=fiche.pdf"}
        )