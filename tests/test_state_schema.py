"""Tests for the domain-3 state schema, run through the UNCHANGED inference engine (reuse
is the point — metric 20). Offline (clingo local); skipped if clingo absent."""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from src.inference_engine import InferenceEngine  # noqa: E402
from src.knowledge_graph import Triple  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "state.lp"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


def _drift(k, v):
    return Triple(k, "drift", v).as_atom()


def test_drift_is_derived_when_observed_differs_from_desired(engine):
    facts = ["desired(k1,good)", "observed(k1,bad)"]
    assert engine.entails(facts, _drift("k1", "bad"))


def test_no_drift_when_observed_matches_desired(engine):
    r = engine.run(["desired(k1,good)", "observed(k1,good)"])
    assert r.satisfiable
    assert not any(a.startswith("drift(") for a in r.atoms)


def test_multiple_drifts_are_enumerated_in_one_run(engine):
    facts = ["desired(k1,a)", "observed(k1,b)", "desired(k2,c)", "observed(k2,d)"]
    r = engine.run(facts)
    assert _drift("k1", "b") in r.atoms
    assert _drift("k2", "d") in r.atoms


def test_keys_without_a_counterpart_do_not_drift(engine):
    # observed but no desired (unknown key), and desired but not yet observed
    r = engine.run(["observed(k1,x)", "desired(k2,y)"])
    assert r.satisfiable
    assert not any(a.startswith("drift(") for a in r.atoms)


def test_impossible_snapshot_is_a_contradiction(engine):
    assert not engine.is_consistent(["observed(k1,a)", "observed(k1,b)"])
    assert not engine.is_consistent(["desired(k1,a)", "desired(k1,b)"])
