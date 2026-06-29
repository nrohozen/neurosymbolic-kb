"""Deterministic test of the M2 scoring math: the consistency filter must raise precision
by dropping the UNSAT-inducing extraction error, without dropping any gold truth. Offline
(clingo local); skipped if clingo absent."""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from eval.run_m2 import evaluate  # noqa: E402
from src.inference_engine import InferenceEngine  # noqa: E402
from src.knowledge_graph import Triple  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "ads.lp"


def test_filter_recovers_precision_without_costing_recall():
    engine = InferenceEngine.from_schema_file(SCHEMA)
    seed_atoms = ["has_complexity(bubblesort,o_n2)", "is_a(bubblesort,sorting_algorithm)"]
    gold_atoms = {
        "is_a(bubblesort,sorting_algorithm)",
        "has_complexity(bubblesort,o_n2)",
    }
    candidates = [
        Triple("bubblesort", "is_a", "sorting_algorithm"),    # correct
        Triple("bubblesort", "has_complexity", "o_n2"),       # correct (== seed)
        Triple("bubblesort", "has_complexity", "o_nlogn"),    # error: conflicts seed -> dropped
        Triple("bubblesort", "has_property", "lifo"),         # false positive: consistent -> kept
    ]
    s = evaluate(engine, seed_atoms, gold_atoms, candidates)

    assert s.precision_raw == pytest.approx(0.5)       # 2 of 4
    assert s.recall_raw == pytest.approx(1.0)          # both gold found
    assert s.n_dropped == 1 and s.false_drops == 0     # only the real error dropped
    assert s.precision_filt > s.precision_raw          # 2/3 > 1/2  -> metric 8 GO
    assert s.retention == pytest.approx(1.0)           # metric 9 GO
