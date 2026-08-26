"""TEOChat bi-temporal change VQA tool – calls remote HF Space or endpoint."""

from __future__ import annotations

import os

from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import get_preview_path


TEOCHAT_ENABLED = os.getenv("TEOCHAT_ENABLED", "true").lower() == "true"
TEOCHAT_SPACE_ID = os.getenv("TEOCHAT_SPACE_ID", "")
TEOCHAT_ENDPOINT = os.getenv("TEOCHAT_ENDPOINT", "")


class TEOChatTool(BaseTool):
    name = "teochat_change_vqa_tool"
    purpose = "Bi-temporal change VQA and change description."
    tool_type = "pretrained_model"
    run_mode = "remote_hf_api"
    resource_lane = "remote_api"
    input_modalities = ["temporal_pair"]
    output_types = ["answer", "change_description", "confidence"]
    enabled = TEOCHAT_ENABLED

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        if not self.enabled:
            return skipped_result(self.name, "TEOChat is disabled.", run_mode=self.run_mode, resource_lane=self.resource_lane)

        assets = context["manifest"].get("assets", [])
        previews = [get_preview_path(a) for a in assets if get_preview_path(a)]

        if len(previews) < 2:
            return skipped_result(self.name, "TEOChat requires two temporal previews.", run_mode=self.run_mode, resource_lane=self.resource_lane)

        query = params.get("prompt", context.get("query", "Describe what has changed between these two images."))

        if TEOCHAT_SPACE_ID:
            return await self._call_space(TEOCHAT_SPACE_ID, previews[0], previews[1], query)
        if TEOCHAT_ENDPOINT:
            return await self._call_endpoint(TEOCHAT_ENDPOINT, previews[0], previews[1], query)

        return skipped_result(
            self.name,
            "TEOChat endpoint not configured. Set TEOCHAT_SPACE_ID or TEOCHAT_ENDPOINT in .env. "
            "The system produced a deterministic change map instead.",
            run_mode=self.run_mode,
            resource_lane=self.resource_lane,
        )

    async def _call_space(self, space_id: str, img1: str, img2: str, query: str) -> dict:
        try:
            from gradio_client import Client
            client = Client(space_id)
            result = client.predict(img1, img2, query, api_name="/predict")
            answer = str(result) if result else "No response from TEOChat."
            return {
                "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
                "outputs": {"answer": answer, "change_description": answer, "source": f"hf_space:{space_id}"},
                "confidence": 0.75,
                "summary": f"TEOChat: {answer[:200]}",
                "artifacts": [],
            }
        except Exception as exc:
            return skipped_result(self.name, f"TEOChat Space call failed: {exc}", run_mode=self.run_mode, resource_lane=self.resource_lane)

    async def _call_endpoint(self, endpoint: str, img1: str, img2: str, query: str) -> dict:
        try:
            import base64
            from backend.geospatial.dependencies import require_module
            httpx = require_module("httpx", "httpx")

            imgs_b64 = []
            for p in (img1, img2):
                with open(p, "rb") as f:
                    imgs_b64.append(base64.b64encode(f.read()).decode())

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(endpoint, json={"images": imgs_b64, "query": query})
                resp.raise_for_status()
                data = resp.json()

            answer = data.get("answer", data.get("text", str(data)))
            return {
                "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
                "outputs": {"answer": answer, "change_description": answer, "source": f"endpoint:{endpoint}"},
                "confidence": 0.75,
                "summary": f"TEOChat: {answer[:200]}",
                "artifacts": [],
            }
        except Exception as exc:
            return skipped_result(self.name, f"TEOChat endpoint call failed: {exc}", run_mode=self.run_mode, resource_lane=self.resource_lane)
