"""Bi-temporal change map generator – pixel-wise difference."""

from __future__ import annotations

from backend.geospatial.dependencies import require_module
from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import (
    confidence_from_coverage, coverage_percent, get_resolution,
    mask_to_area_sq_m, write_mask_and_overlay,
)


class ChangeMapTool(BaseTool):
    name = "change_map_generator"
    purpose = "Produce pixel-wise difference map for bi-temporal images."
    tool_type = "static_function"
    run_mode = "static_function"
    resource_lane = "cpu"
    input_modalities = ["optical", "multispectral", "sar"]
    output_types = ["mask", "area", "confidence"]

    COLOR = (255, 40, 80)

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        previews = [
            asset.get("preview", {}).get("preview_path")
            for asset in context["manifest"].get("assets", [])
            if asset.get("preview")
        ]
        if len(previews) < 2:
            return skipped_result(self.name, "At least two previews are required for change detection.")

        np = require_module("numpy", "numpy")
        Image = require_module("PIL.Image", "Pillow")

        a = Image.open(previews[0]).convert("L")
        b = Image.open(previews[1]).convert("L").resize(a.size)
        diff = np.abs(np.asarray(a, dtype="float32") - np.asarray(b, dtype="float32"))
        threshold = float(diff.mean() + diff.std())
        mask = diff > threshold

        cov = coverage_percent(mask)
        area = mask_to_area_sq_m(mask, get_resolution(context["manifest"]))
        artifacts = write_mask_and_overlay(
            context["run_dir"], mask, "change_map.png", "Change evidence", self.COLOR,
            preview_path=previews[1],
        )
        return {
            "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
            "outputs": {"threshold": threshold, "coverage_percent": cov, "area_sq_m": area},
            "confidence": confidence_from_coverage(cov),
            "summary": f"Pixel-difference change evidence covers {cov:.2f}% of the compared patch.",
            "artifacts": artifacts,
        }
