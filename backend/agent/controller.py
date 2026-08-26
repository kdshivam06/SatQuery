"""Main controller – orchestrates context → router → executor → fusion pipeline."""

from __future__ import annotations

import logging
from pathlib import Path

from backend.agent.context_builder import build_router_input
from backend.agent.executor import execute_plan
from backend.agent.fusion import fuse_results
from backend.agent.router_llm import route
from backend.agent.trace_logger import TraceLogger

logger = logging.getLogger(__name__)


async def run_analysis(
    run_id: str,
    run_dir: str,
    query: str,
    manifest: dict,
    *,
    mode: str = "auto",
    update_state=None,
) -> dict:
    """End-to-end analysis pipeline.

    1. Build router input from manifest
    2. Route (LLM or fallback) → ExecutionPlan
    3. Execute plan (parallel DAG with resource lanes)
    4. Fuse results → answer, confidence, evidence, visuals
    5. Write trace and return final result
    """

    trace = TraceLogger(run_id)
    trace.log_event("run_started", query=query, mode=mode)

    # ── 1. Build context ──────────────────────────────────
    router_input = build_router_input(query, manifest, mode=mode)
    trace.log_event("router_input_built", configuration=router_input["input_summary"]["configuration"])

    if update_state:
        await _safe_update(update_state, run_id, {"status": "routing", "current_step": "routing"})

    # ── 2. Route ──────────────────────────────────────────
    plan = route(router_input)
    trace.log_event(
        "plan_generated",
        workflow=plan.workflow,
        groups=[g.group_id for g in plan.parallel_groups],
        total_steps=len(plan.all_steps()),
        skipped=len(plan.skipped_tools),
    )

    if update_state:
        await _safe_update(update_state, run_id, {
            "status": "executing",
            "current_step": f"executing {plan.workflow}",
            "progress": 0.1,
        })

    # ── 3. Execute ────────────────────────────────────────
    context = {
        "run_id": run_id,
        "run_dir": run_dir,
        "query": query,
        "manifest": manifest,
        "mode": mode,
    }

    tool_results = await execute_plan(plan, context, trace)
    trace.log_event("execution_complete", tools_run=len(tool_results))

    if update_state:
        await _safe_update(update_state, run_id, {
            "status": "fusing",
            "current_step": "synthesising answer",
            "progress": 0.8,
        })

    # ── 4. Fuse ───────────────────────────────────────────
    fused = fuse_results(query, tool_results, workflow=plan.workflow)
    trace.log_event("fusion_complete", confidence=fused["confidence"])

    # ── 5. Build final result ─────────────────────────────
    trace_data = trace.build_trace(
        workflow=plan.workflow,
        input_summary=router_input["input_summary"],
        parallel_groups=plan.flat_parallel_groups(),
        final_confidence=fused["confidence"],
    )
    trace.save(run_dir)

    final = {
        "run_id": run_id,
        "status": "completed",
        "query": query,
        "workflow": plan.workflow,
        "answer": fused["answer"],
        "confidence": fused["confidence"],
        "evidence": fused["evidence"],
        "visual_outputs": fused["visual_outputs"],
        "trace": trace_data,
        "tool_results": {
            name: {k: v for k, v in res.items() if k != "artifacts"}
            for name, res in tool_results.items()
        },
    }

    if update_state:
        await _safe_update(update_state, run_id, final)

    return final


async def _safe_update(update_fn, run_id: str, data: dict):
    """Call the state update function safely, handling sync/async variants."""
    try:
        import asyncio
        result = update_fn(run_id, data)
        if asyncio.iscoroutine(result):
            await result
    except Exception as exc:
        logger.warning("State update failed: %s", exc)
