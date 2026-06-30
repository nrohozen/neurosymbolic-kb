"""Tests for the M5 scoring helpers (metrics 26-29). Offline (clingo local); skipped if
clingo absent. Metric 27 is tested with a STUB judge so it needs no network."""
import json
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from eval.run_m5 import (  # noqa: E402
    STREAM,
    belief_revision_correctness,
    deductive_reliability,
    final_consistency,
    structure_lift,
)
from src.inference_engine import InferenceEngine  # noqa: E402
from src.knowledge_graph import KnowledgeGraph  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "csfield.lp"
SEEDS = ROOT / "eval" / "m5_seeds.jsonl"
CLAIMS = ROOT / "eval" / "m5_claims.jsonl"
REVISION = ROOT / "eval" / "m5_revision.jsonl"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


@pytest.fixture(scope="module")
def seed_atoms():
    return KnowledgeGraph.from_seeds(SEEDS).atoms()


@pytest.fixture(scope="module")
def claims():
    return [json.loads(ln) for ln in CLAIMS.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


def test_deduction_reliably_settles_derivable_claims(engine, seed_atoms, claims):
    acc, n = deductive_reliability(engine, seed_atoms, claims)
    assert n >= 5
    assert acc == pytest.approx(1.0)


def test_belief_revision_matches_designed_gold(engine):
    scenarios = [json.loads(ln) for ln in REVISION.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.startswith("#")]
    assert belief_revision_correctness(engine, scenarios) == pytest.approx(1.0)


def test_contradictory_stream_ends_consistent(engine):
    assert final_consistency(engine, STREAM) == 1.0


class _AlwaysTrueJudge:
    """Stub weak oracle: says every claim is true. It gets the true claims right and the
    false ones wrong -- so deduction (which nails the derivable-false ones) must lift accuracy."""
    def score(self, triple):
        return 0.9


def test_structure_does_not_hurt_and_lifts_over_a_weak_judge(engine, seed_atoms, claims):
    assisted, judge_alone, an, jn = structure_lift(engine, seed_atoms, claims, _AlwaysTrueJudge())
    assert assisted >= judge_alone        # metric 27: structure must not hurt
    assert assisted > judge_alone         # ... and here it strictly helps (fixes derivable-false)
