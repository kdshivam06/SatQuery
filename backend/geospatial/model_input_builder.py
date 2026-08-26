"""Build model-ready NumPy arrays from real remote-sensing patch folders."""

from __future__ import annotations

import json
from pathlib import Path

from .band_mapper import get_bigearthnet_pretrained_band_order
from .dependencies import require_module
from .image_normalizer import percentile_clip_normalize
from .models import ModelInputResult
from .patch_folder import discover_band_files


def build_patch_model_input(
    patch_path: str | Path,
    output_path: str | Path,
    *,
    sensor: str,
    model_version: str = "v0.2.0",
    target_shape: tuple[int, int] | None = None,
    normalize: bool = True,
) -> ModelInputResult:
    """Export one patch folder as a channel-first `.npy` tensor."""

    band_order = get_bigearthnet_pretrained_band_order(sensor, model_version=model_version)
    return _build_stack_from_band_order(
        [(Path(patch_path), tuple(band_order))],
        output_path,
        sensor=sensor,
        model_version=model_version,
        target_shape=target_shape,
        normalize=normalize,
    )


def build_combined_s1_s2_model_input(
    s1_patch_path: str | Path,
    s2_patch_path: str | Path,
    output_path: str | Path,
    *,
    model_version: str = "v0.2.0",
    target_shape: tuple[int, int] | None = None,
    normalize: bool = True,
) -> ModelInputResult:
    """Export a combined S1+S2 channel-first `.npy` tensor."""

    s1_order = get_bigearthnet_pretrained_band_order("s1", model_version=model_version)
    s2_order = get_bigearthnet_pretrained_band_order("s2", model_version=model_version)
    return _build_stack_from_band_order(
        [(Path(s1_patch_path), tuple(s1_order)), (Path(s2_patch_path), tuple(s2_order))],
        output_path,
        sensor="s1_s2",
        model_version=model_version,
        target_shape=target_shape,
        normalize=normalize,
    )


def _build_stack_from_band_order(
    patch_specs: list[tuple[Path, tuple[str, ...]]],
    output_path: str | Path,
    *,
    sensor: str,
    model_version: str,
    target_shape: tuple[int, int] | None,
    normalize: bool,
) -> ModelInputResult:
    rasterio = require_module("rasterio", "rasterio")
    np = require_module("numpy", "numpy")
    Resampling = require_module("rasterio.enums", "rasterio").Resampling

    resolved_specs = []
    missing: list[str] = []
    for patch_path, band_order in patch_specs:
        band_files = discover_band_files(patch_path)
        for band_name in band_order:
            if band_name not in band_files:
                missing.append(f"{patch_path.name}:{band_name}")
        resolved_specs.append((patch_path, band_order, band_files))

    if missing:
        raise ValueError(f"Missing required bands for model input: {', '.join(missing)}")

    if target_shape is None:
        target_shape = _infer_target_shape(resolved_specs)

    arrays = []
    band_order_out: list[str] = []
    source_shapes: dict[str, tuple[int, int]] = {}

    for patch_path, band_order, band_files in resolved_specs:
        for band_name in band_order:
            with rasterio.open(band_files[band_name]) as src:
                source_shapes[f"{patch_path.name}:{band_name}"] = (int(src.height), int(src.width))
                array = src.read(
                    1,
                    out_shape=target_shape,
                    resampling=Resampling.bilinear,
                )
                if normalize:
                    array = percentile_clip_normalize(array, output_dtype="float32", nodata=src.nodata)
                else:
                    array = array.astype("float32")
                arrays.append(array)
                band_order_out.append(band_name)

    stack = np.stack(arrays, axis=0).astype("float32")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(out, stack)

    metadata_path = out.with_suffix(".json")
    metadata = {
        "model_input_path": str(out),
        "source_paths": [str(patch_path) for patch_path, _, _ in resolved_specs],
        "sensor": sensor,
        "model_version": model_version,
        "array_shape": list(stack.shape),
        "dtype": str(stack.dtype),
        "band_order": band_order_out,
        "normalization": {
            "enabled": normalize,
            "method": "per_band_percentile_clip",
            "lower_percentile": 2.0,
            "upper_percentile": 98.0,
        },
        "resampling": {
            "method": "bilinear",
            "target_shape": list(target_shape),
            "source_shapes": {key: list(value) for key, value in source_shapes.items()},
        },
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return ModelInputResult(
        model_input_path=str(out),
        metadata_path=str(metadata_path),
        source_path=";".join(str(patch_path) for patch_path, _, _ in resolved_specs),
        sensor=sensor,
        model_version=model_version,
        array_shape=tuple(int(value) for value in stack.shape),
        dtype=str(stack.dtype),
        band_order=band_order_out,
        normalization=metadata["normalization"],
        resampling=metadata["resampling"],
    )


def _infer_target_shape(resolved_specs) -> tuple[int, int]:
    rasterio = require_module("rasterio", "rasterio")

    preferred_bands = ("B02", "B03", "B04", "B08", "VV", "VH")
    for _, _, band_files in resolved_specs:
        for band_name in preferred_bands:
            if band_name in band_files:
                with rasterio.open(band_files[band_name]) as src:
                    return (int(src.height), int(src.width))

    _, band_order, band_files = resolved_specs[0]
    with rasterio.open(band_files[band_order[0]]) as src:
        return (int(src.height), int(src.width))
