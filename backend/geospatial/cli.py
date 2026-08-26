"""Command-line entry point for SatQuery AI ingestion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import ingest_pair


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest remote-sensing assets for SatQuery AI.")
    parser.add_argument("inputs", nargs="+", help="GeoTIFF/TIFF/PNG/JPEG files to ingest.")
    parser.add_argument(
        "--output-dir",
        default="runs/ingestion",
        help="Directory where previews, metadata, and manifests are written.",
    )
    parser.add_argument(
        "--no-previews",
        action="store_true",
        help="Skip PNG preview generation.",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Also write a simple PDF report when Pillow is installed.",
    )
    parser.add_argument(
        "--no-model-inputs",
        action="store_true",
        help="Skip model-ready .npy stack export for patch-folder inputs.",
    )
    parser.add_argument(
        "--model-version",
        default="v0.2.0",
        help="BigEarthNet pretrained model version band contract.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir)
    result = ingest_pair(
        args.inputs,
        output_dir,
        generate_previews=not args.no_previews,
        generate_pdf=args.pdf,
        generate_model_inputs=not args.no_model_inputs,
        model_version=args.model_version,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
