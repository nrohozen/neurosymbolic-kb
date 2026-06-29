"""Loader for the M2-filter labeled candidate set (eval/m2_filter_cases.jsonl).

Each line is a candidate triple plus a `label` saying what the filter ought to do with it
(see the file header). Shared by the honesty meta-test and the M2-filter scorecard.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from src.knowledge_graph import Triple

CASES = Path(__file__).resolve().parent / "m2_filter_cases.jsonl"

LABELS = {"true", "error_contradictory", "error_consistent"}


@dataclass(frozen=True)
class FilterCase:
    triple: Triple
    label: str


def load_filter_cases(path: str | Path = CASES) -> List[FilterCase]:
    cases: List[FilterCase] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        d = json.loads(line)
        if d["label"] not in LABELS:
            raise ValueError(f"unknown label {d['label']!r}")
        cases.append(FilterCase(Triple(d["s"], d["r"], d["o"]), d["label"]))
    return cases
