"""FastAPI app for the SatQuery AI backend."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        alt = Path(__file__).parent.parent / ".env"
        if alt.exists():
            load_dotenv(alt, override=True)
except ImportError:
    pass

from backend.api.routes_analyze import router as analyze_router
from backend.api.routes_outputs import router as outputs_router
from backend.api.routes_runs import router as runs_router


app = FastAPI(
    title="SatQuery AI",
    description="Agentic remote-sensing VLM backend with ingestion, routing, tools, traces, and reports.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(runs_router)
app.include_router(outputs_router)

# ── Static file serving for frontend ──────────────────────
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

# ── Serve run artifacts ───────────────────────────────────
runs_dir = Path(os.getenv("SATQUERY_RUN_DIR", "runs/api"))
runs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(runs_dir)), name="run_files")


@app.get("/health")
async def health():
    from backend.tools.registry import get_enabled_tools
    enabled = list(get_enabled_tools().keys())
    # Remove legacy aliases from the count
    legacy = {"metadata_summary", "ndwi_water", "ndbi_builtup", "sar_water", "sar_builtup", "change_map"}
    canonical = [t for t in enabled if t not in legacy]
    return {
        "status": "ok",
        "service": "satquery-ai",
        "version": "0.2.0",
        "tools_enabled": len(canonical),
        "router_mode": os.getenv("ROUTER_MODE", "fallback"),
    }
