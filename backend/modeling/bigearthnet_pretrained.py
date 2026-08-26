"""Optional BigEarthNet v2 pretrained model wrapper.

This wrapper deliberately keeps heavy dependencies optional. It can be imported
without PyTorch, ConfigILM, or the official reBEN code installed; loading the
real model fails with an explicit setup message instead of breaking ingestion.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.geospatial.dependencies import MissingDependencyError, require_module
from backend.modeling.bigearthnet_adapter import prepare_bigearthnet_input


BIGEARTHNET_19_CLASSES = [
    "Agro-forestry areas",
    "Arable land",
    "Beaches, dunes, sands",
    "Broad-leaved forest",
    "Coastal wetlands",
    "Complex cultivation patterns",
    "Coniferous forest",
    "Industrial or commercial units",
    "Inland waters",
    "Inland wetlands",
    "Land principally occupied by agriculture, with significant areas of natural vegetation",
    "Marine waters",
    "Mixed forest",
    "Moors, heathland and sclerophyllous vegetation",
    "Natural grassland and sparsely vegetated areas",
    "Pastures",
    "Permanent crops",
    "Transitional woodland, shrub",
    "Urban fabric",
]


@dataclass(slots=True)
class Prediction:
    labels: list[dict[str, float | str]]
    logits_shape: tuple[int, ...]
    prepared_tensor_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "labels": self.labels,
            "logits_shape": self.logits_shape,
            "prepared_tensor_path": self.prepared_tensor_path,
        }


class BigEarthNetPretrainedClassifier:
    """Thin wrapper around official BIFOLD BigEarthNet v2 pretrained classifiers."""

    def __init__(
        self,
        model_name_or_path: str,
        *,
        sensor: str,
        model_version: str = "v0.2.0",
        target_size: int = 224,
        threshold: float = 0.5,
    ):
        self.model_name_or_path = model_name_or_path
        self.sensor = sensor
        self.model_version = model_version
        self.target_size = target_size
        self.threshold = threshold
        self.model = None

    def load(self) -> None:
        """Load the official model when its dependency package is installed."""

        torch = require_module("torch", "torch")
        try:
            model_module = require_module("reben_publication.BigEarthNetv2_0_ImageClassifier")
        except MissingDependencyError as exc:
            raise MissingDependencyError(
                "Official reBEN model code is required to load BigEarthNet v2 pretrained weights. "
                "Install the official BigEarthNet v2/reBEN repository code and ConfigILM, then retry."
            ) from exc

        classifier = model_module.BigEarthNetv2_0_ImageClassifier
        self.model = classifier.from_pretrained(self.model_name_or_path)
        self.model.eval()
        if torch.cuda.is_available():
            self.model.cuda()

    def predict_from_member2_stack(
        self,
        source_npy_path: str | Path,
        *,
        work_dir: str | Path,
    ) -> Prediction:
        """Prepare a Member 2 stack and run multi-label classification."""

        if self.model is None:
            self.load()

        torch = require_module("torch", "torch")
        prepared = prepare_bigearthnet_input(
            source_npy_path,
            Path(work_dir) / "prepared_for_bigearthnet.npy",
            sensor=self.sensor,
            model_version=self.model_version,
            target_size=self.target_size,
        )

        np = require_module("numpy", "numpy")
        array = np.load(prepared.tensor_path)
        tensor = torch.from_numpy(array)
        if torch.cuda.is_available():
            tensor = tensor.cuda()

        with torch.no_grad():
            outputs = self.model(tensor)

        logits = outputs.logits if hasattr(outputs, "logits") else outputs
        probabilities = torch.sigmoid(logits).detach().cpu().numpy()[0]
        labels = [
            {"label": label, "score": float(score)}
            for label, score in zip(BIGEARTHNET_19_CLASSES, probabilities)
            if float(score) >= self.threshold
        ]
        labels.sort(key=lambda item: item["score"], reverse=True)

        return Prediction(
            labels=labels,
            logits_shape=tuple(int(value) for value in logits.shape),
            prepared_tensor_path=prepared.tensor_path,
        )
