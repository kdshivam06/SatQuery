"""SatQuery AI – individual static-function tools.

Each tool is a separate class inheriting from BaseTool.
These are the *new* per-file tools that will be re-exported via the registry.
"""

from __future__ import annotations

from backend.geospatial.dependencies import require_module
from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import (
    confidence_from_coverage,
    coverage_percent,
    find_asset,
    get_band_order,
    get_model_input_path,
    get_preview_path,
    get_resolution,
    mask_to_area_sq_m,
    write_mask_and_overlay,
)


# ─────────────────────────────────────────────────────────
# metadata_tool
# ─────────────────────────────────────────────────────────


class MetadataReaderTool(BaseTool):
    name = "metadata_reader"
    purpose = "Read GeoTIFF metadata: CRS, bounds, transform, resolution, band count, nodata, dtype, image size."
    tool_type = "static_function"
    run_mode = "static_function"
    resource_lane = "cpu"
    input_modalities = ["optical", "multispectral", "sar", "unknown"]
    output_types = ["metadata"]

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        manifest = context["manifest"]
        assets = manifest.get("assets", [])
        modalities = [a.get("modality", {}).get("modality") for a in assets]
        alignment = manifest.get("alignment")
        summary = f"Read {len(assets)} asset(s): {', '.join(str(m) for m in modalities)}."
        if alignment:
            summary += f" Alignment compatible={alignment.get('compatible')} score={alignment.get('score')}."
        previews = []
        for asset in assets:
            p = asset.get("preview")
            if p:
                previews.append({"type": "preview", "label": asset.get("metadata", {}).get("filename", "preview"), "path": p["preview_path"]})
        return {
            "status": "success",
            "run_mode": self.run_mode,
            "resource_lane": self.resource_lane,
            "outputs": {"asset_count": len(assets), "modalities": modalities, "alignment": alignment},
            "confidence": 0.95 if assets else 0.2,
            "summary": summary,
            "artifacts": previews,
        }
