"""Shared Hugging Face Serverless Inference chat client for vision-language models."""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

from backend.geospatial.dependencies import require_module

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass


HF_INFERENCE_BASE_URL = os.getenv(
    "HF_INFERENCE_BASE_URL",
    "https://router.huggingface.co/v1/chat/completions",
)
VLM_SERVERLESS_MODEL_ID = os.getenv("VLM_SERVERLESS_MODEL_ID", "Qwen/Qwen2.5-VL-7B-Instruct")


async def call_hf_vlm(model_id: str, image_paths: list[str], prompt: str) -> str:
    """Send one or more local images to a Hugging Face chat-compatible model."""
    httpx = require_module("httpx", "httpx")
    token = os.getenv("HF_TOKEN", "")
    if not token:
        raise RuntimeError("HF_TOKEN is not configured")

    content: list[dict] = [{"type": "text", "text": prompt}]
    for image_path in image_paths:
        path = Path(image_path)
        media_type = mimetypes.guess_type(path.name)[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{media_type};base64,{encoded}"},
        })

    effective_model_id = VLM_SERVERLESS_MODEL_ID or model_id
    payload = {
        "model": effective_model_id,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": int(os.getenv("VLM_MAX_TOKENS", "512")),
        "temperature": float(os.getenv("VLM_TEMPERATURE", "0.2")),
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(HF_INFERENCE_BASE_URL, headers=headers, json=payload)
        if response.is_error:
            raise RuntimeError(
                f"Hugging Face serverless HTTP {response.status_code}: {response.text[:1000]}"
            )
        data = response.json()

    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(f"Hugging Face returned no choices: {data}")
    message = choices[0].get("message", {}).get("content", "")
    if isinstance(message, list):
        message = " ".join(
            item.get("text", "") for item in message if isinstance(item, dict)
        )
    return str(message).strip()
