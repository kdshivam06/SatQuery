"""FastAPI app for the SatQuery AI prototype backend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_analyze import router as analyze_router
from backend.api.routes_outputs import router as outputs_router
from backend.api.routes_runs import router as runs_router


app = FastAPI(
    title="SatQuery AI Prototype",
    description="Agentic remote-sensing VLM backend with ingestion, routing, tools, traces, and reports.",
    version="0.1.0",
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


@app.get("/health")
async def health():
    return {"status": "ok", "service": "satquery-ai"}
