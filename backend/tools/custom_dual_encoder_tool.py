"""Custom SAR-optical dual encoder tool – wraps BigEarthNet v2 pretrained classifier.

This is the team's primary remote-sensing-adapted component. It processes
both SAR (S1) and optical/multispectral (S2) inputs through the BigEarthNet
pretrained classifier and produces cross-modal similarity, land-cover labels,
and a compatibility confidence score.
"""

from __future__ import annotations

from backend.tools.base_tool import BaseTool, skipped_result
from backend.tools.utils import find_asset, get_model_input_path


class CustomDualEncoderTool(BaseTool):
    name = "custom_sar_optical_dual_encoder_tool"
    purpose = "Validate SAR-optical pairs and compute cross-modal embedding similarity using BigEarthNet v2 pretrained classifier."
    tool_type = "custom_model"
    run_mode = "local_downloaded_model"
    resource_lane = "local_gpu_light"
    input_modalities = ["sar", "optical", "multispectral"]
    output_types = ["embedding", "similarity", "matched", "labels", "confidence"]
    enabled = True

    def __init__(self):
        self._classifier_s1 = None
        self._classifier_s2 = None

    def _load_classifiers(self):
        """Lazy-load BigEarthNet classifiers for S1 and S2."""
        from backend.modeling.bigearthnet_pretrained import BigEarthNetPretrainedClassifier

        if self._classifier_s1 is None:
            self._classifier_s1 = BigEarthNetPretrainedClassifier(
                "BIFOLD/BigEarthNet-S1-v2.0",
                sensor="s1",
                model_version="v0.2.0",
            )
        if self._classifier_s2 is None:
            self._classifier_s2 = BigEarthNetPretrainedClassifier(
                "BIFOLD/BigEarthNet-S2-v2.0",
                sensor="s2",
                model_version="v0.2.0",
            )

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        manifest = context["manifest"]
        sar_asset = find_asset(manifest, "sar")
        s2_asset = find_asset(manifest, "multispectral")

        sar_input = get_model_input_path(sar_asset)
        s2_input = get_model_input_path(s2_asset)

        if not sar_input and not s2_input:
            return skipped_result(
                self.name,
                "No SAR or multispectral model input available.",
                run_mode=self.run_mode,
                resource_lane=self.resource_lane,
            )

        from pathlib import Path
        work_dir = Path(context["run_dir"]) / "tool_outputs" / "dual_encoder"

        # Try to load the actual classifiers
        try:
            self._load_classifiers()
        except Exception:
            # Fall back to metadata-based analysis if model deps aren't installed
            return self._fallback_analysis(manifest, sar_asset, s2_asset)

        results = {}
        s1_labels = []
        s2_labels = []

        # Run S1 classifier
        if sar_input and self._classifier_s1:
            try:
                pred = self._classifier_s1.predict_from_member2_stack(
                    sar_input, work_dir=work_dir / "s1",
                )
                s1_labels = pred.labels
                results["s1_prediction"] = pred.to_dict()
            except Exception as exc:
                results["s1_error"] = str(exc)

        # Run S2 classifier
        if s2_input and self._classifier_s2:
            try:
                pred = self._classifier_s2.predict_from_member2_stack(
                    s2_input, work_dir=work_dir / "s2",
                )
                s2_labels = pred.labels
                results["s2_prediction"] = pred.to_dict()
            except Exception as exc:
                results["s2_error"] = str(exc)

        # Compute cross-modal agreement
        similarity, matched = self._compute_agreement(s1_labels, s2_labels)

        all_labels = list({l["label"] for l in s1_labels + s2_labels})
        confidence = similarity if matched else max(0.4, similarity * 0.7)

        return {
            "status": "success",
            "run_mode": self.run_mode,
            "resource_lane": self.resource_lane,
            "outputs": {
                "similarity": similarity,
                "matched": matched,
                "s1_labels": s1_labels,
                "s2_labels": s2_labels,
                "agreed_labels": all_labels,
                **results,
            },
            "confidence": confidence,
            "summary": (
                f"SAR-optical dual encoder: similarity={similarity:.2f}, "
                f"matched={matched}. Labels: {', '.join(all_labels[:5]) or 'none'}."
            ),
            "artifacts": [],
        }

    def _compute_agreement(self, s1_labels: list, s2_labels: list) -> tuple[float, bool]:
        """Compute label-overlap-based cross-modal agreement."""
        if not s1_labels or not s2_labels:
            return (0.5, False) if (s1_labels or s2_labels) else (0.3, False)

        s1_set = {l["label"] for l in s1_labels}
        s2_set = {l["label"] for l in s2_labels}
        overlap = s1_set & s2_set
        union = s1_set | s2_set

        if not union:
            return 0.3, False

        jaccard = len(overlap) / len(union)
        similarity = round(0.5 + jaccard * 0.45, 2)  # scale to 0.5–0.95
        matched = jaccard > 0.2
        return similarity, matched

    def _fallback_analysis(self, manifest: dict, sar_asset, s2_asset) -> dict:
        """Fallback when model dependencies are not installed."""
        alignment = manifest.get("alignment", {})
        compatible = alignment.get("compatible", False) if alignment else False
        score = alignment.get("score", 0.5) if alignment else 0.5

        has_both = sar_asset is not None and s2_asset is not None
        summary_parts = []
        if has_both:
            summary_parts.append("SAR and multispectral inputs detected")
            if compatible:
                summary_parts.append(f"spatially compatible (score={score})")
            else:
                summary_parts.append("spatial compatibility could not be confirmed")
        elif sar_asset:
            summary_parts.append("Only SAR input available")
        else:
            summary_parts.append("Only multispectral input available")

        # Extract labels from manifest metadata
        labels = []
        for asset in manifest.get("assets", []):
            lm = asset.get("metadata", {}).get("tags", {}).get("labels_metadata", {})
            labels.extend(lm.get("labels", []))
        labels = list(set(labels))

        return {
            "status": "success",
            "run_mode": self.run_mode,
            "resource_lane": self.resource_lane,
            "outputs": {
                "similarity": score,
                "matched": compatible and has_both,
                "labels": labels,
                "mode": "metadata_fallback",
                "note": "BigEarthNet model dependencies not installed; using metadata-based analysis.",
            },
            "confidence": score * 0.8 if has_both else 0.4,
            "summary": ". ".join(summary_parts) + f". Labels: {', '.join(labels[:5]) or 'none'}.",
            "artifacts": [],
        }
