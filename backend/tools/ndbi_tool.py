"""NDBI built-up detector – (SWIR - NIR) / (SWIR + NIR)."""

from __future__ import annotations

from backend.geospatial.dependencies import require_module
from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import (
    confidence_from_coverage, coverage_percent, find_asset,
    get_band_order, get_model_input_path, get_preview_path,
    get_resolution, mask_to_area_sq_m, safe_normalized_index,
    write_mask_and_overlay,
)


class NDBITool(BaseTool):
    name = "ndbi_builtup_detector"
    purpose = "Detect built-up/urban regions using NIR/SWIR bands."
    tool_type = "static_function"
    run_mode = "static_function"
    resource_lane = "cpu"
    input_modalities = ["multispectral"]
    output_types = ["mask", "area", "confidence"]

    BAND_A = "B11"  # SWIR
    BAND_B = "B08"  # NIR
    THRESHOLD = 0.0
    COLOR = (255, 145, 0)

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        asset = find_asset(context["manifest"], "multispectral")
        if not asset or not get_model_input_path(asset):
            return skipped_result(self.name, "No multispectral model input available.")

        np = require_module("numpy", "numpy")
        band_order = get_band_order(asset)
        if self.BAND_A not in band_order or self.BAND_B not in band_order:
            return skipped_result(self.name, f"Missing bands: need {self.BAND_A} (SWIR) and {self.BAND_B} (NIR).")

        arr = np.load(get_model_input_path(asset))
        swir = arr[band_order.index(self.BAND_A)]
        nir = arr[band_order.index(self.BAND_B)]
        index = safe_normalized_index(swir, nir)
        threshold = params.get("threshold", self.THRESHOLD)
        mask = index > threshold

        cov = coverage_percent(mask)
        area = mask_to_area_sq_m(mask, get_resolution(context["manifest"]))
        artifacts = write_mask_and_overlay(
            context["run_dir"], mask, "ndbi.png", "NDBI built-up evidence", self.COLOR,
            preview_path=get_preview_path(asset),
        )
        return {
            "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
            "outputs": {"index": "ndbi", "threshold": threshold, "coverage_percent": cov, "area_sq_m": area},
            "confidence": confidence_from_coverage(cov),
            "summary": f"NDBI built-up evidence covers {cov:.2f}% of the patch.",
            "artifacts": artifacts,
        }
