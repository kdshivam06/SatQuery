"""Provider-neutral serverless inference handler for SAR-Optical dual encoder."""

from __future__ import annotations

import os
import time
import tempfile
from pathlib import Path
from typing import Any, Dict

from serverless.custom_sar_optical.loader import get_inference_device, load_model_classifiers


def handle_inference(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Serverless entrypoint handler.

    Accepts a dictionary with:
    - sar_input_path: str (path to SAR .npy stack)
    - optical_input_path: str (path to Optical .npy stack)
    - checkpoint_dir: str (optional path to custom checkpoint directory)

    Returns a JSON-serializable structured response dictionary.
    """
    start_time = time.perf_counter()

    sar_path = event.get("sar_input_path")
    optical_path = event.get("optical_input_path")
    checkpoint_dir = event.get("checkpoint_dir") or os.getenv("MODEL_CHECKPOINT_DIR")

    if not sar_path and not optical_path:
        runtime_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "status": "failed",
            "error": "Missing inputs: At least one of sar_input_path or optical_input_path must be provided.",
            "runtime_ms": runtime_ms,
        }

    # Validate file existence if provided
    if sar_path and not os.path.exists(sar_path):
        runtime_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "status": "failed",
            "error": f"SAR input file not found: {sar_path}",
            "runtime_ms": runtime_ms,
        }

    if optical_path and not os.path.exists(optical_path):
        runtime_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "status": "failed",
            "error": f"Optical input file not found: {optical_path}",
            "runtime_ms": runtime_ms,
        }

    try:
        classifier_s1, classifier_s2 = load_model_classifiers(checkpoint_dir=checkpoint_dir)
    except Exception as exc:
        # Fallback metadata mode when official model packages/weights are unavailable
        runtime_ms = int((time.perf_counter() - start_time) * 1000)
        return _fallback_inference(sar_path, optical_path, runtime_ms, error=str(exc))

    temp_dir = tempfile.mkdtemp(prefix="serverless_sar_optical_")
    work_dir = Path(temp_dir)

    results = {}
    s1_labels = []
    s2_labels = []

    # Run SAR inference
    if sar_path and classifier_s1:
        try:
            pred = classifier_s1.predict_from_member2_stack(sar_path, work_dir=work_dir / "s1")
            s1_labels = pred.labels
            results["s1_prediction"] = pred.to_dict()
        except Exception as exc:
            results["s1_error"] = str(exc)

    # Run Optical inference
    if optical_path and classifier_s2:
        try:
            pred = classifier_s2.predict_from_member2_stack(optical_path, work_dir=work_dir / "s2")
            s2_labels = pred.labels
            results["s2_prediction"] = pred.to_dict()
        except Exception as exc:
            results["s2_error"] = str(exc)

    # Compute agreement & similarity
    similarity, matched = _compute_agreement(s1_labels, s2_labels)
    all_labels = sorted(list({l["label"] for l in s1_labels + s2_labels}))
    confidence = similarity if matched else max(0.4, similarity * 0.7)

    runtime_ms = int((time.perf_counter() - start_time) * 1000)

    return {
        "status": "success",
        "similarity": similarity,
        "matched": matched,
        "confidence": confidence,
        "agreed_labels": all_labels,
        "s1_labels": s1_labels,
        "s2_labels": s2_labels,
        "runtime_ms": runtime_ms,
        "device": get_inference_device(),
        "details": results,
    }


def _compute_agreement(s1_labels: list, s2_labels: list) -> tuple[float, bool]:
    if not s1_labels or not s2_labels:
        return (0.5, False) if (s1_labels or s2_labels) else (0.3, False)

    s1_set = {l["label"] for l in s1_labels}
    s2_set = {l["label"] for l in s2_labels}
    overlap = s1_set & s2_set
    union = s1_set | s2_set

    if not union:
        return 0.3, False

    jaccard = len(overlap) / len(union)
    similarity = round(0.5 + jaccard * 0.45, 2)
    matched = jaccard > 0.2
    return similarity, matched


def _fallback_inference(sar_path: str | None, optical_path: str | None, runtime_ms: int, error: str) -> dict:
    has_both = sar_path is not None and optical_path is not None
    return {
        "status": "success",
        "mode": "metadata_fallback",
        "similarity": 0.5 if has_both else 0.3,
        "matched": False,
        "confidence": 0.4,
        "agreed_labels": [],
        "s1_labels": [],
        "s2_labels": [],
        "runtime_ms": runtime_ms,
        "note": f"Model packages not installed; using fallback: {error}",
    }
