"""SARCLIP SAR-text inference tool – optional, disabled by default."""

from __future__ import annotations

import os

from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import find_asset, get_preview_path


SARCLIP_ENABLED = os.getenv("SARCLIP_ENABLED", "false").lower() == "true"
SARCLIP_ENDPOINT = os.getenv("SARCLIP_ENDPOINT", "")


class SARCLIPTool(BaseTool):
    name = "sarclip_sar_text_tool"
    purpose = "Optional SAR image-text scoring and zero-shot SAR classification."
    tool_type = "pretrained_model"
    run_mode = "optional_disabled"
    resource_lane = "remote_api"
    input_modalities = ["sar"]
    output_types = ["text_scores", "best_label", "confidence"]
    enabled = SARCLIP_ENABLED

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        if not self.enabled:
            return skipped_result(
                self.name,
                "SARCLIP is disabled. It is only used for SAR-to-text inference, not primary cross-modal retrieval.",
                run_mode=self.run_mode, resource_lane=self.resource_lane,
            )

        sar_asset = find_asset(context["manifest"], "sar")
        if not sar_asset:
            return skipped_result(self.name, "No SAR input available.", run_mode=self.run_mode, resource_lane=self.resource_lane)

        preview = get_preview_path(sar_asset)
        if not preview:
            return skipped_result(self.name, "No SAR preview available.", run_mode=self.run_mode, resource_lane=self.resource_lane)

        if not SARCLIP_ENDPOINT:
            return skipped_result(self.name, "SARCLIP endpoint not configured.", run_mode=self.run_mode, resource_lane=self.resource_lane)

        labels = params.get("labels", ["water", "urban", "cropland", "forest", "bare soil", "wetland"])

        try:
            import base64
            from backend.geospatial.dependencies import require_module
            httpx = require_module("httpx", "httpx")

            with open(preview, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(SARCLIP_ENDPOINT, json={"image": img_b64, "labels": labels})
                resp.raise_for_status()
                data = resp.json()

            return {
                "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
                "outputs": data,
                "confidence": 0.65,
                "summary": f"SARCLIP scored SAR against {len(labels)} text labels.",
                "artifacts": [],
            }
        except Exception as exc:
            return skipped_result(self.name, f"SARCLIP call failed: {exc}", run_mode=self.run_mode, resource_lane=self.resource_lane)
