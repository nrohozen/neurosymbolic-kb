"""Tests for the deductive consistency filter. Offline (clingo local); skipped if absent."""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from src.extraction_filter import consistency_filter  # noqa: E402
from src.inference_engine import InferenceEngine  # noqa: E402
from src.knowledge_graph import Triple  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "ads.lp"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


def test_drops_candidate_that_conflicts_with_trusted_facts(engine):
    trusted = ["has_complexity(quicksort,o_nlogn)"]
    candidates = [
        Triple("quicksort", "is_a", "sorting_algorithm"),  # fine
        Triple("quicksort", "has_complexity", "o_n2"),      # conflicts trusted single-complexity
    ]
    r = consistency_filter(engine, trusted, candidates)
    assert Triple("quicksort", "is_a", "sorting_algorithm") in r.kept
    assert Triple("quicksort", "has_complexity", "o_n2") in r.dropped


def test_catches_intra_batch_conflict_first_seen_wins(engine):
    candidates = [
        Triple("heapsort", "has_property", "stable"),
        Triple("heapsort", "has_property", "not_stable"),  # disjoint with the kept one
    ]
    r = consistency_filter(engine, [], candidates)
    assert r.kept == [Triple("heapsort", "has_property", "stable")]
    assert r.dropped == [Triple("heapsort", "has_property", "not_stable")]


def test_keeps_all_independent_candidates(engine):
    candidates = [
        Triple("heapsort", "is_a", "sorting_algorithm"),
        Triple("heapsort", "has_complexity", "o_nlogn"),
        Triple("avl_tree", "is_a", "binary_search_tree"),
    ]
    r = consistency_filter(engine, [], candidates)
    assert len(r.kept) == 3 and not r.dropped


def test_skips_duplicate_of_a_trusted_fact(engine):
    trusted = ["is_a(stack,abstract_data_type)"]
    r = consistency_filter(engine, trusted, [Triple("stack", "is_a", "abstract_data_type")])
    assert not r.kept and not r.dropped
