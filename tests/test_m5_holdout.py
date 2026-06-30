"""Held-out calibration set is well-formed AND disjoint from the diagnosed set (anti-overfit
guarantee for M5.2). Offline, no network."""
from pathlib import Path

from eval.contested import load_contested

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSED = ROOT / "eval" / "m5_contested.jsonl"
HOLDOUT = ROOT / "eval" / "m5_contested_holdout.jsonl"


def test_holdout_is_balanced():
    cases = load_contested(HOLDOUT)
    by = {}
    for c in cases:
        by[c["status"]] = by.get(c["status"], 0) + 1
    assert by.get("contested", 0) >= 5
    assert by.get("settled_true", 0) >= 3
    assert by.get("settled_false", 0) >= 3


def test_holdout_is_disjoint_from_the_diagnosed_set():
    def keys(path):
        return {(c["s"], c["r"], c["o"]) for c in load_contested(path)}
    assert keys(HOLDOUT).isdisjoint(keys(DIAGNOSED)), "held-out claims overlap the diagnosed set"
