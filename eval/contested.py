"""Loader + signal-builder for the M5.1 calibration set (eval/m5_contested.jsonl).

Bridges the judge ensemble to the calibration layer's `Signals`: the positive judge gives
per-model P(claim true); the negation judge gives P(not claim) for the negation-consistency
probe. Pure given the judge objects, so tests inject stubs and stay offline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from src.calibration import Signals
from src.knowledge_graph import Triple

CONTESTED = Path(__file__).resolve().parent / "m5_contested.jsonl"
STATUSES = {"settled_true", "settled_false", "contested"}


def load_contested(path: str | Path = CONTESTED) -> List[dict]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        d = json.loads(line)
        if d["status"] not in STATUSES:
            raise ValueError(f"bad status {d['status']!r}")
        out.append(d)
    return out


def negation_claim_text(t: Triple) -> str:
    s, o = t.s.replace("_", " "), t.o.replace("_", " ")
    if t.r == "subfield_of":
        return f"In computer science, is it true that {s} is NOT a subfield of {o}?"
    if t.r == "subsumes":
        return f"In computer science, is it true that {s} does NOT generalize {o}?"
    return f"Is the statement '{t.s} {t.r} {t.o}' FALSE?"


def build_signals(triple: Triple, judge_pos, judge_neg) -> Signals:
    """model_scores from the positive judge; neg_score (ensemble mean) from the negation judge."""
    return Signals(model_scores=judge_pos.scores(triple), neg_score=judge_neg.score(triple))
