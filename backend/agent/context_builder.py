"""Context builder – prepares the RouterInput from uploaded images + metadata."""

from __future__ import annotations

from backend.tools.registry import get_registry_summary_for_router, get_enabled_tools


def build_router_input(query: str, manifest: dict, *, mode: str = "auto") -> dict:
    """Build the JSON payload that the LLM router or fallback router consumes."""

    assets = manifest.get("assets", [])
    modalities = [a.get("modality", {}).get("modality", "unknown") for a in assets]
    formats = [a.get("metadata", {}).get("format", "unknown") for a in assets]
    alignment = manifest.get("alignment")

    # Detect configuration
    configuration = _detect_configuration(modalities, mode)

    # Collect available bands per modality
    available_bands: dict[str, list[str]] = {}
    for asset in assets:
        mod = asset.get("modality", {}).get("modality", "unknown")
        mi = asset.get("model_input")
        if mi and mi.get("band_order"):
            available_bands[mod] = mi["band_order"]

    # Resource availability
    resource_state = {
        "cpu_available": True,
        "local_gpu_light_available": True,
        "remote_api_available": True,
    }

    # Available tools (enabled only, no legacy aliases)
    enabled = get_registry_summary_for_router()

    return {
        "query": query,
        "input_summary": {
            "image_count": len(assets),
            "formats": formats,
            "modalities": modalities,
            "configuration": configuration,
            "alignment_status": "passed" if alignment and alignment.get("compatible") else "failed" if alignment else "unknown",
            "available_bands": available_bands,
        },
        "available_tools": list(enabled.keys()),
        "tool_details": enabled,
        "resource_state": resource_state,
    }


def _detect_configuration(modalities: list[str], mode: str) -> str:
    """Detect input configuration: single, cross_modal_pair, temporal_pair."""
    if mode and mode != "auto":
        mode_map = {
            "single": "single",
            "cross_modal": "cross_modal_pair",
            "sar_optical": "cross_modal_pair",
            "temporal": "temporal_pair",
            "change": "temporal_pair",
        }
        if mode in mode_map:
            return mode_map[mode]

    if len(modalities) < 2:
        return "single"

    has_sar = "sar" in modalities
    has_optical = any(m in modalities for m in ("optical", "multispectral"))

    if has_sar and has_optical:
        return "cross_modal_pair"

    # Two images of same modality → temporal pair
    if len(modalities) == 2 and modalities[0] == modalities[1]:
        return "temporal_pair"

    return "multi_image"
