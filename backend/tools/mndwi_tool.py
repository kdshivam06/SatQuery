"""MNDWI water detector – (Green - SWIR) / (Green + SWIR)."""

from __future__ import annotations

from backend.geospatial.dependencies import require_module
from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import (
    confidence_from_coverage, coverage_percent, find_asset,
    get_band_order, get_model_input_path, get_preview_path,
    get_resolution, mask_to_area_sq_m, safe_normalized_index,
    write_mask_and_overlay,
)


class MNDWITool(BaseTool):
    name = "mndwi_water_detector"
    purpose = "Better water extraction when SWIR is available."
    tool_type = "static_function"
    run_mode = "static_function"
    resource_lane = "cpu"
    input_modalities = ["multispectral"]
    output_types = ["mask", "area", "confidence"]

    BAND_A = "B03"  # Green
    BAND_B = "B11"  # SWIR
    THRESHOLD = 0.0
    COLOR = (0, 80, 220)

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        asset = find_asset(context["manifest"], "multispectral")
        if not asset or not get_model_input_path(asset):
            return skipped_result(self.name, "No multispectral model input available.")

        np = require_module("numpy", "numpy")
        band_order = get_band_order(asset)
        if self.BAND_A not in band_order or self.BAND_B not in band_order:
            return skipped_result(self.name, f"Missing bands: need {self.BAND_A} (Green) and {self.BAND_B} (SWIR).")

        arr = np.load(get_model_input_path(asset))
        green = arr[band_order.index(self.BAND_A)]
        swir = arr[band_order.index(self.BAND_B)]
        index = safe_normalized_index(green, swir)
        threshold = params.get("threshold", self.THRESHOLD)
        mask = index > threshold

        cov = coverage_percent(mask)
        area = mask_to_area_sq_m(mask, get_resolution(context["manifest"]))
        artifacts = write_mask_and_overlay(
            context["run_dir"], mask, "mndwi.png", "MNDWI water evidence", self.COLOR,
            preview_path=get_preview_path(asset),
        )
        return {
            "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
            "outputs": {"index": "mndwi", "threshold": threshold, "coverage_percent": cov, "area_sq_m": area},
            "confidence": confidence_from_coverage(cov),
            "summary": f"MNDWI water evidence covers {cov:.2f}% of the patch.",
            "artifacts": artifacts,
        }
