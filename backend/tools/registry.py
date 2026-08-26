"""Local executable tool registry."""

from __future__ import annotations

from backend.tools.geospatial_tools import (
    ChangeMapTool,
    MetadataSummaryTool,
    PairCompatibilityTool,
    SarBuiltupTool,
    SarWaterTool,
    SpectralIndexTool,
)
from backend.tools.model_tools import RemoteSensingVLMTool, RetrievalStubTool


TOOL_REGISTRY = {
    "metadata_summary": MetadataSummaryTool(),
    "pair_compatibility": PairCompatibilityTool(),
    "ndvi_vegetation": SpectralIndexTool(
        "ndvi_vegetation",
        numerator=("B08", "B04"),
        threshold=0.25,
        label="NDVI vegetation evidence",
        color=(20, 170, 70),
    ),
    "ndwi_water": SpectralIndexTool(
        "ndwi_water",
        numerator=("B03", "B08"),
        threshold=0.0,
        label="NDWI water evidence",
        color=(0, 110, 255),
    ),
    "ndbi_builtup": SpectralIndexTool(
        "ndbi_builtup",
        numerator=("B11", "B08"),
        threshold=0.0,
        label="NDBI built-up evidence",
        color=(255, 145, 0),
    ),
    "sar_water": SarWaterTool(),
    "sar_builtup": SarBuiltupTool(),
    "change_map": ChangeMapTool(),
    "rs_vlm_caption_vqa": RemoteSensingVLMTool(),
    "retrieval_stub": RetrievalStubTool(),
}
