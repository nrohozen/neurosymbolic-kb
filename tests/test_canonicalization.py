"""Tests for the canonicalization layer. Pure Python -- no clingo, no network. Tests the
mapping rules as GENERAL rules (varied surface forms), idempotence on already-canonical
input (metric 15), and that distinct entities are never falsely merged."""
from pathlib import Path

from eval.extraction_corpus import load_corpus
from src.canonicalization import Canonicalizer, canonical_key, map_complexity, map_property
from src.knowledge_graph import KnowledgeGraph, Triple

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "schema" / "seeds.jsonl"

KNOWN = ["bubblesort", "quicksort", "sorting_algorithm", "binary_search", "binary_search_tree"]


def test_entity_linking_collapses_surface_variants():
    c = Canonicalizer(KNOWN)
    for variant in ("bubble_sort", "bubble sort", "Bubblesort", "BUBBLE-SORT"):
        assert c.link_entity(variant) == "bubblesort"
    # "sorting algorithm" (space) links to the seed type
    assert c.link_entity("sorting algorithm") == "sorting_algorithm"


def test_entity_linking_does_not_falsely_merge_distinct_entities():
    c = Canonicalizer(KNOWN)
    assert c.link_entity("binary search") == "binary_search"
    assert c.link_entity("binary search tree") == "binary_search_tree"
    # unknown mention falls back to lexical-normal form, not a wrong link
    assert c.link_entity("Heap Sort") == "heap_sort"


def test_complexity_maps_math_and_word_forms():
    assert map_complexity("O(1)") == "o_1"
    assert map_complexity("constant") == "o_1"
    assert map_complexity("O(log n)") == "o_logn"
    assert map_complexity("O(n)") == "o_n"
    assert map_complexity("linear") == "o_n"
    assert map_complexity("O(n log n)") == "o_nlogn"
    assert map_complexity("linearithmic") == "o_nlogn"
    assert map_complexity("O(n^2)") == "o_n2"
    assert map_complexity("O(n²)") == "o_n2"
    assert map_complexity("quadratic") == "o_n2"
    assert map_complexity("exponential") == "o_2n"
    assert map_complexity("not a complexity") is None
    # idempotent on the enum form
    for c in ("o_1", "o_logn", "o_n", "o_nlogn", "o_n2", "o_2n"):
        assert map_complexity(c) == c


def test_property_maps_surface_forms_with_negation():
    assert map_property("sorts in place") == "in_place"
    assert map_property("operates in place") == "in_place"
    assert map_property("out of place") == "not_in_place"
    assert map_property("stable") == "stable"
    assert map_property("not stable") == "not_stable"
    assert map_property("unstable") == "not_stable"
    assert map_property("comparison-based") == "comparison_based"
    assert map_property("last in first out") == "lifo"
    assert map_property("last-in, first-out ordering") == "lifo"
    assert map_property("first in first out") == "fifo"
    assert map_property("something else") is None
    # schema can't represent a negated comparison/lifo -> dropped, not mis-polarized
    assert map_property("not comparison based") is None
    # idempotent on enum forms
    for p in ("stable", "not_stable", "in_place", "not_in_place", "comparison_based", "lifo", "fifo"):
        assert map_property(p) == p


def test_canonicalize_triple_fixes_surface_forms():
    c = Canonicalizer(KNOWN)
    assert c.canonicalize(Triple("Bubble Sort", "has_complexity", "O(n^2)")) == \
        Triple("bubblesort", "has_complexity", "o_n2")
    assert c.canonicalize(Triple("stack", "has_property", "last in first out")) == \
        Triple("stack", "has_property", "lifo")
    # unmappable value -> rejected
    assert c.canonicalize(Triple("quicksort", "has_property", "fast")) is None


def test_canonicalize_leaves_structure_drift_unfixed():
    # a property folded into the is_a object is OUT OF SCOPE: it stays a (wrong) entity
    c = Canonicalizer(KNOWN)
    out = c.canonicalize(Triple("quicksort", "is_a", "comparison based sorting algorithm"))
    assert out == Triple("quicksort", "is_a", "comparison_based_sorting_algorithm")


def test_idempotent_on_seeds_and_gold():
    # metric 15: canonicalization must not alter already-canonical facts
    kg = KnowledgeGraph.from_seeds(SEEDS)
    c = Canonicalizer.from_seed_triples(kg.triples)
    gold = [t for e in load_corpus() for t in e.gold]
    for t in list(kg.triples) + gold:
        out = c.canonicalize(t)
        assert out is not None, f"canonicalization rejected a gold/seed fact: {t}"
        assert (out.s, out.r, out.o) == (t.s, t.r, t.o), f"altered {t} -> {out}"
