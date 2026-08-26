"""Controlled dataset downloader for SatQuery AI prototype assets."""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATA_DIR = Path("data/raw")


@dataclass(frozen=True, slots=True)
class DownloadItem:
    name: str
    url: str
    output_path: Path
    size_hint: str


DOWNLOADS = {
    "ben-txt": [
        DownloadItem(
            name="BigEarthNet.txt annotations parquet",
            url="https://huggingface.co/datasets/BIFOLD-BigEarthNetv2-0/BigEarthNet.txt/resolve/main/BigEarthNet.txt.parquet?download=true",
            output_path=Path("bigearthnet_txt/BigEarthNet.txt.parquet"),
            size_hint="about 467 MB",
        ),
    ],
    "vrsbench-eval": [
        DownloadItem(
            name="VRSBench caption eval JSON",
            url="https://huggingface.co/datasets/xiang709/VRSBench/resolve/main/VRSBench_EVAL_Cap.json?download=true",
            output_path=Path("vrsbench/VRSBench_EVAL_Cap.json"),
            size_hint="about 4.8 MB",
        ),
        DownloadItem(
            name="VRSBench referring eval JSON",
            url="https://huggingface.co/datasets/xiang709/VRSBench/resolve/main/VRSBench_EVAL_referring.json?download=true",
            output_path=Path("vrsbench/VRSBench_EVAL_referring.json"),
            size_hint="about 10.3 MB",
        ),
        DownloadItem(
            name="VRSBench VQA eval JSON",
            url="https://huggingface.co/datasets/xiang709/VRSBench/resolve/main/VRSBench_EVAL_vqa.json?download=true",
            output_path=Path("vrsbench/VRSBench_EVAL_vqa.json"),
            size_hint="about 9.4 MB",
        ),
    ],
    "vrsbench-train-annotations": [
        DownloadItem(
            name="VRSBench train JSON",
            url="https://huggingface.co/datasets/xiang709/VRSBench/resolve/main/VRSBench_train.json?download=true",
            output_path=Path("vrsbench/VRSBench_train.json"),
            size_hint="about 64.9 MB",
        ),
        DownloadItem(
            name="VRSBench train annotations zip",
            url="https://huggingface.co/datasets/xiang709/VRSBench/resolve/main/Annotations_train.zip?download=true",
            output_path=Path("vrsbench/Annotations_train.zip"),
            size_hint="about 28.6 MB",
        ),
        DownloadItem(
            name="VRSBench val annotations zip",
            url="https://huggingface.co/datasets/xiang709/VRSBench/resolve/main/Annotations_val.zip?download=true",
            output_path=Path("vrsbench/Annotations_val.zip"),
            size_hint="about 12.8 MB",
        ),
    ],
    "vrsbench-val-images": [
        DownloadItem(
            name="VRSBench validation images zip",
            url="https://huggingface.co/datasets/xiang709/VRSBench/resolve/main/Images_val.zip?download=true",
            output_path=Path("vrsbench/Images_val.zip"),
            size_hint="about 4.0 GB",
        ),
    ],
}

DOWNLOADS["prototype-small"] = DOWNLOADS["ben-txt"] + DOWNLOADS["vrsbench-eval"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download SatQuery AI dataset assets.")
    parser.add_argument(
        "--preset",
        choices=sorted(DOWNLOADS),
        default="prototype-small",
        help="Dataset group to download.",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="Root output directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Download even when the target file already exists.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data_dir = Path(args.data_dir)
    for item in DOWNLOADS[args.preset]:
        target = data_dir / item.output_path
        download_file(item, target, overwrite=args.overwrite)
    return 0


def download_file(item: DownloadItem, target: Path, *, overwrite: bool = False) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        print(f"skip: {target} already exists")
        return

    temp_path = target.with_suffix(target.suffix + ".part")
    print(f"download: {item.name} ({item.size_hint})")
    print(f"source:   {item.url}")
    print(f"target:   {target}")

    request = urllib.request.Request(item.url, headers={"User-Agent": "SatQueryAI/0.1"})
    started = time.monotonic()
    downloaded = 0

    try:
        with urllib.request.urlopen(request) as response, temp_path.open("wb") as handle:
            total = int(response.headers.get("Content-Length") or 0)
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                _print_progress(downloaded, total, started)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Download failed with HTTP {exc.code}: {item.url}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Download failed: {exc.reason}") from exc

    temp_path.replace(target)
    print(f"\ndone: {target}")


def _print_progress(downloaded: int, total: int, started: float) -> None:
    elapsed = max(time.monotonic() - started, 0.001)
    rate_mib = downloaded / 1024 / 1024 / elapsed
    if total:
        pct = downloaded * 100 / total
        message = f"\r  {downloaded / 1024 / 1024:.1f} MiB / {total / 1024 / 1024:.1f} MiB ({pct:.1f}%) at {rate_mib:.1f} MiB/s"
    else:
        message = f"\r  {downloaded / 1024 / 1024:.1f} MiB at {rate_mib:.1f} MiB/s"
    sys.stdout.write(message)
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
