"""M5.2 wiring test: build_rows + evaluate over the held-out set with stub judges. Offline
(clingo local); skipped if clingo absent. (evaluate's math is covered in test_run_m5_1.)"""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from eval.contested import load_contested  # noqa: E402
from eval.run_m5_1 import build_rows, evaluate  # noqa: E402
from src.inference_engine import InferenceEngine  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "csfield.lp"
HOLDOUT = ROOT / "eval" / "m5_contested_holdout.jsonl"


class _Stub:
    def __init__(self, per_model, mean):
        self._per, self._mean = per_model, mean

    def scores(self, t):
        return list(self._per)

    def score(self, t):
        return self._mean


def test_build_rows_commits_on_confident_consistent_signals():
    engine = InferenceEngine.from_schema_file(SCHEMA)
    settled_true = [c for c in load_contested(HOLDOUT) if c["status"] == "settled_true"][:2]
    # confident TRUE + consistent negation (low) -> should commit True
    rows = build_rows(engine, [], settled_true, _Stub([0.9, 0.95], 0.92), _Stub([0.08, 0.05], 0.07))
    assert len(rows) == 2
    assert all(r["adj_status"] == "committed" and r["adj_verdict"] is True for r in rows)
    s = evaluate(rows)
    assert s.settled_over_abstention == 0.0
