"""Tests for the M4 scoring helpers (metrics 21-24). Offline (clingo local); skipped if
clingo absent. The active-learning sim is pure and needs no clingo."""
import json
from pathlib import Path

import pytest

from eval.run_m4 import (
    SCHEDULE,
    TICKS,
    _atoms,
    drift_recall,
    false_drift_rate,
    simulate_active_learning,
    volatility_of,
)

clingo = pytest.importorskip("clingo")

from src.inference_engine import InferenceEngine  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "state.lp"
CASES = ROOT / "eval" / "m4_cases.jsonl"
SNAPSHOT = ROOT / "eval" / "m4_snapshot.json"


@pytest.fixture(scope="module")
def engine():
    return InferenceEngine.from_schema_file(SCHEMA)


@pytest.fixture(scope="module")
def cases():
    return [json.loads(ln) for ln in CASES.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


def test_all_planted_drifts_are_caught(engine, cases):
    assert drift_recall(engine, cases) == pytest.approx(1.0)


def test_consistent_states_are_not_flagged(engine, cases):
    controls = [_atoms(c["facts"]) for c in cases if c["type"] == "consistent"]
    assert false_drift_rate(engine, controls) == pytest.approx(0.0)


def test_active_learning_catches_changes_and_saves_queries():
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    from src.state_extraction import observed_from_snapshot
    keys = [t.s for t in observed_from_snapshot(snap)]
    recall, savings, naive, policy, n = simulate_active_learning(keys, SCHEDULE, TICKS)
    assert n >= 10
    assert recall == pytest.approx(1.0)   # every persisted change is caught
    assert savings > 0                     # ... while querying fewer than naive
    assert policy < naive


def test_volatility_assignment():
    assert volatility_of("proxmox.guest.api.status") == "high"
    assert volatility_of("npm.proxy.x.enabled") == "medium"
    assert volatility_of("pihole.dns.media.lan") == "low"
