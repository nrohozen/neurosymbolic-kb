"""Tests for the clingo-backed inference engine. Offline (clingo is local, no network);
skipped automatically if clingo isn't installed."""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from src.inference_engine import InferenceEngine  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "ads.lp"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


def test_faster_than_is_derived_from_the_complexity_lattice(engine):
    facts = ["has_complexity(quicksort,o_nlogn)", "has_complexity(bubblesort,o_n2)"]
    assert engine.entails(facts, "faster_than(quicksort,bubblesort)")
    assert not engine.entails(facts, "faster_than(bubblesort,quicksort)")


def test_is_a_is_transitive(engine):
    facts = ["is_a(a,b)", "is_a(b,c)"]
    assert engine.entails(facts, "is_a(a,c)")


def test_conflicting_complexity_is_a_contradiction(engine):
    facts = ["has_complexity(quicksort,o_nlogn)", "has_complexity(quicksort,o_n2)"]
    assert not engine.is_consistent(facts)


def test_is_a_cycle_is_a_contradiction(engine):
    assert not engine.is_consistent(["is_a(a,b)", "is_a(b,a)"])


def test_disjoint_property_is_a_contradiction(engine):
    assert not engine.is_consistent(["has_property(x,stable)", "has_property(x,not_stable)"])


def test_independent_facts_are_consistent(engine):
    facts = ["has_complexity(heapsort,o_nlogn)", "is_a(heapsort,sorting_algorithm)"]
    assert engine.is_consistent(facts)
