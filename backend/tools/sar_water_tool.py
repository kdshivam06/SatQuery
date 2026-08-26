"""SAR water/flood detector – low-backscatter thresholding."""

from __future__ import annotations

from backend.geospatial.dependencies import require_module
from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import (
    confidence_from_coverage, coverage_percent, find_asset,
    get_model_input_path, get_preview_path, get_resolution,
    mask_to_area_sq_m, otsu_threshold, write_mask_and_overlay,
)


class SARWaterTool(BaseTool):
    name = "sar_water_detector"
    purpose = "Detect water/flood regions from low SAR backscatter."
    tool_type = "static_function"
    run_mode = "static_function"
    resource_lane = "cpu"
    input_modalities = ["sar"]
    output_types = ["mask", "area", "confidence"]

    COLOR = (0, 120, 255)

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        asset = find_asset(context["manifest"], "sar")
        if not asset or not get_model_input_path(asset):
            return skipped_result(self.name, "No SAR model input available.")

        np = require_module("numpy", "numpy")
        arr = np.load(get_model_input_path(asset))
        score = arr.mean(axis=0)
        threshold = otsu_threshold(score)
        mask = score < threshold

        cov = coverage_percent(mask)
        area = mask_to_area_sq_m(mask, get_resolution(context["manifest"]))
        artifacts = write_mask_and_overlay(
            context["run_dir"], mask, "sar_water.png", "SAR water/flood evidence", self.COLOR,
            preview_path=get_preview_path(asset),
        )
        return {
            "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
            "outputs": {"threshold": float(threshold), "coverage_percent": cov, "area_sq_m": area},
            "confidence": confidence_from_coverage(cov),
            "summary": f"SAR low-backscatter water evidence covers {cov:.2f}% of the patch.",
            "artifacts": artifacts,
        }
