"""Mask fusion tool – combines multiple binary masks (e.g. NDWI + SAR water)."""

from __future__ import annotations

from pathlib import Path

from backend.geospatial.dependencies import require_module
from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import (
    confidence_from_coverage, coverage_percent, get_resolution,
    mask_to_area_sq_m, write_mask_and_overlay,
)


class MaskFusionTool(BaseTool):
    name = "mask_fusion_tool"
    purpose = "Combine NDWI + SAR water masks or optical + SAR evidence."
    tool_type = "static_function"
    run_mode = "static_function"
    resource_lane = "cpu"
    input_modalities = ["optical", "multispectral", "sar"]
    output_types = ["mask", "area", "confidence"]

    COLOR = (0, 200, 255)

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        np = require_module("numpy", "numpy")
        Image = require_module("PIL.Image", "Pillow")

        # Collect mask artifacts from prior tool results
        mask_paths = []
        for result in prior_results.values():
            for artifact in result.get("artifacts", []):
                if artifact.get("type") == "mask":
                    mask_paths.append(artifact["path"])

        if len(mask_paths) < 2:
            return skipped_result(self.name, f"Need at least 2 masks to fuse, found {len(mask_paths)}.")

        # Load and resize masks to match the first one
        first = np.asarray(Image.open(mask_paths[0]).convert("L")) > 127
        fused = first.copy()
        method = params.get("method", "union")

        for mpath in mask_paths[1:]:
            other = np.asarray(Image.open(mpath).convert("L").resize(
                (first.shape[1], first.shape[0])
            )) > 127
            if method == "intersection":
                fused = fused & other
            else:  # union
                fused = fused | other

        cov = coverage_percent(fused)
        area = mask_to_area_sq_m(fused, get_resolution(context["manifest"]))

        # Find a preview to overlay on
        preview_path = None
        for asset in context["manifest"].get("assets", []):
            p = asset.get("preview", {}).get("preview_path")
            if p:
                preview_path = p
                break

        artifacts = write_mask_and_overlay(
            context["run_dir"], fused, "fused_mask.png", "Fused evidence mask", self.COLOR,
            preview_path=preview_path,
        )
        return {
            "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
            "outputs": {"method": method, "input_masks": len(mask_paths), "coverage_percent": cov, "area_sq_m": area},
            "confidence": confidence_from_coverage(cov),
            "summary": f"Fused {len(mask_paths)} masks ({method}). Combined evidence covers {cov:.2f}%.",
            "artifacts": artifacts,
        }
