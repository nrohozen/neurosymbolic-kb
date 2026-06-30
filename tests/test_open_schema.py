"""Tests for the domain-5 open-knowledge schema, via the UNCHANGED engine (reuse = metric
38). Offline (clingo local); skipped if clingo absent."""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from src.inference_engine import InferenceEngine  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "open.lp"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


def test_broader_than_is_transitive(engine):
    facts = ["broader_than(a,b)", "broader_than(b,c)"]
    assert engine.entails(facts, "broader_than(a,c)")


def test_broader_than_cycle_is_a_conflict(engine):
    assert not engine.is_consistent(["broader_than(a,b)", "broader_than(b,a)"])  # surface
    assert not engine.is_consistent(  # latent 3-cycle
        ["broader_than(a,b)", "broader_than(b,c)", "broader_than(c,a)"]
    )


def test_same_as_is_symmetric_and_transitive(engine):
    assert engine.entails(["same_as(x,y)"], "same_as(y,x)")
    assert engine.entails(["same_as(x,y)", "same_as(y,z)"], "same_as(x,z)")


def test_broader_than_and_same_as_disjoint(engine):
    assert not engine.is_consistent(["broader_than(x,y)", "same_as(x,y)"])  # surface
    # latent via same_as transitivity: x~y, y~z, x broader_than z
    assert not engine.is_consistent(
        ["same_as(x,y)", "same_as(y,z)", "broader_than(x,z)"]
    )


def test_independent_open_claims_are_consistent(engine):
    facts = ["broader_than(animal,dog)", "same_as(puppy,young_dog)", "broader_than(dog,puppy)"]
    assert engine.is_consistent(facts)
