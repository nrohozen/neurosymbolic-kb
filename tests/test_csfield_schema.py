"""Tests for the domain-4 CS-field schema, run through the UNCHANGED inference engine
(reuse = metric 25). Offline (clingo local); skipped if clingo absent."""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from src.inference_engine import InferenceEngine  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "csfield.lp"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


def test_subfield_of_is_transitive(engine):
    facts = ["subfield_of(deep_learning,machine_learning)", "subfield_of(machine_learning,ai)"]
    assert engine.entails(facts, "subfield_of(deep_learning,ai)")
    assert not engine.entails(facts, "subfield_of(ai,deep_learning)")


def test_subfield_of_cycle_is_a_contradiction(engine):
    assert not engine.is_consistent(["subfield_of(a,b)", "subfield_of(b,a)"])
    # 3-cycle too (caught via transitive X subfield_of X)
    assert not engine.is_consistent(
        ["subfield_of(a,b)", "subfield_of(b,c)", "subfield_of(c,a)"]
    )


def test_subsumes_is_transitive_and_acyclic(engine):
    facts = ["subsumes(a,b)", "subsumes(b,c)"]
    assert engine.entails(facts, "subsumes(a,c)")
    assert not engine.is_consistent(["subsumes(x,y)", "subsumes(y,x)"])


def test_independent_field_facts_are_consistent(engine):
    facts = ["subfield_of(nlp,ai)", "subfield_of(cv,ai)", "subsumes(transformer,rnn)"]
    assert engine.is_consistent(facts)
