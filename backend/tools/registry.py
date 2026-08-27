"""Full tool registry for SatQuery AI.

Every tool is registered with: name, purpose, type, run_mode, resource_lane,
input_modalities, outputs, enabled, fallback_behavior.
"""

from __future__ import annotations

from backend.tools.metadata_tool import MetadataReaderTool
from backend.tools.preview_tool import PreviewGeneratorTool
from backend.tools.ndvi_tool import NDVITool
from backend.tools.ndwi_tool import NDWITool
from backend.tools.mndwi_tool import MNDWITool
from backend.tools.ndbi_tool import NDBITool
from backend.tools.sar_water_tool import SARWaterTool
from backend.tools.sar_builtup_tool import SARBuiltupTool
from backend.tools.change_map_tool import ChangeMapTool
from backend.tools.mask_fusion_tool import MaskFusionTool
from backend.tools.area_calculator_tool import AreaCalculatorTool
from backend.tools.overlay_tool import OverlayGeneratorTool
from backend.tools.custom_dual_encoder_tool import CustomDualEncoderTool
from backend.tools.croma_tool import CROMATool
from backend.tools.remoteclip_tool import RemoteCLIPTool
from backend.tools.rsllava_tool import RSLLavaTool
from backend.tools.geochat_tool import GeoChatTool
from backend.tools.teochat_tool import TEOChatTool
from backend.tools.segearth_tool import SegEarthTool
from backend.tools.sarclip_tool import SARCLIPTool


# ── Tool instances ────────────────────────────────────────

TOOL_REGISTRY: dict[str, object] = {
    # Static function tools (CPU)
    "metadata_reader": MetadataReaderTool(),
    "preview_generator": PreviewGeneratorTool(),
    "ndvi_vegetation_detector": NDVITool(),
    "ndwi_water_detector": NDWITool(),
    "mndwi_water_detector": MNDWITool(),
    "ndbi_builtup_detector": NDBITool(),
    "sar_water_detector": SARWaterTool(),
    "sar_builtup_detector": SARBuiltupTool(),
    "change_map_generator": ChangeMapTool(),
    "mask_fusion_tool": MaskFusionTool(),
    "area_calculator": AreaCalculatorTool(),
    "overlay_generator": OverlayGeneratorTool(),

    # Local downloaded model tools (GPU light)
    "custom_sar_optical_dual_encoder_tool": CustomDualEncoderTool(),
    "croma_cross_modal_feature_tool": CROMATool(),
    "remoteclip_optical_retrieval_tool": RemoteCLIPTool(),

    # Remote HF API tools
    "geochat_vqa_caption_tool": GeoChatTool(),
    "rsllava_vqa_caption_tool": RSLLavaTool(),
    "teochat_change_vqa_tool": TEOChatTool(),
    "segearth_text_guided_segmentation_tool": SegEarthTool(),
    "sarclip_sar_text_tool": SARCLIPTool(),
}

# ── Legacy aliases (keep old names working) ───────────────

TOOL_REGISTRY["metadata_summary"] = TOOL_REGISTRY["metadata_reader"]
TOOL_REGISTRY["ndwi_water"] = TOOL_REGISTRY["ndwi_water_detector"]
TOOL_REGISTRY["ndbi_builtup"] = TOOL_REGISTRY["ndbi_builtup_detector"]
TOOL_REGISTRY["sar_water"] = TOOL_REGISTRY["sar_water_detector"]
TOOL_REGISTRY["sar_builtup"] = TOOL_REGISTRY["sar_builtup_detector"]
TOOL_REGISTRY["change_map"] = TOOL_REGISTRY["change_map_generator"]


# ── Registry helpers ──────────────────────────────────────


def get_enabled_tools() -> dict[str, object]:
    """Return only tools that are enabled."""
    return {
        name: tool
        for name, tool in TOOL_REGISTRY.items()
        if getattr(tool, "enabled", True)
    }


def get_tools_for_modality(modality: str) -> list[str]:
    """Return tool names that accept the given modality."""
    result = []
    for name, tool in TOOL_REGISTRY.items():
        mods = getattr(tool, "input_modalities", [])
        if modality in mods or "unknown" in mods:
            if getattr(tool, "enabled", True):
                result.append(name)
    return result


def get_registry_summary_for_router() -> dict[str, dict]:
    """Return a JSON-serialisable summary of enabled tools for the LLM router."""
    summary = {}
    for name, tool in TOOL_REGISTRY.items():
        if not getattr(tool, "enabled", True):
            continue
        # Skip legacy aliases
        if name in ("metadata_summary", "ndwi_water", "ndbi_builtup", "sar_water", "sar_builtup", "change_map"):
            continue
        summary[name] = {
            "type": getattr(tool, "tool_type", "static_function"),
            "run_mode": getattr(tool, "run_mode", "static_function"),
            "resource_lane": getattr(tool, "resource_lane", "cpu"),
            "purpose": getattr(tool, "purpose", ""),
            "input_modalities": list(getattr(tool, "input_modalities", [])),
            "outputs": list(getattr(tool, "output_types", [])),
        }
    return summary
