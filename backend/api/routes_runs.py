"""Run status, trace, and report endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.storage.run_store import RunStore


router = APIRouter(prefix="/api", tags=["runs"])
store = RunStore()


@router.get("/runs")
async def list_runs(limit: int = 25):
    return {"runs": store.list_runs(limit=limit)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    try:
        return store.get_state(run_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/trace")
async def get_trace(run_id: str):
    try:
        state = store.get_state(run_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"run_id": run_id, "trace": state.get("trace", {})}


@router.get("/runs/{run_id}/report")
async def get_report(run_id: str, format: str = "html"):
    """Download the run report (html or json)."""
    try:
        state = store.get_state(run_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    report = state.get("report", {})
    if not report:
        raise HTTPException(status_code=404, detail="No report generated for this run.")

    if format == "json":
        path = report.get("json")
        media = "application/json"
    else:
        path = report.get("html")
        media = "text/html"

    if not path:
        raise HTTPException(status_code=404, detail=f"No {format} report available.")

    from pathlib import Path
    if not Path(path).exists():
        raise HTTPException(status_code=404, detail=f"Report file not found: {path}")

    return FileResponse(path, media_type=media)
