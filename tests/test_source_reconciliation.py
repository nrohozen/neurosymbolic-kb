"""Tests for source reconciliation (domain 5). Offline (clingo local); skipped if absent."""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from src.inference_engine import InferenceEngine  # noqa: E402
from src.source_reconciliation import (  # noqa: E402
    reconcile,
    sourced,
    surface_conflicts,
)

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "open.lp"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


def test_all_consistent_sources_are_agreed(engine):
    claims = [
        sourced("animal", "broader_than", "dog", "src_a"),
        sourced("dog", "broader_than", "puppy", "src_b"),
    ]
    r = reconcile(engine, claims)
    assert len(r.agreed) == 2 and not r.contested


def test_surface_conflict_two_sources(engine):
    claims = [
        sourced("a", "broader_than", "b", "src_a"),
        sourced("b", "broader_than", "a", "src_b"),  # reverse -> 2-cycle
    ]
    r = reconcile(engine, claims)
    assert not r.agreed
    assert len(r.contested) == 1
    cl = r.contested[0]
    assert cl.kind == "surface"
    assert cl.sources == {"src_a", "src_b"}     # both positions kept with sources
    assert len(cl.positions) == 2


def test_latent_conflict_three_sources_no_pair_conflicts(engine):
    claims = [
        sourced("a", "broader_than", "b", "src_a"),
        sourced("b", "broader_than", "c", "src_b"),
        sourced("c", "broader_than", "a", "src_c"),  # closes a 3-cycle
    ]
    # the pairwise baseline sees NOTHING...
    assert surface_conflicts(engine, claims) == []
    # ...but deductive reconcile localizes the latent conflict, keeping all three sources
    r = reconcile(engine, claims)
    assert len(r.contested) == 1
    cl = r.contested[0]
    assert cl.kind == "latent"
    assert cl.sources == {"src_a", "src_b", "src_c"}
    assert len(cl.positions) == 3


def test_latent_conflict_across_relations(engine):
    claims = [
        sourced("x", "same_as", "y", "src_a"),
        sourced("y", "same_as", "z", "src_b"),
        sourced("x", "broader_than", "z", "src_c"),  # x~z via transitivity, but broader_than -> conflict
    ]
    assert surface_conflicts(engine, claims) == []
    r = reconcile(engine, claims)
    assert len(r.contested) == 1 and r.contested[0].kind == "latent"


def test_agreed_and_contested_partition_cleanly(engine):
    claims = [
        sourced("animal", "broader_than", "cat", "src_a"),   # agreed (independent)
        sourced("p", "broader_than", "q", "src_b"),
        sourced("q", "broader_than", "p", "src_c"),          # contested pair
    ]
    r = reconcile(engine, claims)
    agreed_atoms = {t.as_atom() for t in r.agreed}
    assert "broader_than(animal,cat)" in agreed_atoms
    assert len(r.contested) == 1
    assert {t.as_atom() for t in r.contested[0].positions} == {
        "broader_than(p,q)", "broader_than(q,p)"
    }
