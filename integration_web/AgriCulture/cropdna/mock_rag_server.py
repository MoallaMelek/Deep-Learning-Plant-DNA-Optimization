from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import time

app = FastAPI(title="AgriCulture RAG Mock Server (Windows Compatibility)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    trait: Optional[str] = None

class RAGRequest(BaseModel):
    question: str
    query: str
    top_k: int = 10

class AgentRequest(BaseModel):
    question: str

class FicheRequest(BaseModel):
    sequence: str
    accession: Optional[str] = ''

@app.get("/health")
def health():
    return {"status": "ok", "platform": "IRA DNA Search Engine (MOCK)", "version": "1.0.0"}

@app.get("/")
def root():
    return {"name": "IRA DNA Search Engine API (MOCK)", "status": "Running in compatibility mode"}

@app.post("/search")
def search(req: SearchRequest):
    return {
        "query": req.query,
        "count": 1,
        "prediction": {"trait": "drought_tolerance", "confidence": 0.85},
        "results": [
            {
                "rank": 1,
                "accession": "MOCK_AC_001",
                "trait": "drought_tolerance",
                "score": 0.99,
                "score_type": "hybrid",
                "gene_name": "WHEAT_DR_1",
                "organism": "Triticum aestivum",
                "description": "Mock sequence for drought tolerance testing.",
                "seq_length": 450,
                "gc_content": 0.48,
                "publication": "Mock Agriculture Journal 2026",
                "pmid": "12345678",
                "sparse_score": 10,
                "dense_dnabert": 0.95,
                "dense_kmer": 0.92
            }
        ]
    }

@app.post("/rag")
def rag_answer(req: RAGRequest):
    return {
        "question": req.question,
        "answer": "This is a mock RAG answer. On Windows, the DNABERT-2 model is disabled to avoid Triton dependency issues. However, the system is responding correctly to your query.",
        "trait": "drought_tolerance",
        "articles": [{"title": "Genomics of Wheat", "authors": "AgriAI Team", "year": 2026, "url": "#"}],
        "sequences": []
    }

@app.post("/agent")
@app.post("/a2a")
def agent_mock(req: AgentRequest):
    return {
        "question": req.question,
        "answer": "The AgriAgent (Mock) is operational. I can process your genomic queries using synthetic data providers.",
        "agents_called": ["DNA_Agent", "Mock_Provider"]
    }

@app.post("/fiche", response_class=HTMLResponse)
def generate_fiche(req: FicheRequest):
    return "<html><body><h1>Genomic Fiche (Mock)</h1><p>Sequence: " + req.sequence[:50] + "...</p></body></html>"

@app.get("/stats")
def get_stats():
    return {"sequences": 4982, "status": "MOCK_MODE"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5007)
