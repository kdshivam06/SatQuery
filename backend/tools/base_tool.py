"""Abstract base class for all SatQuery tools and standardised result type."""

from __future__ import annotations

import abc
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class ToolResult:
    """Canonical return value from every tool execution."""

    tool_name: str
    status: str  # success | skipped | failed
    run_mode: str = "static_function"
    resource_lane: str = "cpu"
    started_at: str = ""
    finished_at: str = ""
    runtime_ms: int = 0
    inputs: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None
    summary: str = ""
    artifacts: list[dict[str, str]] = field(default_factory=list)
    error: str | None = None
    reason: str | None = None  # used when status == "skipped"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def skipped_result(
    tool_name: str,
    reason: str,
    *,
    run_mode: str = "static_function",
    resource_lane: str = "cpu",
) -> dict:
    """Convenience builder for a canonical skipped-tool output dict."""
    return {
        "status": "skipped",
        "run_mode": run_mode,
        "resource_lane": resource_lane,
        "outputs": {"reason": reason},
        "confidence": None,
        "summary": f"{tool_name} skipped: {reason}",
        "artifacts": [],
        "reason": reason,
    }


class BaseTool(abc.ABC):
    """Every SatQuery tool must subclass this."""

    # ── Metadata (set by subclass) ────────────────────────
    name: str = ""
    purpose: str = ""
    tool_type: str = "static_function"  # static_function | custom_model | pretrained_model
    run_mode: str = "static_function"  # static_function | local_downloaded_model | remote_hf_api | optional_disabled
    resource_lane: str = "cpu"  # cpu | local_gpu_light | remote_api
    input_modalities: list[str] = []
    output_types: list[str] = []
    enabled: bool = True
    fallback_behavior: str = "skip_with_trace"

    # legacy compat
    @property
    def resource(self) -> str:
        return self.resource_lane

    @property
    def description(self) -> str:
        return self.purpose

    # ── Execution ─────────────────────────────────────────

    @abc.abstractmethod
    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        """Execute the tool and return a canonical result dict.

        Keys expected in the returned dict:
            status, outputs, confidence, summary, artifacts
        Optional:
            run_mode, resource_lane, reason (for skipped)
        """

    # ── Registry summary (sent to the LLM router) ────────

    def registry_entry(self) -> dict:
        return {
            "name": self.name,
            "type": self.tool_type,
            "run_mode": self.run_mode,
            "resource_lane": self.resource_lane,
            "purpose": self.purpose,
            "input_modalities": list(self.input_modalities),
            "outputs": list(self.output_types),
            "enabled": self.enabled,
        }


def _now() -> str:
    return datetime.now(UTC).isoformat()
