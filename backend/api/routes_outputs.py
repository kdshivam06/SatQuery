"""Artifact serving endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.storage.file_store import resolve_run_file
from backend.storage.run_store import RunStore


router = APIRouter(prefix="/api", tags=["outputs"])
store = RunStore()


@router.get("/runs/{run_id}/outputs/{relative_path:path}")
async def get_output(run_id: str, relative_path: str):
    try:
        path = resolve_run_file(store.run_dir(run_id), relative_path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path)


@router.get("/runs/{run_id}/report")
async def get_report(run_id: str):
    try:
        state = store.get_state(run_id)
        manifest = state.get("manifest") or {}
        report_path = manifest.get("pdf_report")
        if not report_path:
            raise FileNotFoundError("No PDF report for this run.")
        path = resolve_run_file(store.run_dir(run_id), _relative_to_run(store.run_dir(run_id), report_path))
    except (KeyError, FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type="application/pdf")


def _relative_to_run(run_dir, path: str) -> str:
    candidate = str(path).replace("\\", "/")
    run_prefix = str(run_dir).replace("\\", "/")
    if candidate.startswith(run_prefix):
        return candidate[len(run_prefix) :].lstrip("/")
    parts = candidate.split("/")
    if "ingestion" in parts:
        return "/".join(parts[parts.index("ingestion") :])
    if "reports" in parts:
        return "/".join(parts[parts.index("reports") :])
    return candidate
