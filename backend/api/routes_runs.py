"""Run status and trace endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

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
    return {"run_id": run_id, "trace": state.get("trace", [])}
