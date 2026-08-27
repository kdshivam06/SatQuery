import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).parent.parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass

from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import find_asset, get_preview_path


RSLLAVA_ENABLED = os.getenv("RSLLAVA_ENABLED", "true").lower() == "true"
RSLLAVA_MODEL_ID = os.getenv("RSLLAVA_MODEL_ID", "BigData-KSU/RS-llava-v1.5-7b-LoRA")
RSLLAVA_MODEL_BASE = os.getenv("RSLLAVA_MODEL_BASE", "Intel/neural-chat-7b-v3-3")
RSLLAVA_ENDPOINT = os.getenv("RSLLAVA_ENDPOINT", "")


class RSLLavaTool(BaseTool):
    name = "rsllava_vqa_caption_tool"
    purpose = "Remote-sensing visual question answering and image captioning via RS-LLaVA."
    tool_type = "pretrained_model"
    run_mode = "remote_hf_api"
    resource_lane = "remote_api"
    input_modalities = ["optical", "multispectral", "preview"]
    output_types = ["answer", "caption", "confidence"]
    enabled = RSLLAVA_ENABLED

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        if not self.enabled:
            return skipped_result(self.name, "RS-LLaVA is disabled.", run_mode=self.run_mode, resource_lane=self.resource_lane)

        # Find optical/multispectral preview image to send
        preview = None
        for mod in ("optical", "multispectral", "preview"):
            asset = find_asset(context.get("manifest", {}), mod)
            if asset:
                preview = get_preview_path(asset)
                if preview:
                    break

        if not preview:
            return skipped_result(
                self.name,
                "No optical or multispectral preview image available for RS-LLaVA.",
                run_mode=self.run_mode,
                resource_lane=self.resource_lane,
            )

        query = params.get("prompt", context.get("query", "Describe this remote sensing image."))

        # 1. Custom HTTP endpoint (if configured)
        if RSLLAVA_ENDPOINT:
            return await self._call_endpoint(RSLLAVA_ENDPOINT, preview, query)

        # 2. Hugging Face Serverless Inference API (if HF_TOKEN is configured)
        hf_token = os.getenv("HF_TOKEN", "")
        if hf_token:
            return await self._call_serverless_api(RSLLAVA_MODEL_ID, preview, query)

        # Neither endpoint nor HF_TOKEN configured — return informative skip
        return skipped_result(
            self.name,
            "RS-LLaVA endpoint or HF_TOKEN not configured. Set RSLLAVA_ENDPOINT or HF_TOKEN in .env to enable serverless inference.",
            run_mode=self.run_mode,
            resource_lane=self.resource_lane,
        )

    async def _call_endpoint(self, endpoint: str, image_path: str, query: str) -> dict:
        """Call a custom HTTP endpoint for RS-LLaVA inference."""
        try:
            import base64
            from backend.geospatial.dependencies import require_module
            httpx = require_module("httpx", "httpx")

            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(endpoint, json={"image": img_b64, "query": query})
                resp.raise_for_status()
                data = resp.json()

            answer = data.get("answer", data.get("text", str(data)))
            return {
                "status": "success",
                "run_mode": self.run_mode,
                "resource_lane": self.resource_lane,
                "outputs": {
                    "answer": answer,
                    "caption": answer,
                    "source": f"endpoint:{endpoint}",
                },
                "confidence": 0.75,
                "summary": f"RS-LLaVA: {answer[:200]}",
                "artifacts": [],
            }
        except Exception as exc:
            return skipped_result(
                self.name,
                f"RS-LLaVA endpoint call failed: {exc}",
                run_mode=self.run_mode,
                resource_lane=self.resource_lane,
            )

    async def _call_serverless_api(self, model_id: str, image_path: str, query: str) -> dict:
        """Call Hugging Face Serverless Inference API for RS-LLaVA."""
        try:
            from backend.tools.hf_serverless import call_hf_vlm
            answer = await call_hf_vlm(model_id, [image_path], query)

            return {
                "status": "success",
                "run_mode": self.run_mode,
                "resource_lane": self.resource_lane,
                "outputs": {
                    "answer": answer,
                    "caption": answer,
                    "source": f"hf_serverless:{model_id}",
                },
                "confidence": 0.75,
                "summary": f"RS-LLaVA: {answer[:200]}",
                "artifacts": [],
            }
        except Exception as exc:
            return skipped_result(
                self.name,
                f"RS-LLaVA serverless API call failed: {exc}",
                run_mode=self.run_mode,
                resource_lane=self.resource_lane,
            )
