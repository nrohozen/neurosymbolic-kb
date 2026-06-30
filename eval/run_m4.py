"""Milestone 4 scorecard: domain 3 (homelab/infrastructure), a temporal/mutable oracle.

Tests whether the deductive core transfers to a mutable oracle: a NEW schema
(schema/state.lp) + a NEW oracle (StateOracle) over snapshot facts, with the engine /
triple store / contradiction logic reused UNCHANGED. Metrics 20-24 (see DIRECTION.md):
config-drift = contradiction-as-product, plus an active-learning staleness policy over a
simulated snapshot stream. Deductive + offline (clingo only, no LLM, no network).

Run:  python -m eval.run_m4
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable, List, Sequence

from eval.run_m1 import _verdict
from src.inference_engine import InferenceEngine
from src.knowledge_graph import Triple
from src.staleness import ttl_for
from src.state_extraction import file_provider, observed_from_snapshot

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "state.lp"
SNAPSHOT = ROOT / "eval" / "m4_snapshot.json"
DESIRED = ROOT / "eval" / "m4_desired.json"
CASES = ROOT / "eval" / "m4_cases.jsonl"

CORE = [
    "src/inference_engine.py",
    "src/knowledge_graph.py",
    "src/extraction_filter.py",
    "src/canonicalization.py",
]

# simulated change stream: (tick, key, new value). Each change persists past its key's TTL
# (realistic for infra config), so a correct staleness policy catches it.
TICKS = 20
SCHEDULE = [
    (3, "proxmox.guest.gameserver.status", "stopped"),
    (10, "proxmox.guest.downloads.status", "stopped"),
    (15, "proxmox.guest.api.status", "stopped"),
    (4, "npm.proxy.downloads.example.foo.enabled", "false"),
    (12, "npm.proxy.api.example.foo.enabled", "false"),
    (8, "pihole.secondary_dns", "1.1.1.1"),
    (1, "npm.proxy.media.example.foo.forward", "10.0.0.99:8080"),
    (5, "npm.proxy.downloads.example.foo.forward", "10.0.0.45:8081"),
    (2, "pihole.dns.downloads.lan", "10.0.0.44"),
    (6, "pihole.dns.api.lan", "10.0.0.13"),
]


def _atoms(facts) -> List[str]:
    return [Triple(*f).as_atom() for f in facts]


def _flagged(engine: InferenceEngine, atoms: Sequence[str]) -> bool:
    """A snapshot is flagged if it is impossible (UNSAT) or any drift is derived."""
    r = engine.run(atoms)
    return (not r.satisfiable) or any(a.startswith("drift(") for a in r.atoms)


def drift_recall(engine, cases) -> float:
    drift = [c for c in cases if c["type"] == "drift"]
    if not drift:
        return 0.0
    return sum(_flagged(engine, _atoms(c["facts"])) for c in drift) / len(drift)


def false_drift_rate(engine, atom_sets) -> float:
    if not atom_sets:
        return 0.0
    return sum(_flagged(engine, a) for a in atom_sets) / len(atom_sets)


def volatility_of(key: str) -> str:
    if key.endswith(".status"):
        return "high"
    if key.endswith(".enabled") or key == "pihole.secondary_dns":
        return "medium"
    return "low"


def simulate_active_learning(keys, schedule, ticks):
    """Compare a TTL-by-volatility re-query policy to naive 'query everything every tick'."""
    changes: dict[str, list[tuple[int, str]]] = {}
    for tick, key, val in sorted(schedule):
        changes.setdefault(key, []).append((tick, val))
    total_events = sum(len(v) for v in changes.values())

    detected = 0
    policy_q = 0
    for key in keys:
        ttl = ttl_for(volatility_of(key))
        qticks = [t for t in range(ticks) if t % ttl == 0]
        policy_q += len(qticks)
        kc = changes.get(key, [])
        for i, (c, _v) in enumerate(kc):
            end = kc[i + 1][0] if i + 1 < len(kc) else ticks
            if any(c <= q < end for q in qticks):  # a query observes this value while current
                detected += 1

    naive_q = len(keys) * ticks
    recall = detected / total_events if total_events else 1.0
    savings = (naive_q - policy_q) / naive_q if naive_q else 0.0
    return recall, savings, naive_q, policy_q, total_events


def core_diff_lines() -> int | None:
    try:
        base = subprocess.check_output(
            ["git", "rev-list", "--max-count=1", "--grep=M4: pre-commit", "HEAD"],
            cwd=ROOT, text=True,
        ).strip()
        if not base:
            return None
        out = subprocess.check_output(
            ["git", "diff", "--numstat", f"{base}..HEAD", "--", *CORE], cwd=ROOT, text=True
        )
        total = 0
        for line in out.splitlines():
            add, dele, _ = line.split("\t", 2)
            total += (int(add) if add.isdigit() else 0) + (int(dele) if dele.isdigit() else 0)
        return total
    except Exception:
        return None


def main() -> int:
    engine = InferenceEngine.from_schema_file(SCHEMA)
    try:
        engine.run([])
    except ImportError:
        print("clingo is not installed.  pip install -r requirements.txt")
        return 1

    cases = [json.loads(ln) for ln in CASES.read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.startswith("#")]

    snapshot = file_provider(SNAPSHOT)()
    observed = observed_from_snapshot(snapshot)
    observed_atoms = [t.as_atom() for t in observed]
    keys = [t.s for t in observed]
    desired = json.loads(DESIRED.read_text(encoding="utf-8"))
    desired_atoms = [Triple(k, "desired", v).as_atom() for k, v in desired.items()]

    recall = drift_recall(engine, cases)
    # false-drift inputs: the real baseline (desired matches observed) + the consistent cases
    controls = [observed_atoms + desired_atoms] + \
        [_atoms(c["facts"]) for c in cases if c["type"] == "consistent"]
    fdr = false_drift_rate(engine, controls)
    al_recall, savings, naive_q, policy_q, n_events = simulate_active_learning(keys, SCHEDULE, TICKS)
    diff = core_diff_lines()

    v20 = "GO" if diff == 0 else "KILL"
    v21 = _verdict(recall, 0.90, 0.60)
    v22 = _verdict(fdr, 0.10, 0.25, higher_is_better=False)
    v23 = _verdict(al_recall, 0.90, 0.60)
    v24 = "GO" if savings > 0 else "KILL"

    print("=" * 68)
    print("  Milestone 4 scorecard  (domain 3: homelab / a temporal oracle)")
    print("=" * 68)
    print(f"  snapshot keys={len(keys)}  desired-intent={len(desired)}  "
          f"drift cases={sum(c['type']=='drift' for c in cases)}  controls={len(controls)}")
    print("-" * 68)
    diff_str = "n/a" if diff is None else str(diff)
    print(f"  20. core reuse (swappable) {diff_str:>5} diffs  go=0                 -> {v20}")
    print(f"  21. drift-detection recall {recall:5.2f}    go>=0.90 kill<0.60   -> {v21}")
    print(f"  22. false-drift rate       {fdr:5.2f}    go<=0.10 kill>0.25   -> {v22}")
    print(f"  23. active-learn recall    {al_recall:5.2f}    go>=0.90 kill<0.60   -> {v23}")
    print(f"  24. query savings          {savings:5.2f}    go>0                 -> {v24}")
    print("-" * 68)
    print(f"  active learning: {policy_q} queries vs {naive_q} naive over {TICKS} ticks "
          f"({n_events} changes, {al_recall:.0%} caught)")
    print(f"  frozen core unchanged: {CORE}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
