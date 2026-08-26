"""Structured trace logger for audit/tool-calling logs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class TraceLogger:
    """Accumulates structured trace events for a single run."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.events: list[dict[str, Any]] = []
        self.tool_logs: list[dict[str, Any]] = []

    def log_event(self, event: str, **data):
        self.events.append({"timestamp": _now(), "event": event, **data})

    def log_tool(
        self,
        tool: str,
        *,
        run_mode: str = "",
        status: str = "",
        runtime_ms: int = 0,
        summary: str = "",
        confidence: float | None = None,
        reason: str | None = None,
    ):
        entry = {
            "tool": tool,
            "run_mode": run_mode,
            "status": status,
            "runtime_ms": runtime_ms,
            "summary": summary,
            "confidence": confidence,
        }
        if reason:
            entry["reason"] = reason
        self.tool_logs.append(entry)

    def build_trace(
        self,
        *,
        workflow: str = "",
        input_summary: dict | None = None,
        parallel_groups: list[list[str]] | None = None,
        final_confidence: float | None = None,
    ) -> dict:
        return {
            "run_id": self.run_id,
            "workflow": workflow,
            "input_summary": input_summary or {},
            "parallel_groups": parallel_groups or [],
            "tool_logs": self.tool_logs,
            "final_confidence": final_confidence,
            "events": self.events,
        }

    def save(self, run_dir: str | Path):
        """Write the trace to a JSON file in the run directory."""
        out = Path(run_dir) / "trace.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.build_trace(), indent=2, default=str), encoding="utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat()
