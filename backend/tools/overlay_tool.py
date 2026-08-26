"""Overlay generator – renders masks/boxes over image previews for UI evidence."""

from __future__ import annotations

from pathlib import Path

from backend.geospatial.dependencies import require_module
from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import write_overlay_png


class OverlayGeneratorTool(BaseTool):
    name = "overlay_generator"
    purpose = "Render masks/boxes over image previews for UI evidence."
    tool_type = "static_function"
    run_mode = "static_function"
    resource_lane = "cpu"
    input_modalities = ["optical", "multispectral", "sar"]
    output_types = ["overlay"]

    # Default colours for different evidence types
    COLOURS = {
        "water": (0, 110, 255),
        "vegetation": (20, 170, 70),
        "builtup": (255, 145, 0),
        "change": (255, 40, 80),
        "default": (0, 200, 255),
    }

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        np = require_module("numpy", "numpy")
        Image = require_module("PIL.Image", "Pillow")

        # Find a preview to overlay on
        preview_path = None
        for asset in context["manifest"].get("assets", []):
            p = asset.get("preview", {}).get("preview_path")
            if p:
                preview_path = p
                break

        if not preview_path:
            return skipped_result(self.name, "No preview image available for overlay.")

        # Collect mask artifacts from prior results that don't already have overlays
        masks_to_overlay = []
        existing_overlays = set()
        for result in prior_results.values():
            for artifact in result.get("artifacts", []):
                if artifact.get("type") == "overlay":
                    existing_overlays.add(artifact.get("label", ""))
        for result in prior_results.values():
            for artifact in result.get("artifacts", []):
                if artifact.get("type") == "mask" and artifact.get("label", "") not in existing_overlays:
                    masks_to_overlay.append(artifact)

        if not masks_to_overlay:
            return {
                "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
                "outputs": {"overlays_created": 0},
                "confidence": 0.8,
                "summary": "All masks already have overlays; no new overlays needed.",
                "artifacts": [],
            }

        out_dir = Path(context["run_dir"]) / "tool_outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        artifacts = []

        for mask_artifact in masks_to_overlay:
            label = mask_artifact.get("label", "evidence")
            color = self._pick_colour(label)
            mask = np.asarray(Image.open(mask_artifact["path"]).convert("L")) > 127
            overlay_name = Path(mask_artifact["path"]).stem + "_overlay.png"
            overlay_path = out_dir / overlay_name
            saved = write_overlay_png(mask, preview_path, overlay_path, color)
            artifacts.append({"type": "overlay", "label": label, "path": saved})

        return {
            "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
            "outputs": {"overlays_created": len(artifacts)},
            "confidence": 0.9,
            "summary": f"Created {len(artifacts)} overlay(s) over preview.",
            "artifacts": artifacts,
        }

    def _pick_colour(self, label: str) -> tuple[int, int, int]:
        label_lower = label.lower()
        for keyword, colour in self.COLOURS.items():
            if keyword in label_lower:
                return colour
        return self.COLOURS["default"]
