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


def build_raster_model_input(
    raster_path: str | Path,
    output_path: str | Path,
    *,
    sensor: str,
    modality: str,
    model_version: str = "v0.2.0",
    target_shape: tuple[int, int] | None = None,
    normalize: bool = True,
) -> ModelInputResult:
    """Export a multi-band GeoTIFF/TIFF as a channel-first .npy tensor.

    Maps raster bands to BigEarthNet expected names based on modality and band count.
    For SAR: bands are mapped to (VV, VH) in order.
    For multispectral: bands are mapped to the BigEarthNet S2 order by position.
    """

    rasterio = require_module("rasterio", "rasterio")
    np = require_module("numpy", "numpy")
    Resampling = require_module("rasterio.enums", "rasterio").Resampling

    p = Path(raster_path)
    band_order = list(get_bigearthnet_pretrained_band_order(sensor, model_version=model_version))

    with rasterio.open(p) as src:
        src_count = src.count

        # Try to read band descriptions from the raster
        descriptions = list(src.descriptions) if src.descriptions else []
        # Clean up empty/None descriptions
        descriptions = [d if d else "" for d in descriptions]

        # Build a mapping from raster band index (1-based) to named band
        band_mapping = _map_raster_bands_to_names(src_count, descriptions, modality, band_order)

        # Determine target shape
        if target_shape is None:
            target_shape = (int(src.height), int(src.width))

        arrays = []
        mapped_band_order = []
        source_shapes: dict[str, tuple[int, int]] = {}

        for band_name in band_order:
            src_index = band_mapping.get(band_name)
            if src_index is None:
                continue  # Skip bands not available in the raster

            source_shapes[band_name] = (int(src.height), int(src.width))
            array = src.read(
                src_index,
                out_shape=target_shape,
                resampling=Resampling.bilinear,
            )
            if normalize:
                array = percentile_clip_normalize(array, output_dtype="float32", nodata=src.nodata)
            else:
                array = array.astype("float32")
            arrays.append(array)
            mapped_band_order.append(band_name)

    if not arrays:
        raise ValueError(
            f"No matching bands found in raster for {sensor} modality. "
            f"Raster has {src_count} bands, descriptions={descriptions}."
        )

    stack = np.stack(arrays, axis=0).astype("float32")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(out, stack)

    metadata_path = out.with_suffix(".json")
    metadata = {
        "model_input_path": str(out),
        "source_paths": [str(p)],
        "sensor": sensor,
        "model_version": model_version,
        "array_shape": list(stack.shape),
        "dtype": str(stack.dtype),
        "band_order": mapped_band_order,
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
        source_path=str(p),
        sensor=sensor,
        model_version=model_version,
        array_shape=tuple(int(value) for value in stack.shape),
        dtype=str(stack.dtype),
        band_order=mapped_band_order,
        normalization=metadata["normalization"],
        resampling=metadata["resampling"],
    )


def _map_raster_bands_to_names(
    src_count: int,
    descriptions: list[str],
    modality: str,
    target_bands: list[str],
) -> dict[str, int]:
    """Map raster band indices (1-based) to named bands.

    Strategy:
    1. Try to match by band description (e.g., 'VV', 'B04')
    2. Fall back to positional mapping based on modality and band count
    """

    # First, try to match by description
    desc_map: dict[str, int] = {}
    for idx, desc in enumerate(descriptions, start=1):
        normalized = desc.upper().strip()
        if normalized in target_bands:
            desc_map[normalized] = idx

    if len(desc_map) >= len(target_bands):
        return desc_map

    # Check if any descriptions are useful
    has_useful_descriptions = any(
        d.upper().strip() in {"VV", "VH", "HH", "HV"}
        or (d.upper().strip().startswith("B") and d.upper().strip()[1:].replace("A", "").isdigit())
        for d in descriptions
    )

    if has_useful_descriptions:
        # Use description-based mapping even if partial
        return desc_map

    # Fall back to positional mapping
    return _positional_band_mapping(src_count, modality, target_bands)


def _positional_band_mapping(
    src_count: int,
    modality: str,
    target_bands: list[str],
) -> dict[str, int]:
    """Map raster bands by position based on modality and band count."""

    mapping: dict[str, int] = {}

    if modality == "sar":
        # Standard S1 GRD: band 1 = VV, band 2 = VH
        if src_count >= 2:
            mapping["VV"] = 1
            mapping["VH"] = 2
        elif src_count == 1:
            mapping["VV"] = 1

    elif modality in ("multispectral", "optical"):
        # Standard Sentinel-2 L2A band order (10 bands):
        # B01, B02, B03, B04, B05, B06, B07, B08, B8A, B11
        s2_full_order = [
            "B01", "B02", "B03", "B04", "B05",
            "B06", "B07", "B08", "B8A", "B11",
        ]
        if src_count == 10:
            for idx, band_name in enumerate(s2_full_order, start=1):
                if band_name in target_bands:
                    mapping[band_name] = idx
        elif src_count >= 4:
            # Likely B02, B03, B04, B08 (common subset)
            fallback_order = ["B02", "B03", "B04", "B08"]
            for idx, band_name in enumerate(fallback_order[:src_count], start=1):
                if band_name in target_bands:
                    mapping[band_name] = idx
        elif src_count >= 3:
            # Likely B02, B03, B04 (RGB)
            fallback_order = ["B02", "B03", "B04"]
            for idx, band_name in enumerate(fallback_order[:src_count], start=1):
                if band_name in target_bands:
                    mapping[band_name] = idx

    return mapping


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
