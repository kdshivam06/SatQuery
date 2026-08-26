"""Preview generator tool."""

from __future__ import annotations

from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import find_asset, get_preview_path


class PreviewGeneratorTool(BaseTool):
    name = "preview_generator"
    purpose = "Create RGB/false-color display image for frontend and model input."
    tool_type = "static_function"
    run_mode = "static_function"
    resource_lane = "cpu"
    input_modalities = ["optical", "multispectral", "sar", "unknown"]
    output_types = ["preview"]

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        manifest = context["manifest"]
        previews = []
        for asset in manifest.get("assets", []):
            p = asset.get("preview")
            if p:
                previews.append({
                    "type": "preview",
                    "label": asset.get("metadata", {}).get("filename", "preview"),
                    "path": p["preview_path"],
                })
        if not previews:
            return skipped_result(self.name, "No preview images were generated during ingestion.")
        return {
            "status": "success",
            "run_mode": self.run_mode,
            "resource_lane": self.resource_lane,
            "outputs": {"preview_count": len(previews)},
            "confidence": 0.95,
            "summary": f"Generated {len(previews)} preview image(s).",
            "artifacts": previews,
        }
