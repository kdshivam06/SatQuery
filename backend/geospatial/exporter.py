"""Export helpers for ingestion artifacts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .dependencies import require_module
from .models import AssetMetadata, IngestedAsset


def write_metadata_json(metadata: AssetMetadata, output_path: str | Path) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(metadata.to_dict(), indent=2), encoding="utf-8")
    return str(out)


def write_ingest_manifest(data: dict[str, Any], output_path: str | Path) -> str:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return str(out)


def export_geotiff_copy(source_path: str | Path, output_path: str | Path) -> str:
    """Copy a source GeoTIFF/TIFF while preserving bytes and metadata."""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, out)
    return str(out)


def create_pdf_report(
    assets: list[IngestedAsset],
    output_path: str | Path,
    *,
    title: str = "SatQuery AI Ingestion Report",
) -> str:
    """Create a simple PDF report from preview images and metadata.

    Pillow can write PDF files directly, which keeps the prototype dependency
    surface small. The JSON manifest remains the canonical machine-readable
    report for backend integration.
    """

    Image = require_module("PIL.Image", "Pillow")
    ImageDraw = require_module("PIL.ImageDraw", "Pillow")
    ImageFont = require_module("PIL.ImageFont", "Pillow")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    pages = []
    for asset in assets:
        page = Image.new("RGB", (1240, 1754), "white")
        draw = ImageDraw.Draw(page)
        font = ImageFont.load_default()
        y = 60
        draw.text((60, y), title, fill="black", font=font)
        y += 50
        draw.text((60, y), f"File: {asset.metadata.filename}", fill="black", font=font)
        y += 28
        draw.text((60, y), f"Format: {asset.metadata.format.value}", fill="black", font=font)
        y += 28
        draw.text(
            (60, y),
            f"Modality: {asset.modality.modality.value} ({asset.modality.confidence:.2f})",
            fill="black",
            font=font,
        )
        y += 28
        draw.text((60, y), f"Size: {asset.metadata.width} x {asset.metadata.height}", fill="black", font=font)
        y += 28
        draw.text((60, y), f"Bands: {asset.metadata.band_count}", fill="black", font=font)
        y += 28
        draw.text((60, y), f"CRS: {asset.metadata.crs or 'not available'}", fill="black", font=font)
        y += 50

        if asset.preview:
            with Image.open(asset.preview.preview_path) as preview:
                preview = preview.convert("RGB")
                preview.thumbnail((900, 900))
                page.paste(preview, (60, y))

        pages.append(page)

    if not pages:
        pages.append(Image.new("RGB", (1240, 1754), "white"))

    first, rest = pages[0], pages[1:]
    first.save(out, "PDF", resolution=100.0, save_all=True, append_images=rest)
    return str(out)
