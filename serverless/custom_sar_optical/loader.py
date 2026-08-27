"""Model loader with process-level warm caching and inference device selection."""

from __future__ import annotations

import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger("serverless_custom_sar_optical")

# Warm process-level cache
_CACHED_CLASSIFIER_S1 = None
_CACHED_CLASSIFIER_S2 = None
_CACHED_DEVICE = None


def get_inference_device():
    """Detect available inference device safely."""
    global _CACHED_DEVICE
    if _CACHED_DEVICE is not None:
        return _CACHED_DEVICE

    try:
        from backend.geospatial.dependencies import require_module
        torch = require_module("torch", "torch")
        _CACHED_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        _CACHED_DEVICE = "cpu"

    return _CACHED_DEVICE


def load_model_classifiers(
    checkpoint_dir: Optional[str] = None,
    model_version: str = "v0.2.0"
) -> Tuple[Any, Any]:
    """Lazy-load and cache the S1 (SAR) and S2 (Optical) classifiers in process memory."""
    global _CACHED_CLASSIFIER_S1, _CACHED_CLASSIFIER_S2

    if _CACHED_CLASSIFIER_S1 is not None and _CACHED_CLASSIFIER_S2 is not None:
        logger.info("Reusing warm-cached SAR-optical model classifiers.")
        return _CACHED_CLASSIFIER_S1, _CACHED_CLASSIFIER_S2

    from backend.modeling.bigearthnet_pretrained import BigEarthNetPretrainedClassifier

    s1_path = os.getenv("SAR_MODEL_PATH", "BIFOLD/BigEarthNet-S1-v2.0")
    s2_path = os.getenv("OPTICAL_MODEL_PATH", "BIFOLD/BigEarthNet-S2-v2.0")

    if checkpoint_dir and os.path.exists(checkpoint_dir):
        # Override model path if custom checkpoint dir exists
        s1_custom = os.path.join(checkpoint_dir, "s1_model")
        s2_custom = os.path.join(checkpoint_dir, "s2_model")
        if os.path.exists(s1_custom):
            s1_path = s1_custom
        if os.path.exists(s2_custom):
            s2_path = s2_custom

    classifier_s1 = BigEarthNetPretrainedClassifier(
        s1_path,
        sensor="s1",
        model_version=model_version,
    )
    classifier_s2 = BigEarthNetPretrainedClassifier(
        s2_path,
        sensor="s2",
        model_version=model_version,
    )

    _CACHED_CLASSIFIER_S1 = classifier_s1
    _CACHED_CLASSIFIER_S2 = classifier_s2
    return _CACHED_CLASSIFIER_S1, _CACHED_CLASSIFIER_S2
