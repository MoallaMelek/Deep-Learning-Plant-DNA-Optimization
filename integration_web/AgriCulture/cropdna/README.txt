 
CropDNA AI Platform — Installation et lancement
================================================

PREREQUIS
    Python 3.10
    pip install -r requirements.txt

LANCEMENT
    Option 1 — Double-cliquer sur start.bat
    
    Option 2 — Manuel :
        Terminal 1: uvicorn module7_server:app --port 5007
        Terminal 2: uvicorn main:app --port 8000 --reload

ACCES
    Docs    : http://127.0.0.1:8000/docs
    Gateway : http://127.0.0.1:8000
    Module7 : http://127.0.0.1:5007

ENDPOINTS PRINCIPAUX
    POST /module7/search   — Recherche sequences ADN
    POST /module7/rag      — RAG + articles scientifiques
    POST /module7/agent    — Agent LangGraph
    POST /module7/a2a      — Agent-to-Agent
    POST /module7/fiche    — Rapport HTML genomique
    POST /module7/pdf      — Rapport PDF
    POST /module8/analyze  — Sorghum OCR chromatine
    GET  /api/iot/plants   — Sound of Plant CNN

CLE GROQ (deja configuree dans le code)
    Modele RAG   : llama-3.1-8b-instant
    Modele Agent : meta-llama/llama-4-scout-17b-16e-instruct

DONNEES REQUISES (dans le meme dossier)
    faiss_dnabert.index
    faiss_kmer.index
    master_index.parquet
    best_xgboost.pkl
    label_encoder.pkl
    kmer_inverted_index.pkl
    seq_id_to_accession.pkl
    wheat_enriched.csv

CONTACT
    Module 7 DNA Search Engine — Ela, ESPRIT 2026
    IRA Medenine, Tunisie