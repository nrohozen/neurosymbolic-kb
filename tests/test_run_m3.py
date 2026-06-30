"""Tests for the M3 scoring helpers (metrics 17-19) over the fixture. Offline (clingo
local); skipped if clingo absent."""
import json
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from eval.run_m3 import (  # noqa: E402
    _atoms,
    contradiction_recall,
    false_contradiction_rate,
    reachability,
)
from src.code_extraction import extract_facts, python_files  # noqa: E402
from src.inference_engine import InferenceEngine  # noqa: E402
from src.oracle import AstOracle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "code.lp"
CASES = ROOT / "eval" / "m3_cases.jsonl"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


@pytest.fixture(scope="module")
def cases():
    return [json.loads(ln) for ln in CASES.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


def test_all_planted_code_violations_are_caught(engine, cases):
    assert contradiction_recall(engine, cases) == pytest.approx(1.0)


def test_reachability_matches_gold_and_oracle_agrees(engine, cases):
    facts = extract_facts(python_files(ROOT, ["eval/m3_fixture"]), ROOT)
    base = sorted({t.as_atom() for t in facts})
    oracle = AstOracle.from_call_triples(facts)
    acc, agree, n = reachability(engine, oracle, base, cases)
    assert n >= 15
    assert acc == pytest.approx(1.0)     # deductive closure matches hand-labeled gold
    assert agree == pytest.approx(1.0)   # ... and the independent BFS oracle agrees


def test_consistent_controls_are_not_flagged(engine, cases):
    controls = [_atoms(c["facts"]) for c in cases if c["type"] == "consistent"]
    assert false_contradiction_rate(engine, controls) == pytest.approx(0.0)
