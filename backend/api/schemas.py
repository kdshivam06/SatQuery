"""Pydantic schemas for SatQuery API endpoints and router I/O."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── API Request / Response ────────────────────────────────


class AnalyzePathsRequest(BaseModel):
    query: str = Field(..., min_length=1)
    paths: list[str] = Field(default_factory=list)
    mode: str = "auto"
    generate_pdf: bool = True
    generate_model_inputs: bool = True


class AnalyzeResponse(BaseModel):
    run_id: str
    status: str


class Benv1AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1)
    dataset_root: str = "data/raw/real_samples/benv1_14k"
    index: int | None = None
    s1_id: str | None = None
    s2_id: str | None = None
    mode: str = "auto"
    generate_pdf: bool = True
    generate_model_inputs: bool = True


# ── Tool Result Schema ────────────────────────────────────


class ToolArtifact(BaseModel):
    type: str
    path: str
    label: str = ""


class ToolResultSchema(BaseModel):
    tool_name: str
    status: str  # success, skipped, failed
    run_mode: str = "static_function"
    resource_lane: str = "cpu"
    started_at: str = ""
    finished_at: str = ""
    runtime_ms: int = 0
    inputs: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None
    summary: str = ""
    artifacts: list[ToolArtifact] = Field(default_factory=list)
    error: str | None = None
    reason: str | None = None  # for skipped tools


# ── Router I/O Schemas ────────────────────────────────────


class InputSummary(BaseModel):
    image_count: int = 0
    formats: list[str] = Field(default_factory=list)
    modalities: list[str] = Field(default_factory=list)
    configuration: str = "unknown"  # single, cross_modal_pair, temporal_pair
    alignment_status: str = "unknown"
    available_bands: dict[str, list[str]] = Field(default_factory=dict)


class ResourceState(BaseModel):
    cpu_available: bool = True
    local_gpu_light_available: bool = True
    remote_api_available: bool = True


class RouterInput(BaseModel):
    query: str
    input_summary: InputSummary
    available_tools: list[str] = Field(default_factory=list)
    resource_state: ResourceState = Field(default_factory=ResourceState)


class ExecutionStep(BaseModel):
    step_id: str
    tool: str
    depends_on: list[str] = Field(default_factory=list)
    resource_lane: str = "cpu"
    params: dict[str, Any] = Field(default_factory=dict)


class ParallelGroup(BaseModel):
    group_id: str
    can_run_parallel: bool = True
    steps: list[ExecutionStep] = Field(default_factory=list)


class SkippedTool(BaseModel):
    tool: str
    reason: str


class ExecutionPlan(BaseModel):
    workflow: str
    intent: str = ""
    requires_visual_output: bool = True
    parallel_groups: list[ParallelGroup] = Field(default_factory=list)
    skipped_tools: list[SkippedTool] = Field(default_factory=list)


# ── Run Status Response ───────────────────────────────────


class VisualOutput(BaseModel):
    type: str
    label: str = ""
    url: str = ""


class ToolLogEntry(BaseModel):
    tool: str
    run_mode: str = ""
    status: str = ""
    runtime_ms: int = 0
    summary: str = ""
    confidence: float | None = None
    reason: str | None = None  # for skipped


class RunTraceResponse(BaseModel):
    run_id: str
    workflow: str = ""
    input_summary: dict[str, Any] = Field(default_factory=dict)
    parallel_groups: list[list[str]] = Field(default_factory=list)
    tool_logs: list[ToolLogEntry] = Field(default_factory=list)
    final_confidence: float | None = None


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    query: str = ""
    current_step: str | None = None
    progress: float = 0.0
    answer: str | None = None
    confidence: float | None = None
    evidence: list[str] = Field(default_factory=list)
    visual_outputs: list[VisualOutput] = Field(default_factory=list)
    trace: RunTraceResponse | None = None
