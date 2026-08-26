"""PNG preview generation for raster and benchmark image inputs."""

from __future__ import annotations

from pathlib import Path

from .band_mapper import select_preview_bands
from .dependencies import require_module
from .image_normalizer import percentile_clip_normalize
from .metadata_extractor import infer_asset_format
from .models import AssetFormat, AssetMetadata, Modality, PreviewResult


def generate_preview(
    path: str | Path,
    output_path: str | Path,
    *,
    metadata: AssetMetadata | None = None,
    modality: Modality | str = Modality.UNKNOWN,
    max_size: int = 1024,
) -> PreviewResult:
    """Create a displayable PNG preview from a supported image file."""

    asset_format = metadata.format if metadata else infer_asset_format(path)
    if asset_format == AssetFormat.PATCH_FOLDER:
        from .patch_folder import generate_patch_folder_preview

        return generate_patch_folder_preview(path, output_path, metadata=metadata, max_size=max_size)
    if asset_format in {AssetFormat.GEOTIFF, AssetFormat.TIFF}:
        return generate_raster_preview(
            path,
            output_path,
            metadata=metadata,
            modality=modality,
            max_size=max_size,
        )
    if asset_format in {AssetFormat.PNG, AssetFormat.JPEG}:
        return generate_standard_image_preview(path, output_path, max_size=max_size)
    raise ValueError(f"Cannot generate preview for unsupported format: {asset_format.value}")


def generate_raster_preview(
    path: str | Path,
    output_path: str | Path,
    *,
    metadata: AssetMetadata | None = None,
    modality: Modality | str = Modality.UNKNOWN,
    max_size: int = 1024,
) -> PreviewResult:
    rasterio = require_module("rasterio", "rasterio")
    np = require_module("numpy", "numpy")
    Image = require_module("PIL.Image", "Pillow")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    selected_bands = select_preview_bands(metadata, modality) if metadata else []
    normalization = {
        "method": "percentile_clip",
        "lower_percentile": 2.0,
        "upper_percentile": 98.0,
    }

    with rasterio.open(path) as src:
        if not selected_bands:
            selected_bands = [1, 2, 3] if src.count >= 3 else [1]

        selected_bands = [min(max(index, 1), src.count) for index in selected_bands]
        raw_bands = [src.read(index) for index in selected_bands]
        norm_bands = [
            percentile_clip_normalize(band, output_dtype="uint8", nodata=src.nodata)
            for band in raw_bands
        ]

        if len(norm_bands) == 1:
            image_array = norm_bands[0]
            mode = "L"
        else:
            while len(norm_bands) < 3:
                norm_bands.append(norm_bands[-1])
            image_array = np.stack(norm_bands[:3], axis=-1)
            mode = "RGB"

    image = Image.fromarray(image_array, mode=mode)
    image.thumbnail((max_size, max_size))
    image.save(out, format="PNG")

    return PreviewResult(
        preview_path=str(out),
        source_path=str(path),
        width=image.width,
        height=image.height,
        selected_bands=selected_bands,
        normalization=normalization,
    )


def generate_standard_image_preview(
    path: str | Path,
    output_path: str | Path,
    *,
    max_size: int = 1024,
) -> PreviewResult:
    Image = require_module("PIL.Image", "Pillow")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((max_size, max_size))
        image.save(out, format="PNG")
        width, height = image.size

    return PreviewResult(
        preview_path=str(out),
        source_path=str(path),
        width=width,
        height=height,
        selected_bands=[1, 2, 3],
        normalization={"method": "source_rgb_thumbnail"},
    )
