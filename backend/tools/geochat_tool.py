"""GeoChat VQA/captioning tool – calls remote HF Space or endpoint.

Uses gradio_client for free public Spaces, or httpx for custom endpoints.
If neither is configured/available, skips cleanly with trace.
"""

from __future__ import annotations

import os

from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import find_asset, get_preview_path


GEOCHAT_ENABLED = os.getenv("GEOCHAT_ENABLED", "true").lower() == "true"
GEOCHAT_SPACE_ID = os.getenv("GEOCHAT_SPACE_ID", "")
GEOCHAT_ENDPOINT = os.getenv("GEOCHAT_ENDPOINT", "")
GEOCHAT_MODEL_ID = os.getenv("GEOCHAT_MODEL_ID", "MBZUAI/geochat-7B")


class GeoChatTool(BaseTool):
    name = "geochat_vqa_caption_tool"
    purpose = "Remote-sensing VQA and captioning via GeoChat."
    tool_type = "pretrained_model"
    run_mode = "remote_hf_api"
    resource_lane = "remote_api"
    input_modalities = ["optical", "multispectral", "sar", "preview"]
    output_types = ["answer", "caption", "boxes", "confidence"]
    enabled = GEOCHAT_ENABLED

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        if not self.enabled:
            return skipped_result(self.name, "GeoChat is disabled.", run_mode=self.run_mode, resource_lane=self.resource_lane)

        # Find a preview image to send
        preview = None
        for mod in ("multispectral", "optical", "sar"):
            asset = find_asset(context["manifest"], mod)
            if asset:
                preview = get_preview_path(asset)
                if preview:
                    break

        if not preview:
            return skipped_result(self.name, "No preview image available for GeoChat.", run_mode=self.run_mode, resource_lane=self.resource_lane)

        query = params.get("prompt", context.get("query", "Describe this remote sensing image."))

        # Use HF Serverless Inference API (free, just needs HF_TOKEN)
        hf_token = os.getenv("HF_TOKEN", "")
        if hf_token:
            return await self._call_serverless(preview, query)

        # No token at all — skip
        return skipped_result(
            self.name,
            "HF_TOKEN not configured. Set HF_TOKEN in .env to enable VLM inference via the free HF Inference API.",
            run_mode=self.run_mode,
            resource_lane=self.resource_lane,
        )

    async def _call_serverless(self, image_path: str, query: str) -> dict:
        try:
            from backend.tools.hf_serverless import call_hf_vlm
            answer = await call_hf_vlm(GEOCHAT_MODEL_ID, [image_path], query)
            return {
                "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
                "outputs": {"answer": answer, "source": f"hf_serverless:{GEOCHAT_MODEL_ID}"},
                "confidence": 0.75, "summary": f"GeoChat: {answer[:200]}", "artifacts": [],
            }
        except Exception as exc:
            return skipped_result(self.name, f"GeoChat serverless inference failed: {exc}", run_mode=self.run_mode, resource_lane=self.resource_lane)

    async def _call_space(self, space_id: str, image_path: str, query: str) -> dict:
        """Call a Gradio Space for GeoChat inference."""
        try:
            from gradio_client import Client
            client = Client(space_id)
            result = client.predict(image_path, query, api_name="/predict")

            answer = str(result) if result else "No response from GeoChat."
            return {
                "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
                "outputs": {"answer": answer, "source": f"hf_space:{space_id}"},
                "confidence": 0.75,
                "summary": f"GeoChat: {answer[:200]}",
                "artifacts": [],
            }
        except Exception as exc:
            return skipped_result(
                self.name,
                f"GeoChat Space call failed: {exc}",
                run_mode=self.run_mode,
                resource_lane=self.resource_lane,
            )

    async def _call_endpoint(self, endpoint: str, image_path: str, query: str) -> dict:
        """Call a custom HTTP endpoint for GeoChat inference."""
        try:
            import base64
            from backend.geospatial.dependencies import require_module
            httpx = require_module("httpx", "httpx")

            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            async with httpx.AsyncClient(timeout=60) as client:
                headers = {"Content-Type": "application/json"}
                hf_token = os.getenv("HF_TOKEN", "")
                if hf_token:
                    headers["Authorization"] = f"Bearer {hf_token}"
                resp = await client.post(endpoint, headers=headers, json={"image": img_b64, "query": query})
                resp.raise_for_status()
                data = resp.json()

            answer = data.get("answer", data.get("text", str(data)))
            return {
                "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
                "outputs": {"answer": answer, "source": f"endpoint:{endpoint}"},
                "confidence": 0.75,
                "summary": f"GeoChat: {answer[:200]}",
                "artifacts": [],
            }
        except Exception as exc:
            return skipped_result(
                self.name,
                f"GeoChat endpoint call failed: {exc}",
                run_mode=self.run_mode,
                resource_lane=self.resource_lane,
            )
