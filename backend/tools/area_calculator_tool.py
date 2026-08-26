"""Area calculator – converts mask pixels to area using GeoTIFF resolution."""

from __future__ import annotations

from backend.geospatial.dependencies import require_module
from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import coverage_percent, get_resolution, mask_to_area_sq_m


class AreaCalculatorTool(BaseTool):
    name = "area_calculator"
    purpose = "Convert mask pixels into area using GeoTIFF resolution."
    tool_type = "static_function"
    run_mode = "static_function"
    resource_lane = "cpu"
    input_modalities = ["optical", "multispectral", "sar"]
    output_types = ["area"]

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        np = require_module("numpy", "numpy")
        Image = require_module("PIL.Image", "Pillow")

        resolution = get_resolution(context["manifest"])
        if resolution is None:
            return skipped_result(self.name, "No pixel resolution metadata available for area calculation.")

        # Find the latest mask artifact from prior results
        mask_path = None
        mask_label = ""
        for result in reversed(list(prior_results.values())):
            for artifact in result.get("artifacts", []):
                if artifact.get("type") == "mask":
                    mask_path = artifact["path"]
                    mask_label = artifact.get("label", "")
                    break
            if mask_path:
                break

        if mask_path is None:
            return skipped_result(self.name, "No mask artifact found from prior tools.")

        mask = np.asarray(Image.open(mask_path).convert("L")) > 127
        area = mask_to_area_sq_m(mask, resolution)
        cov = coverage_percent(mask)

        return {
            "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
            "outputs": {
                "area_sq_m": area,
                "area_sq_km": round(area / 1e6, 4) if area else None,
                "coverage_percent": cov,
                "resolution_m": resolution,
                "source_mask": mask_label,
            },
            "confidence": 0.9 if area else 0.3,
            "summary": f"Area from '{mask_label}': {area:.2f} sq m ({cov:.2f}% coverage).",
            "artifacts": [],
        }
