"""Pair selection helpers for the local benv1_14k dataset."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path


MASTER_LABELS_FILENAME = "benv1_14k_dataset_master_labels.csv"


@dataclass(slots=True)
class Benv1Pair:
    index: int
    s1_id: str
    s2_id: str
    s1_path: str
    s2_path: str
    s1_labels: list[str]
    s2_labels: list[str]
    exists: bool

    def to_dict(self) -> dict:
        return asdict(self)


def select_benv1_pair(
    dataset_root: str | Path,
    *,
    index: int | None = None,
    s1_id: str | None = None,
    s2_id: str | None = None,
) -> Benv1Pair:
    """Select a matching S1/S2 pair from benv1_14k labels."""

    if sum(value is not None for value in (index, s1_id, s2_id)) != 1:
        raise ValueError("Provide exactly one selector: index, s1_id, or s2_id.")

    root = Path(dataset_root)
    rows = _read_rows(root)
    for row_index, row in enumerate(rows):
        if index is not None and row_index != index:
            continue
        if s1_id is not None and row["S1_ID"] != s1_id:
            continue
        if s2_id is not None and row["S2_ID"] != s2_id:
            continue
        return _row_to_pair(root, row_index, row)

    selector = f"index={index}" if index is not None else f"s1_id={s1_id}" if s1_id else f"s2_id={s2_id}"
    raise LookupError(f"No benv1_14k pair found for {selector}.")


def list_benv1_pairs(dataset_root: str | Path, *, limit: int = 10) -> list[Benv1Pair]:
    """Return the first N pair mappings for quick inspection."""

    root = Path(dataset_root)
    return [_row_to_pair(root, index, row) for index, row in enumerate(_read_rows(root)[:limit])]


def _read_rows(dataset_root: Path) -> list[dict[str, str]]:
    csv_path = dataset_root / MASTER_LABELS_FILENAME
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing benv1_14k labels CSV: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _row_to_pair(root: Path, index: int, row: dict[str, str]) -> Benv1Pair:
    s1_path = root / "s1" / row["S1_ID"]
    s2_path = root / "s2" / row["S2_ID"]
    return Benv1Pair(
        index=index,
        s1_id=row["S1_ID"],
        s2_id=row["S2_ID"],
        s1_path=str(s1_path),
        s2_path=str(s2_path),
        s1_labels=_split_labels(row.get("S1_Labels", "")),
        s2_labels=_split_labels(row.get("S2_Labels", "")),
        exists=s1_path.exists() and s2_path.exists(),
    )


def _split_labels(value: str) -> list[str]:
    return [label.strip() for label in value.split("|") if label.strip()]
