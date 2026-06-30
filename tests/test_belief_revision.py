"""Tests for AGM belief revision over the CS-field schema. Offline (clingo local); skipped
if clingo absent."""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from src.belief_revision import revise  # noqa: E402
from src.inference_engine import InferenceEngine  # noqa: E402
from src.knowledge_graph import Triple  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "csfield.lp"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


def _c(*pairs):
    return {Triple(s, "subfield_of", o).as_atom(): conf for s, o, conf in pairs}


def test_consistent_candidate_is_accepted(engine):
    accepted = [Triple("ml", "subfield_of", "ai")]
    cand = Triple("nlp", "subfield_of", "ai")
    r = revise(engine, accepted, cand, _c(("ml", "ai", 0.9), ("nlp", "ai", 0.8)))
    assert r.candidate_accepted and not r.retracted
    assert cand in r.accepted


def test_weaker_candidate_is_rejected_incumbent_kept(engine):
    accepted = [Triple("ml", "subfield_of", "ai")]
    cand = Triple("ai", "subfield_of", "ml")  # would create a 2-cycle
    r = revise(engine, accepted, cand, _c(("ml", "ai", 0.9), ("ai", "ml", 0.2)))
    assert not r.candidate_accepted
    assert accepted[0] in r.accepted
    assert engine.is_consistent([t.as_atom() for t in r.accepted])


def test_tie_favors_the_incumbent(engine):
    accepted = [Triple("ml", "subfield_of", "ai")]
    cand = Triple("ai", "subfield_of", "ml")
    r = revise(engine, accepted, cand, _c(("ml", "ai", 0.7), ("ai", "ml", 0.7)))
    assert not r.candidate_accepted and accepted[0] in r.accepted


def test_stronger_candidate_retracts_weaker_belief(engine):
    accepted = [Triple("ai", "subfield_of", "ml")]   # weakly held, "wrong" direction
    cand = Triple("ml", "subfield_of", "ai")
    r = revise(engine, accepted, cand, _c(("ai", "ml", 0.2), ("ml", "ai", 0.95)))
    assert r.candidate_accepted
    assert accepted[0] in r.retracted
    assert engine.is_consistent([t.as_atom() for t in r.accepted])


def test_multi_hop_cycle_retracts_the_weakest_link(engine):
    accepted = [Triple("a", "subfield_of", "b"), Triple("b", "subfield_of", "c")]
    cand = Triple("c", "subfield_of", "a")  # closes a 3-cycle
    conf = _c(("a", "b", 0.9), ("b", "c", 0.4), ("c", "a", 0.95))
    r = revise(engine, accepted, cand, conf)
    assert r.candidate_accepted
    assert Triple("b", "subfield_of", "c") in r.retracted   # the weakest link goes
    assert engine.is_consistent([t.as_atom() for t in r.accepted])
