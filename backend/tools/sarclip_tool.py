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

        labels = params.get("labels", [])
        if not labels:
            # Try to extract labels from user query
            labels = _extract_labels_from_query(context.get("query", ""))
        if not labels:
            labels = ["water", "urban", "cropland", "forest", "bare soil", "wetland"]

        try:
            import base64
            from backend.geospatial.dependencies import require_module
            httpx = require_module("httpx", "httpx")

            with open(preview, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            hf_token = os.getenv("HF_TOKEN", "")
            headers = {}
            if hf_token:
                headers["Authorization"] = f"Bearer {hf_token}"
            headers["Content-Type"] = "application/json"

            # HuggingFace Inference Endpoint format for zero-shot-image-classification
            payload = {
                "inputs": img_b64,
                "parameters": {"candidate_labels": labels},
            }

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    SARCLIP_ENDPOINT,
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            # HF zero-shot returns a list of {label, score} dicts
            # Normalize to our internal format and strip "SAR image of " prefix
            if isinstance(data, list):
                scores = {}
                for item in data:
                    clean_label = item["label"].replace("SAR image of ", "").strip()
                    scores[clean_label] = item["score"]
                best = list(scores.keys())[0] if scores else ""
                top_score = list(scores.values())[0] if scores else 0.5
            else:
                scores = data.get("scores", data.get("text_scores", {}))
                best = data.get("best_label", "")
                top_score = max(scores.values()) if scores else 0.5

            answer = _format_sarclip_answer(list(scores.keys()), scores, best)

            return {
                "status": "success", "run_mode": self.run_mode, "resource_lane": self.resource_lane,
                "outputs": {"scores": scores, "best_label": best, "answer": answer},
                "confidence": round(min(top_score + 0.1, 1.0), 2),
                "summary": f"SARCLIP: {answer[:200]}",
                "artifacts": [],
            }
        except Exception as exc:
            return skipped_result(self.name, f"SARCLIP call failed: {exc}", run_mode=self.run_mode, resource_lane=self.resource_lane)


def _extract_labels_from_query(query: str) -> list[str]:
    """Extract candidate labels from a user query like 'using the labels: urban, water, arable land'."""
    import re
    q = query.lower()
    # Match patterns like "labels: X, Y, Z" or "labels X, Y, or Z"
    match = re.search(r"labels?[:\s]+(.+?)(?:\.|$)", q)
    if match:
        raw = match.group(1)
        # Split on commas and 'or'
        parts = re.split(r",\s*|\s+or\s+|\s+and\s+", raw)
        return [p.strip() for p in parts if p.strip()]
    return []


def _format_sarclip_answer(labels: list[str], scores: dict, best_label: str) -> str:
    """Format SARCLIP scores into a readable answer."""
    if not scores and best_label:
        return f"SARCLIP zero-shot classification: best match is '{best_label}'."

    if isinstance(scores, dict):
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    elif isinstance(scores, list) and len(scores) == len(labels):
        sorted_scores = sorted(zip(labels, scores), key=lambda x: x[1], reverse=True)
    else:
        return f"SARCLIP scored SAR against {len(labels)} text labels."

    parts = []
    for label, score in sorted_scores:
        pct = score * 100 if isinstance(score, float) and score <= 1 else score
        parts.append(f"{label} ({pct:.0f}%)")

    top = sorted_scores[0]
    top_pct = top[1] * 100 if isinstance(top[1], float) and top[1] <= 1 else top[1]
    return f"SARCLIP zero-shot classification: best match is '{top[0]}' with {top_pct:.0f}% confidence. All scores: {', '.join(parts)}."

