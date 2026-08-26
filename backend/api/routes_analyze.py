"""Analyze endpoints for upload, local paths, and benv1_14k samples."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from backend.agent.controller import run_analysis
from backend.api.schemas import AnalyzePathsRequest, AnalyzeResponse, Benv1AnalyzeRequest
from backend.geospatial.benv1_selector import select_benv1_pair
from backend.storage.file_store import save_upload_file
from backend.storage.run_store import RunStore


router = APIRouter(prefix="/api", tags=["analyze"])
store = RunStore()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_uploads(
    background_tasks: BackgroundTasks,
    query: str = Form(...),
    mode: str = Form("auto"),
    files: list[UploadFile] = File(...),
):
    """Analyze uploaded image files."""

    state = store.create_run(query, mode=mode)
    run_dir = store.run_dir(state["run_id"])
    upload_dir = run_dir / "uploads"
    saved_paths = []
    for uploaded in files:
        saved_paths.append(save_upload_file(uploaded.file, uploaded.filename or "upload.bin", upload_dir))
    background_tasks.add_task(run_analysis, state["run_id"], query, saved_paths, run_dir, mode=mode)
    return AnalyzeResponse(run_id=state["run_id"], status="queued")


@router.post("/analyze/paths", response_model=AnalyzeResponse)
async def analyze_paths(payload: AnalyzePathsRequest, background_tasks: BackgroundTasks):
    """Analyze local paths. Useful for local dataset prototype runs."""

    if not payload.paths:
        raise HTTPException(status_code=400, detail="At least one input path is required.")
    missing = [path for path in payload.paths if not Path(path).exists()]
    if missing:
        raise HTTPException(status_code=400, detail={"missing_paths": missing})

    state = store.create_run(payload.query, mode=payload.mode)
    run_dir = store.run_dir(state["run_id"])
    background_tasks.add_task(
        run_analysis,
        state["run_id"],
        payload.query,
        payload.paths,
        run_dir,
        mode=payload.mode,
        generate_pdf=payload.generate_pdf,
        generate_model_inputs=payload.generate_model_inputs,
    )
    return AnalyzeResponse(run_id=state["run_id"], status="queued")


@router.post("/analyze/benv1", response_model=AnalyzeResponse)
async def analyze_benv1(payload: Benv1AnalyzeRequest, background_tasks: BackgroundTasks):
    """Select a real benv1_14k pair and analyze it."""

    try:
        pair = select_benv1_pair(
            payload.dataset_root,
            index=payload.index,
            s1_id=payload.s1_id,
            s2_id=payload.s2_id,
        )
    except (FileNotFoundError, LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not pair.exists:
        raise HTTPException(status_code=400, detail=pair.to_dict())

    state = store.create_run(payload.query, mode=payload.mode)
    run_dir = store.run_dir(state["run_id"])
    background_tasks.add_task(
        run_analysis,
        state["run_id"],
        payload.query,
        [pair.s1_path, pair.s2_path],
        run_dir,
        mode=payload.mode,
        generate_pdf=payload.generate_pdf,
        generate_model_inputs=payload.generate_model_inputs,
        dataset_pair=pair.to_dict(),
    )
    return AnalyzeResponse(run_id=state["run_id"], status="queued")
