"""Top-level analysis controller used by the API."""

from __future__ import annotations

import asyncio
from pathlib import Path

from backend.agent.executor import execute_plan
from backend.agent.fusion import fuse_outputs
from backend.agent.intent_classifier import classify_intent
from backend.agent.planner import create_execution_plan
from backend.geospatial.pipeline import ingest_pair
from backend.storage.run_store import RunStore


store = RunStore()


def run_analysis(
    run_id: str,
    query: str,
    paths: list[str],
    run_dir: str | Path,
    *,
    mode: str = "auto",
    generate_pdf: bool = True,
    generate_model_inputs: bool = True,
    dataset_pair: dict | None = None,
) -> None:
    """Run ingestion, planning, tools, fusion, and trace updates."""

    try:
        store.update(run_id, status="running", current_step="ingestion", progress=0.1)
        store.append_trace(run_id, {"event": "ingestion_started", "paths": paths})

        ingest_dir = Path(run_dir) / "ingestion"
        manifest = ingest_pair(
            paths,
            ingest_dir,
            generate_pdf=generate_pdf,
            generate_model_inputs=generate_model_inputs,
        )
        if dataset_pair:
            manifest["dataset_pair"] = dataset_pair

        store.update(run_id, manifest=manifest, current_step="planning", progress=0.35)
        store.append_trace(run_id, {"event": "ingestion_completed", "manifest_path": manifest.get("manifest_path")})

        intent = classify_intent(query, manifest, mode=mode)
        plan = create_execution_plan(intent, manifest)
        context = {
            "run_id": run_id,
            "query": query,
            "run_dir": str(run_dir),
            "manifest": manifest,
            "intent": intent,
        }
        store.append_trace(run_id, {"event": "plan_created", "intent": intent, "plan": plan})

        store.update(run_id, current_step="tool_execution", progress=0.55)
        results = asyncio.run(execute_plan(plan, context))
        store.append_trace(run_id, {"event": "tools_completed", "results": results})

        store.update(run_id, current_step="fusion", progress=0.85)
        final = fuse_outputs(query, intent, manifest, plan, results)
        state = store.get_state(run_id)
        state.update(
            {
                "status": "completed",
                "current_step": None,
                "progress": 1.0,
                "answer": final["answer"],
                "confidence": final["confidence"],
                "visual_outputs": final["visual_outputs"],
                "artifacts": _collect_artifacts(manifest, results),
                "tool_results": results,
                "final": final,
            }
        )
        state.setdefault("trace", []).append({"event": "fusion_completed", **final["trace"]})
        store.save_state(run_id, state)
    except Exception as exc:
        store.update(
            run_id,
            status="failed",
            current_step=None,
            error=str(exc),
            progress=1.0,
        )
        store.append_trace(run_id, {"event": "analysis_failed", "error": str(exc)})


def _collect_artifacts(manifest: dict, results: dict[str, dict]) -> list[dict]:
    artifacts: list[dict] = []
    for asset in manifest.get("assets", []):
        preview = asset.get("preview")
        if preview:
            artifacts.append({"type": "preview", "path": preview["preview_path"], "label": asset["metadata"]["filename"]})
    if manifest.get("pdf_report"):
        artifacts.append({"type": "report", "path": manifest["pdf_report"], "label": "PDF report"})
    for result in results.values():
        artifacts.extend(result.get("artifacts", []))
    return artifacts
