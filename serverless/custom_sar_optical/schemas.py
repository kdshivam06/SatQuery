"""Request and response schemas for serverless SAR-optical inference."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class InferenceRequest(BaseModel):
    sar_input_path: Optional[str] = Field(None, description="Path to SAR .npy channel-first tensor or image file")
    optical_input_path: Optional[str] = Field(None, description="Path to Optical/Multispectral .npy channel-first tensor or image file")
    checkpoint_dir: Optional[str] = Field(None, description="Optional path to custom checkpoint directory e.g. best_ben14k_isro_retrieval")


class LabelPrediction(BaseModel):
    label: str
    score: float


class InferenceResponse(BaseModel):
    status: str = "success"
    similarity: float
    matched: bool
    confidence: float
    agreed_labels: list[str] = Field(default_factory=list)
    s1_labels: list[dict[str, Any]] = Field(default_factory=list)
    s2_labels: list[dict[str, Any]] = Field(default_factory=list)
    runtime_ms: int = 0
    mode: str = "model_inference"
    note: Optional[str] = None


class ErrorResponse(BaseModel):
    status: str = "failed"
    error: str
    runtime_ms: int = 0
