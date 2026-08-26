"""Metadata extraction for GeoTIFF/TIFF and common image inputs."""

from __future__ import annotations

from pathlib import Path

from .dependencies import require_module
from .models import AssetFormat, AssetMetadata, BandInfo, RasterBounds, RasterTransform


GEOTIFF_EXTENSIONS = {".tif", ".tiff", ".geotiff", ".gtiff"}
PNG_EXTENSIONS = {".png"}
JPEG_EXTENSIONS = {".jpg", ".jpeg"}


def infer_asset_format(path: str | Path) -> AssetFormat:
    path = Path(path)
    if path.is_dir():
        return AssetFormat.PATCH_FOLDER
    suffix = path.suffix.lower()
    if suffix in {".geotiff", ".gtiff"}:
        return AssetFormat.GEOTIFF
    if suffix in {".tif", ".tiff"}:
        return AssetFormat.TIFF
    if suffix in PNG_EXTENSIONS:
        return AssetFormat.PNG
    if suffix in JPEG_EXTENSIONS:
        return AssetFormat.JPEG
    return AssetFormat.UNKNOWN


def read_asset_metadata(path: str | Path) -> AssetMetadata:
    """Read metadata for a supported image path.

    GeoTIFF and TIFF files use rasterio so CRS, transform, bounds, nodata, and
    band details are preserved. PNG/JPEG files use Pillow and intentionally
    return no CRS metadata.
    """

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input asset does not exist: {path}")

    asset_format = infer_asset_format(path)
    if asset_format == AssetFormat.PATCH_FOLDER:
        from .patch_folder import read_patch_folder_metadata

        return read_patch_folder_metadata(path)
    if asset_format in {AssetFormat.GEOTIFF, AssetFormat.TIFF}:
        return read_geotiff_metadata(path, asset_format)
    if asset_format in {AssetFormat.PNG, AssetFormat.JPEG}:
        return read_pil_image_metadata(path, asset_format)
    return AssetMetadata.from_path(path, AssetFormat.UNKNOWN)


def read_geotiff_metadata(
    path: str | Path,
    asset_format: AssetFormat | None = None,
) -> AssetMetadata:
    rasterio = require_module("rasterio", "rasterio")
    p = Path(path)
    metadata = AssetMetadata.from_path(p, asset_format or infer_asset_format(p))

    with rasterio.open(p) as src:
        metadata.width = int(src.width)
        metadata.height = int(src.height)
        metadata.band_count = int(src.count)
        metadata.dtypes = [str(dtype) for dtype in src.dtypes]
        metadata.crs = src.crs.to_string() if src.crs else None
        metadata.bounds = RasterBounds(
            left=float(src.bounds.left),
            bottom=float(src.bounds.bottom),
            right=float(src.bounds.right),
            top=float(src.bounds.top),
        )
        metadata.transform = RasterTransform(tuple(float(v) for v in src.transform[:6]))
        metadata.resolution = (float(abs(src.res[0])), float(abs(src.res[1])))
        metadata.nodata = src.nodata
        metadata.band_descriptions = list(src.descriptions)
        metadata.tags = dict(src.tags())
        metadata.bands = [
            BandInfo(
                index=i,
                dtype=str(src.dtypes[i - 1]),
                description=src.descriptions[i - 1],
                nodata=src.nodata,
            )
            for i in range(1, src.count + 1)
        ]

    return metadata


def read_pil_image_metadata(path: str | Path, asset_format: AssetFormat) -> AssetMetadata:
    Image = require_module("PIL.Image", "Pillow")
    p = Path(path)
    metadata = AssetMetadata.from_path(p, asset_format)

    with Image.open(p) as image:
        metadata.width, metadata.height = image.size
        metadata.band_count = len(image.getbands())
        metadata.dtypes = [str(image.mode)]
        metadata.band_descriptions = list(image.getbands())

    return metadata
