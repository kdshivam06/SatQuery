"""Parallel DAG executor based on resource lanes."""

from __future__ import annotations

import asyncio
import logging
import time

from backend.agent.planner_schema import ExecutionPlan
from backend.agent.resource_scheduler import get_semaphore
from backend.agent.trace_logger import TraceLogger
from backend.tools.registry import TOOL_REGISTRY

logger = logging.getLogger(__name__)


async def execute_plan(
    plan: ExecutionPlan,
    context: dict,
    trace: TraceLogger,
) -> dict[str, dict]:
    """Execute tools according to the plan's parallel groups and dependencies."""

    results: dict[str, dict] = {}
    
    # Log skipped tools upfront
    for skipped in plan.skipped_tools:
        trace.log_tool(skipped.tool, status="skipped", reason=skipped.reason)

    for group_idx, group in enumerate(plan.parallel_groups):
        logger.info("Executing parallel group %s: %s", group_idx, [s.tool for s in group.steps])

        if group.can_run_parallel:
            tasks = [
                _run_step_safely(step, context, results, trace)
                for step in group.steps
            ]
            group_results = await asyncio.gather(*tasks, return_exceptions=True)
            for step, res in zip(group.steps, group_results):
                if isinstance(res, Exception):
                    logger.error("Step %s failed abruptly: %s", step.tool, res)
                    results[step.tool] = {
                        "status": "failed",
                        "error": str(res),
                        "summary": f"Unhandled exception: {res}",
                    }
                    trace.log_tool(step.tool, status="failed", reason=str(res))
                else:
                    results[step.tool] = res
        else:
            # Sequential execution for this group (e.g., validation)
            for step in group.steps:
                try:
                    res = await _run_step_safely(step, context, results, trace)
                    results[step.tool] = res
                except Exception as exc:
                    logger.error("Step %s failed abruptly: %s", step.tool, exc)
                    results[step.tool] = {
                        "status": "failed",
                        "error": str(exc),
                        "summary": f"Unhandled exception: {exc}",
                    }
                    trace.log_tool(step.tool, status="failed", reason=str(exc))

    return results


async def _run_step_safely(
    step,
    context: dict,
    prior_results: dict[str, dict],
    trace: TraceLogger,
) -> dict:
    """Execute a single tool with semaphore protection and tracing."""

    tool_instance = TOOL_REGISTRY.get(step.tool)
    if not tool_instance:
        msg = f"Tool {step.tool} not found in registry."
        logger.warning(msg)
        trace.log_tool(step.tool, status="failed", reason=msg)
        return {"status": "failed", "error": msg, "summary": msg}

    semaphore = get_semaphore(step.resource_lane)

    start_time = time.monotonic()
    run_mode = getattr(tool_instance, "run_mode", "static_function")
    
    logger.info("Acquiring %s lane for %s...", step.resource_lane, step.tool)
    try:
        async with semaphore:
            logger.info("Running %s...", step.tool)
            result = await tool_instance.run(context, step.params, prior_results)
    except Exception as exc:
        logger.exception("Error running tool %s: %s", step.tool, exc)
        result = {
            "status": "failed",
            "run_mode": run_mode,
            "resource_lane": step.resource_lane,
            "error": str(exc),
            "summary": f"Failed: {exc}",
        }

    runtime_ms = int((time.monotonic() - start_time) * 1000)

    # Standardize result
    if "status" not in result:
        result["status"] = "success"
    if "runtime_ms" not in result:
        result["runtime_ms"] = runtime_ms
    if "run_mode" not in result:
        result["run_mode"] = run_mode
    if "resource_lane" not in result:
        result["resource_lane"] = step.resource_lane

    trace.log_tool(
        step.tool,
        run_mode=result["run_mode"],
        status=result["status"],
        runtime_ms=runtime_ms,
        summary=result.get("summary", ""),
        confidence=result.get("confidence"),
        reason=result.get("reason"),
    )

    return result
