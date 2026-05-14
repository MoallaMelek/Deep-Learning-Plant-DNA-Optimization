from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router

app = FastAPI(
    title="ODM Wheat API",
    description="Oligonucleotide-Directed Mutagenesis pipeline for Triticum aestivum — DNABERT Fine-Tuning v4",
    version="4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
