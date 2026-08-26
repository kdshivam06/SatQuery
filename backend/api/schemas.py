"""Pydantic schemas for SatQuery API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


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
