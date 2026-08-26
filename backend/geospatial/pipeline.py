"""High-level ingestion workflow for Member 2."""

from __future__ import annotations

from pathlib import Path

from .alignment_checker import check_alignment
from .dependencies import MissingDependencyError
from .exporter import create_pdf_report, write_ingest_manifest, write_metadata_json
from .metadata_extractor import read_asset_metadata
from .model_input_builder import build_combined_s1_s2_model_input, build_patch_model_input
from .modality_detector import detect_modality
from .models import AssetFormat, IngestedAsset, Modality
from .preview_generator import generate_preview


def ingest_asset(
    path: str | Path,
    output_dir: str | Path,
    *,
    generate_previews: bool = True,
    write_metadata: bool = True,
    generate_model_input: bool = False,
    model_version: str = "v0.2.0",
) -> IngestedAsset:
    """Read, classify, normalize-preview, and export metadata for one asset."""

    p = Path(path)
    out_dir = Path(output_dir)
    errors: list[str] = []

    metadata = read_asset_metadata(p)
    modality = detect_modality(metadata)
    preview = None
    model_input = None

    if generate_previews:
        preview_path = out_dir / "previews" / f"{p.stem}.png"
        try:
            preview = generate_preview(p, preview_path, metadata=metadata, modality=modality.modality)
        except (MissingDependencyError, ValueError) as exc:
            errors.append(str(exc))

    if write_metadata:
        write_metadata_json(metadata, out_dir / "metadata" / f"{p.stem}.json")

    if generate_model_input and metadata.format == AssetFormat.PATCH_FOLDER:
        sensor = _sensor_from_modality(modality.modality)
        if sensor:
            try:
                model_input = build_patch_model_input(
                    p,
                    out_dir / "model_inputs" / f"{p.stem}_{sensor}_{model_version}.npy",
                    sensor=sensor,
                    model_version=model_version,
                )
            except (MissingDependencyError, ValueError) as exc:
                errors.append(str(exc))

    return IngestedAsset(
        metadata=metadata,
        modality=modality,
        preview=preview,
        model_input=model_input,
        errors=errors,
    )


def ingest_pair(
    paths: list[str | Path],
    output_dir: str | Path,
    *,
    generate_previews: bool = True,
    generate_pdf: bool = False,
    generate_model_inputs: bool = True,
    model_version: str = "v0.2.0",
) -> dict:
    """Ingest one or more assets and check pair alignment when two are present."""

    out_dir = Path(output_dir)
    assets = [
        ingest_asset(
            path,
            out_dir,
            generate_previews=generate_previews,
            generate_model_input=generate_model_inputs,
            model_version=model_version,
        )
        for path in paths
    ]

    alignment = None
    if len(assets) == 2:
        alignment = check_alignment(assets[0].metadata, assets[1].metadata)

    manifest = {
        "assets": [asset.to_dict() for asset in assets],
        "alignment": alignment.to_dict() if alignment else None,
        "combined_model_input": None,
    }

    if generate_model_inputs and len(assets) == 2:
        combined = _build_combined_model_input_if_possible(assets, out_dir, model_version)
        if combined:
            manifest["combined_model_input"] = combined.to_dict()

    if generate_pdf:
        try:
            manifest["pdf_report"] = create_pdf_report(assets, out_dir / "reports" / "ingestion_report.pdf")
        except MissingDependencyError as exc:
            manifest["pdf_report_error"] = str(exc)

    manifest["manifest_path"] = write_ingest_manifest(manifest, out_dir / "ingestion_manifest.json")
    return manifest


def _sensor_from_modality(modality: Modality) -> str | None:
    if modality == Modality.SAR:
        return "s1"
    if modality == Modality.MULTISPECTRAL:
        return "s2"
    return None


def _build_combined_model_input_if_possible(
    assets: list[IngestedAsset],
    output_dir: Path,
    model_version: str,
):
    if any(asset.metadata.format != AssetFormat.PATCH_FOLDER for asset in assets):
        return None

    s1_asset = next((asset for asset in assets if asset.modality.modality == Modality.SAR), None)
    s2_asset = next((asset for asset in assets if asset.modality.modality == Modality.MULTISPECTRAL), None)
    if not s1_asset or not s2_asset:
        return None

    try:
        return build_combined_s1_s2_model_input(
            s1_asset.metadata.path,
            s2_asset.metadata.path,
            output_dir / "model_inputs" / f"s1_s2_{model_version}.npy",
            model_version=model_version,
        )
    except (MissingDependencyError, ValueError) as exc:
        s1_asset.errors.append(str(exc))
        s2_asset.errors.append(str(exc))
        return None
