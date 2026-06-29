"""Tests for the domain-2 code schema, run through the UNCHANGED inference engine
(reuse is the point — see metric 16). Offline (clingo local); skipped if clingo absent."""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from src.inference_engine import InferenceEngine  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "code.lp"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


def test_reaches_is_the_transitive_closure_of_calls(engine):
    facts = ["calls(a,b)", "calls(b,c)"]
    assert engine.entails(facts, "reaches(a,c)")
    assert not engine.entails(facts, "reaches(c,a)")


def test_imports_trans_is_transitive(engine):
    facts = ["imports(m1,m2)", "imports(m2,m3)"]
    assert engine.entails(facts, "imports_trans(m1,m3)")


def test_inheritance_cycle_is_a_contradiction(engine):
    assert not engine.is_consistent(["inherits(a,b)", "inherits(b,a)"])
    assert not engine.is_consistent(["inherits(a,a)"])


def test_layering_violation_core_importing_harness_is_a_contradiction(engine):
    facts = ["imports(core_mod,harness_mod)", "layer(core_mod,core)", "layer(harness_mod,harness)"]
    assert not engine.is_consistent(facts)
    # transitively, too
    facts_t = [
        "imports(core_mod,mid_mod)", "imports(mid_mod,harness_mod)",
        "layer(core_mod,core)", "layer(harness_mod,harness)",
    ]
    assert not engine.is_consistent(facts_t)


def test_harness_importing_core_is_fine(engine):
    facts = ["imports(harness_mod,core_mod)", "layer(harness_mod,harness)", "layer(core_mod,core)"]
    assert engine.is_consistent(facts)


def test_independent_code_facts_are_consistent(engine):
    facts = ["calls(f,g)", "inherits(c,d)", "imports(m1,m2)", "defines(m1,f)"]
    assert engine.is_consistent(facts)
