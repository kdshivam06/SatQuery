"""Adapters between Member 2 `.npy` stacks and BigEarthNet pretrained models."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from backend.geospatial.band_mapper import get_bigearthnet_pretrained_band_order
from backend.geospatial.dependencies import require_module


@dataclass(slots=True)
class PreparedTensor:
    tensor_path: str
    metadata_path: str
    source_path: str
    sensor: str
    model_version: str
    shape: tuple[int, int, int, int]
    dtype: str
    band_order: list[str]
    transform: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def prepare_bigearthnet_input(
    source_npy_path: str | Path,
    output_path: str | Path,
    *,
    sensor: str,
    model_version: str = "v0.2.0",
    target_size: int = 224,
    normalization_profile: str = "identity_0_1",
) -> PreparedTensor:
    """Convert a channel-first stack into model-wrapper-ready batch format.

    Input shape: `(C, H, W)`.
    Output shape: `(1, C, target_size, target_size)`.
    """

    np = require_module("numpy", "numpy")
    source = Path(source_npy_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    array = np.load(source).astype("float32")
    if array.ndim != 3:
        raise ValueError(f"Expected channel-first input with shape (C,H,W), got {array.shape}.")

    expected_bands = list(get_bigearthnet_pretrained_band_order(sensor, model_version=model_version))
    if array.shape[0] != len(expected_bands):
        raise ValueError(
            f"{sensor} {model_version} expects {len(expected_bands)} channels "
            f"({expected_bands}), got {array.shape[0]} from {source}."
        )

    resized = resize_channel_first(array, target_size=target_size)
    normalized = apply_normalization_profile(resized, normalization_profile)
    batched = normalized[None, ...].astype("float32")
    np.save(output, batched)

    metadata_path = output.with_suffix(".json")
    metadata = {
        "tensor_path": str(output),
        "source_path": str(source),
        "sensor": sensor,
        "model_version": model_version,
        "shape": list(batched.shape),
        "dtype": str(batched.dtype),
        "band_order": expected_bands,
        "transform": {
            "input_layout": "C,H,W",
            "output_layout": "B,C,H,W",
            "target_size": target_size,
            "normalization_profile": normalization_profile,
        },
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return PreparedTensor(
        tensor_path=str(output),
        metadata_path=str(metadata_path),
        source_path=str(source),
        sensor=sensor,
        model_version=model_version,
        shape=tuple(int(value) for value in batched.shape),
        dtype=str(batched.dtype),
        band_order=expected_bands,
        transform=metadata["transform"],
    )


def resize_channel_first(array, *, target_size: int):
    """Resize `(C,H,W)` float32 arrays with bilinear interpolation."""

    np = require_module("numpy", "numpy")
    Image = require_module("PIL.Image", "Pillow")

    if array.shape[1:] == (target_size, target_size):
        return array.astype("float32")

    channels = []
    for channel in array:
        image = Image.fromarray(channel.astype("float32"), mode="F")
        image = image.resize((target_size, target_size), resample=Image.Resampling.BILINEAR)
        channels.append(np.asarray(image, dtype="float32"))
    return np.stack(channels, axis=0).astype("float32")


def apply_normalization_profile(array, profile: str):
    """Apply final model-wrapper normalization."""

    np = require_module("numpy", "numpy")
    arr = np.asarray(array, dtype="float32")

    if profile == "identity_0_1":
        return np.clip(arr, 0.0, 1.0).astype("float32")

    if profile == "per_channel_standardize":
        means = arr.mean(axis=(1, 2), keepdims=True)
        stds = arr.std(axis=(1, 2), keepdims=True)
        stds = np.where(stds < 1e-6, 1.0, stds)
        return ((arr - means) / stds).astype("float32")

    raise ValueError(f"Unsupported normalization profile: {profile}")
