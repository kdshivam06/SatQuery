"""Parallel-ish execution of planned tools with trace-friendly results."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from time import perf_counter

from backend.tools.registry import TOOL_REGISTRY


RESOURCE_LIMITS = {
    "cpu": asyncio.Semaphore(8),
    "gpu_0_light": asyncio.Semaphore(2),
    "gpu_0_heavy": asyncio.Semaphore(1),
}


async def execute_plan(plan: dict, context: dict) -> dict[str, dict]:
    """Execute plan steps as soon as dependencies are available."""

    results: dict[str, dict] = {}
    pending = {step["id"]: step for step in plan.get("steps", [])}

    while pending:
        ready = [
            step
            for step in pending.values()
            if all(dep in results for dep in step.get("depends_on", []))
        ]
        if not ready:
            raise RuntimeError(f"Plan has unresolved dependencies: {list(pending)}")

        completed = await asyncio.gather(
            *[_run_step(step, context, results) for step in ready],
            return_exceptions=True,
        )
        for step, result in zip(ready, completed):
            if isinstance(result, Exception):
                results[step["id"]] = _failed_result(step, result)
            else:
                results[step["id"]] = result
            del pending[step["id"]]

    return results


async def _run_step(step: dict, context: dict, results: dict[str, dict]) -> dict:
    tool = TOOL_REGISTRY[step["tool"]]
    resource = step.get("resource", tool.resource)
    semaphore = RESOURCE_LIMITS.get(resource, RESOURCE_LIMITS["cpu"])
    started = _now()
    start = perf_counter()

    async with semaphore:
        output = await tool.run(context, step.get("params", {}), results)

    runtime_ms = int((perf_counter() - start) * 1000)
    return {
        "step_id": step["id"],
        "tool_name": tool.name,
        "status": output.get("status", "success"),
        "started_at": started,
        "finished_at": _now(),
        "runtime_ms": runtime_ms,
        "resource": resource,
        "parameters": step.get("params", {}),
        "outputs": output.get("outputs", {}),
        "confidence": output.get("confidence"),
        "summary": output.get("summary", ""),
        "artifacts": output.get("artifacts", []),
    }


def _failed_result(step: dict, exc: Exception) -> dict:
    return {
        "step_id": step["id"],
        "tool_name": step.get("tool"),
        "status": "failed",
        "started_at": _now(),
        "finished_at": _now(),
        "runtime_ms": 0,
        "resource": step.get("resource", "cpu"),
        "parameters": step.get("params", {}),
        "outputs": {"error": str(exc)},
        "confidence": 0.0,
        "summary": f"Tool failed: {exc}",
        "artifacts": [],
    }


def _now() -> str:
    return datetime.now(UTC).isoformat()
