"""Honesty meta-test for the M2-filter candidate set: the labels must be TRUE. An
`error_contradictory` triple must really be UNSAT against the seeds; every `true` and
`error_consistent` triple must really be SAT. This stops the set from rigging metrics
10-12 by mislabeling. Offline (clingo local); skipped if clingo absent."""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from eval.filter_cases import load_filter_cases  # noqa: E402
from src.inference_engine import InferenceEngine  # noqa: E402
from src.knowledge_graph import KnowledgeGraph  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "ads.lp"
SEEDS = ROOT / "schema" / "seeds.jsonl"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


@pytest.fixture(scope="module")
def seed_atoms():
    return KnowledgeGraph.from_seeds(SEEDS).atoms()


def test_set_is_balanced_and_well_formed():
    cases = load_filter_cases()
    by = {}
    for c in cases:
        by[c.label] = by.get(c.label, 0) + 1
    assert by.get("error_contradictory", 0) >= 8
    assert by.get("true", 0) >= 8
    assert by.get("error_consistent", 0) >= 3
    atoms = [c.triple.as_atom() for c in cases]
    assert len(atoms) == len(set(atoms)), "duplicate candidate atoms"


def test_labels_are_honest(engine, seed_atoms):
    for c in load_filter_cases():
        consistent = engine.is_consistent(list(seed_atoms) + [c.triple.as_atom()])
        if c.label == "error_contradictory":
            assert not consistent, f"{c.triple.as_atom()} labeled contradictory but is SAT vs seeds"
        else:
            assert consistent, f"{c.triple.as_atom()} labeled {c.label} but is UNSAT vs seeds"
