"""Tests for the M2-filter scoring (metrics 10-12) and the order-dependence caveat.
Offline (clingo local); skipped if clingo absent."""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from eval.filter_cases import load_filter_cases  # noqa: E402
from eval.run_m2_filter import evaluate_filter  # noqa: E402
from src.extraction_filter import consistency_filter  # noqa: E402
from src.inference_engine import InferenceEngine  # noqa: E402
from src.knowledge_graph import KnowledgeGraph, Triple  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "ads.lp"
SEEDS = ROOT / "schema" / "seeds.jsonl"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


@pytest.fixture(scope="module")
def seed_atoms():
    return KnowledgeGraph.from_seeds(SEEDS).atoms()


def test_filter_catches_contradictions_keeps_truths_and_lifts_precision(engine, seed_atoms):
    s = evaluate_filter(engine, seed_atoms, load_filter_cases())
    assert s.catch_rate == pytest.approx(1.0)        # metric 10: all contradictions dropped
    assert s.false_drop_rate == pytest.approx(0.0)   # metric 11: no truth dropped
    assert s.consistent_dropped == 0                 # ceiling: cannot catch consistent errors
    assert s.lift > 0                                # metric 12: precision recovered
    assert s.precision_filt > s.precision_raw


def test_order_dependence_a_true_fact_can_be_dropped_if_a_conflict_precedes_it(engine):
    # Two facts about an UNSEEDED entity, jointly violating single-complexity: neither
    # conflicts the seeds alone, so whichever arrives FIRST survives -- the filter's known
    # order-dependence (DIRECTION.md M2-filter caveat).
    a = Triple("foo", "has_complexity", "o_n")
    b = Triple("foo", "has_complexity", "o_nlogn")
    assert consistency_filter(engine, [], [a, b]).kept == [a]
    assert consistency_filter(engine, [], [b, a]).kept == [b]
