"""Deterministic, offline tests for the triple store (no clingo, no network)."""
from pathlib import Path

from src.knowledge_graph import KnowledgeGraph, Triple, normalize

SEEDS = Path(__file__).resolve().parents[1] / "schema" / "seeds.jsonl"


def test_normalize_makes_asp_safe_constants():
    assert normalize("Quicksort") == "quicksort"
    assert normalize("Binary Search") == "binary_search"
    assert normalize("O(n log n)") == "o_n_log_n_"
    # must not start with a digit (ASP would read it as a number)
    assert normalize("2n").startswith("x_")


def test_as_atom_is_space_free_canonical_form():
    t = Triple("quicksort", "has_complexity", "o_nlogn")
    assert t.as_atom() == "has_complexity(quicksort,o_nlogn)"


def test_add_dedups():
    kg = KnowledgeGraph()
    assert kg.add(Triple("a", "is_a", "b")) is True
    assert kg.add(Triple("a", "is_a", "b")) is False
    assert len(kg) == 1


def test_from_seeds_loads_anchor_triples():
    kg = KnowledgeGraph.from_seeds(SEEDS)
    assert len(kg) >= 20
    atoms = kg.atoms()
    assert "has_complexity(quicksort,o_nlogn)" in atoms
    assert "is_a(quicksort,sorting_algorithm)" in atoms
