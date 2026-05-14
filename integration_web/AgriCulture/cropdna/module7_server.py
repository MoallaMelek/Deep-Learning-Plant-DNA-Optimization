"""
main.py
-------
FastAPI server for the IRA DNA Search Platform.
Exposes all Module 7 components as REST API endpoints.

Start server:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

API docs:
    http://localhost:8000/docs
"""

import os
import json
import tempfile
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────

GROQ_KEY   = os.getenv('GROQ_API_KEY') or os.getenv('GROQ_KEY')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
AGENT_MODEL= os.getenv('AGENT_MODEL', 'meta-llama/llama-4-scout-17b-16e-instruct')


# ── Request / Response models ─────────────────────────────────

class SearchRequest(BaseModel):
    query  : str
    top_k  : int  = 10
    trait  : Optional[str] = None

class RAGRequest(BaseModel):
    question : str
    query    : str
    top_k    : int  = 10
    trait    : Optional[str] = None
    gene     : Optional[str] = None

class AgentRequest(BaseModel):
    question : str

class FicheRequest(BaseModel):
    sequence  : str
    accession : Optional[str] = ''
    species   : Optional[str] = 'Triticum aestivum'
    gene      : Optional[str] = ''

class PredictRequest(BaseModel):
    sequence : str

class SearchResult(BaseModel):
    rank          : int
    accession     : str
    trait         : str
    score         : float
    score_type    : str
    gene_name     : str
    organism      : str
    description   : str
    seq_length    : int
    gc_content    : float
    publication   : str
    pmid          : str
    sparse_score  : int
    dense_dnabert : float
    dense_kmer    : float


# ── Lifespan — load all components once ──────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all components at startup — DNABERT takes ~3 seconds."""
    print('Loading IRA DNA Search Platform...')

    from search_engine import DNASearchEngine
    from input_parser  import InputParser
    from rag_engine    import RAGEngine
    from agent         import DNAAgent
    from a2a_agent     import A2ASystem

    app.state.engine = DNASearchEngine()
    app.state.parser = InputParser(app.state.engine)
    app.state.rag    = RAGEngine(
        groq_key   = GROQ_KEY,
        groq_model = GROQ_MODEL,
    )
    app.state.agent = DNAAgent(
        app.state.engine,
        app.state.rag,
        model = AGENT_MODEL,
    )
    app.state.a2a = A2ASystem(
        app.state.engine,
        app.state.rag,
        model = AGENT_MODEL,
    )

    print('All components loaded [OK]')
    yield
    print('Shutting down...')


# ── FastAPI app ───────────────────────────────────────────────

app = FastAPI(
    title       = 'IRA DNA Search Engine API',
    description = (
        'Module 7 — DNA Search Engine for the IRA AI Agriculture Platform.\n'
        'Hybrid retrieval (DNABERT-2 + k-mer + RRF) + RAG + Agentic RAG + A2A.'
    ),
    version  = '1.0.0',
    lifespan = lifespan,
)

# Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ['*'],
    allow_credentials = True,
    allow_methods     = ['*'],
    allow_headers     = ['*'],
)


# ── Helper ────────────────────────────────────────────────────

def result_to_dict(r) -> dict:
    return {
        'rank'         : r.rank,
        'accession'    : r.accession,
        'trait'        : r.trait,
        'score'        : r.score,
        'score_type'   : r.score_type,
        'gene_name'    : r.gene_name,
        'organism'     : r.organism,
        'description'  : r.description,
        'seq_length'   : r.seq_length,
        'gc_content'   : r.gc_content,
        'publication'  : r.publication,
        'pmid'         : r.pmid,
        'sparse_score' : r.sparse_score,
        'dense_dnabert': r.dense_dnabert,
        'dense_kmer'   : r.dense_kmer,
    }


# ── Endpoints ─────────────────────────────────────────────────

@app.get('/health')
def health():
    """Check if the server is running."""
    return {
        'status'  : 'ok',
        'platform': 'IRA DNA Search Engine',
        'version' : '1.0.0',
        'modules' : ['search', 'rag', 'agent', 'a2a', 'fiche', 'pdf'],
    }


@app.get('/')
def root():
    """API information."""
    return {
        'name'       : 'IRA DNA Search Engine API',
        'description': 'Module 7 — DNA Search Engine for IRA Tunisia',
        'endpoints'  : {
            'GET  /health'    : 'Server status',
            'POST /search'    : 'Hybrid sequence search (DNABERT + k-mer + RRF)',
            'POST /predict'   : 'Trait prediction (XGBoost Module 1)',
            'POST /rag'       : 'RAG answer with articles (LangChain)',
            'POST /agent'     : 'Agentic RAG with memory (LangGraph)',
            'POST /a2a'       : 'Agent-to-Agent system',
            'POST /fiche'     : 'Generate HTML genomic report',
            'POST /pdf'       : 'Generate PDF genomic report',
            'GET  /docs'      : 'Interactive API documentation',
        },
        'dataset': {
            'sequences': 4982,
            'species'  : 'Triticum aestivum',
            'traits'   : ['drought_tolerance', 'heat_tolerance', 'salt_tolerance', 'disease_resistance'],
        }
    }


@app.post('/search')
def search(req: SearchRequest, request: Request):
    """
    Search wheat sequences using hybrid retrieval.
    Accepts: DNA sequence, accession ID, gene name, or natural language query.
    Returns: top-K results with hybrid scores (sparse + DNABERT + k-mer).
    """
    try:
        engine = request.app.state.engine
        parser = request.app.state.parser

        results    = parser.parse_and_search(req.query, top_k=req.top_k)
        prediction = engine._last_prediction or {}

        if req.trait:
            tf      = req.trait.lower().replace(' ', '_')
            results = [r for r in results if tf in r.trait.lower()]

        return {
            'query'     : req.query,
            'count'     : len(results),
            'prediction': prediction,
            'results'   : [result_to_dict(r) for r in results],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/predict')
def predict_trait(req: PredictRequest, request: Request):
    """
    Predict stress trait from a raw DNA sequence using XGBoost (Module 1).
    Returns: trait class + confidence + probabilities for all 4 classes.
    """
    try:
        engine = request.app.state.engine
        pred   = engine.predict_trait(req.sequence)
        return {
            'sequence_length': len(req.sequence),
            'predicted_trait': pred['trait'],
            'confidence'     : pred['confidence'],
            'probabilities'  : pred['probabilities'],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/rag')
def rag_answer(req: RAGRequest, request: Request):
    """
    RAG answer: search sequences + fetch Europe PMC articles + LLM synthesis.
    Returns: LLM answer with citations + articles list.
    """
    try:
        engine  = request.app.state.engine
        parser  = request.app.state.parser
        rag     = request.app.state.rag

        results = parser.parse_and_search(req.query, top_k=req.top_k)
        pred    = engine._last_prediction
        rag._last_xgb_prediction = pred

        answer  = rag.answer(
            req.question,
            results,
            trait = req.trait or '',
            gene  = req.gene  or '',
        )

        articles = [
            {
                'title'  : a.title,
                'authors': a.authors,
                'year'   : a.year,
                'journal': a.journal,
                'pmid'   : a.pmid,
                'url'    : a.pubmed_url(),
                'abstract': a.abstract[:200] if a.abstract else '',
            }
            for a in answer.articles[:5]
        ]

        return {
            'question'  : req.question,
            'answer'    : answer.answer,
            'trait'     : answer.trait,
            'gene'      : answer.gene,
            'model'     : answer.model_used,
            'articles'  : articles,
            'sequences' : [result_to_dict(r) for r in results[:5]],
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/agent')
def agent_answer(req: AgentRequest, request: Request):
    """
    Agentic RAG: LangGraph ReAct agent with JSON memory.
    Agent decides which tools to call and how many times.
    Returns: synthesized answer + tools used.
    """
    try:
        agent  = request.app.state.agent
        answer = agent.run(req.question)

        return {
            'question'  : req.question,
            'answer'    : answer,
            'memory'    : len(agent.memory),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/a2a')
def a2a_answer(req: AgentRequest, request: Request):
    """
    Agent-to-Agent system: Coordinator dynamically calls DNA/Science/Report agents.
    Returns: answer + which agents were called.
    """
    try:
        a2a    = request.app.state.a2a
        answer = a2a.run(req.question)

        return {
            'question'     : req.question,
            'answer'       : answer,
            'agents_called': a2a.store_called,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/fiche', response_class=HTMLResponse)
def generate_fiche(req: FicheRequest, request: Request):
    """
    Generate complete HTML genomic report (fiche).
    Includes: CGR visualization, iNaturalist photo, trait scores,
    RAG description, articles, colorized sequence.
    Returns: HTML string.
    """
    try:
        from fiche_generator import generate_fiche as _gen

        engine = request.app.state.engine
        rag    = request.app.state.rag

        pred = engine.predict_trait(req.sequence)
        engine._last_xgb_prediction = pred

        html = _gen(
            engine      = engine,
            rag         = rag,
            sequence    = req.sequence,
            accession   = req.accession,
            species     = req.species,
            gene        = req.gene,
            output_file = None,
        )
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/pdf')
def generate_pdf_report(req: FicheRequest, request: Request):
    """
    Generate PDF genomic report.
    Generates HTML fiche then converts to PDF using pdfkit.
    Returns: PDF file download.
    """
    try:
        from fiche_generator import generate_fiche as _gen
        from pdf_generator   import generate_pdf

        engine = request.app.state.engine
        rag    = request.app.state.rag

        pred = engine.predict_trait(req.sequence)
        engine._last_xgb_prediction = pred

        # Generate HTML to temp file
        tmp_html = f'tmp_fiche_{req.accession or "seq"}.html'
        tmp_pdf  = f'tmp_fiche_{req.accession or "seq"}.pdf'

        _gen(
            engine      = engine,
            rag         = rag,
            sequence    = req.sequence,
            accession   = req.accession,
            species     = req.species,
            gene        = req.gene,
            output_file = tmp_html,
        )

        result = generate_pdf(tmp_html, tmp_pdf)
        if not result:
            raise HTTPException(status_code=500, detail='PDF generation failed')

        return FileResponse(
            path             = tmp_pdf,
            media_type       = 'application/pdf',
            filename         = f'fiche_{req.accession or "sequence"}.pdf',
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete('/agent/memory')
def clear_agent_memory(request: Request):
    """Clear agent conversation memory."""
    request.app.state.agent.clear_memory()
    return {'status': 'ok', 'message': 'Agent memory cleared'}


@app.get('/agent/memory')
def get_agent_memory(request: Request):
    """Get agent conversation history."""
    agent  = request.app.state.agent
    return {
        'count' : len(agent.memory),
        'turns' : [
            {
                'timestamp' : t['timestamp'],
                'query'     : t['query'][:100],
                'tools_used': t.get('tools_used', []),
            }
            for t in agent.memory[-10:]
        ]
    }


@app.get('/stats')
def get_stats(request: Request):
    """Get database statistics."""
    engine = request.app.state.engine
    return {
        'sequences'    : len(engine.df),
        'dnabert_index': engine.index_dnabert.ntotal,
        'kmer_index'   : engine.index_kmer.ntotal,
        'kmer_vocab'   : len(engine.kmer_inv),
        'traits'       : engine.df['trait'].value_counts().to_dict(),
        'xgboost'      : engine.xgb_model is not None,
    }
