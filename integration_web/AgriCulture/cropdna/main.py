from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from module8_client import router as module8_router
from module7_client import router as module7_router   # ← AJOUTÉ
from routers.iot import router as iot_router
from database import init_db
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse



app = FastAPI(
    title="CropDNA AI Platform",
    description="IRA — Plant Genomics & Smart Agriculture",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()
    print("CropDNA AI Platform started")
    print("  Module 8  : /module8/")
    print("  Module 7  : /module7/")    # ← AJOUTÉ
    print("  IoT       : /api/iot/")
    print("  Docs      : http://127.0.0.1:8000/docs")


# ── Modules ────────────────────────────────────────────────
app.include_router(module7_router)      # ← AJOUTÉ
app.include_router(module8_router)
app.include_router(iot_router, prefix="/api/iot")
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/test")
def test_page():
    return FileResponse("test.html")

# ── Root ───────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "platform": "CropDNA AI Platform",
        "version":  "1.0.0",
        "modules": {
            "module8": "/module8/health",
            "iot":     "/api/iot/plants",
            "docs":    "/docs"
        }
    }
