"""SegEarth-OV text-guided segmentation tool – remote HF API (disabled by default)."""

from __future__ import annotations

import os

from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import find_asset, get_preview_path


SEGEARTH_ENABLED = os.getenv("SEGEARTH_ENABLED", "false").lower() == "true"
SEGEARTH_ENDPOINT = os.getenv("SEGEARTH_ENDPOINT", "")


class SegEarthTool(BaseTool):
    name = "segearth_text_guided_segmentation_tool"
    purpose = "Text-guided segmentation masks for water/building/road/vegetation."
    tool_type = "pretrained_model"
    run_mode = "remote_hf_api"
    resource_lane = "remote_api"
    input_modalities = ["optical", "multispectral", "sar", "preview"]
    output_types = ["mask", "confidence"]
    enabled = SEGEARTH_ENABLED

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        if not self.enabled:
            return skipped_result(self.name, "SegEarth-OV is disabled (SEGEARTH_ENABLED=false).", run_mode=self.run_mode, resource_lane=self.resource_lane)
        if not SEGEARTH_ENDPOINT:
            return skipped_result(self.name, "SegEarth endpoint not configured.", run_mode=self.run_mode, resource_lane=self.resource_lane)

        preview = None
        for mod in ("multispectral", "optical", "sar"):
            asset = find_asset(context["manifest"], mod)
            if asset:
                preview = get_preview_path(asset)
                if preview:
                    break

        if not preview:
            return skipped_result(self.name, "No preview for SegEarth.", run_mode=self.run_mode, resource_lane=self.resource_lane)

        query = params.get("prompt", context.get("query", "segment water bodies"))

        try:
            import base64
            from backend.geospatial.dependencies import require_module
            httpx = require_module("httpx", "httpx")

            with open(preview, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(SEGEARTH_ENDPOINT, json={"image": img_b64, "text": query})
                resp.raise_for_status()
                data = resp.json()

            return {
                "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
                "outputs": data,
                "confidence": 0.7,
                "summary": f"SegEarth segmentation for '{query}' completed.",
                "artifacts": [],
            }
        except Exception as exc:
            return skipped_result(self.name, f"SegEarth call failed: {exc}", run_mode=self.run_mode, resource_lane=self.resource_lane)
