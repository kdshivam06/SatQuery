"""Select and optionally ingest a real S1/S2 pair from benv1_14k."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.geospatial.benv1_selector import list_benv1_pairs, select_benv1_pair
from backend.geospatial.pipeline import ingest_pair


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Select a real benv1_14k S1/S2 pair.")
    parser.add_argument(
        "--dataset-root",
        default="data/raw/real_samples/benv1_14k",
        help="Path to the benv1_14k root containing s1, s2, and master labels CSV.",
    )
    parser.add_argument("--index", type=int, help="Row index from the master labels CSV.")
    parser.add_argument("--s1-id", help="Specific Sentinel-1 patch ID.")
    parser.add_argument("--s2-id", help="Specific Sentinel-2 patch ID.")
    parser.add_argument("--list", type=int, metavar="N", help="List the first N pairs.")
    parser.add_argument("--ingest", action="store_true", help="Run Member 2 ingestion for the selected pair.")
    parser.add_argument(
        "--output-dir",
        default="runs/benv1_selected_pair",
        help="Output directory used with --ingest.",
    )
    parser.add_argument("--pdf", action="store_true", help="Generate PDF report when using --ingest.")
    parser.add_argument(
        "--no-model-inputs",
        action="store_true",
        help="Skip model-ready .npy stack export when using --ingest.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list is not None:
        pairs = [pair.to_dict() for pair in list_benv1_pairs(args.dataset_root, limit=args.list)]
        print(json.dumps(pairs, indent=2))
        return 0

    pair = select_benv1_pair(
        args.dataset_root,
        index=args.index,
        s1_id=args.s1_id,
        s2_id=args.s2_id,
    )

    result = pair.to_dict()
    if args.ingest:
        result["ingestion"] = ingest_pair(
            [pair.s1_path, pair.s2_path],
            args.output_dir,
            generate_pdf=args.pdf,
            generate_model_inputs=not args.no_model_inputs,
        )

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
