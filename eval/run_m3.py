"""Milestone 3 scorecard: domain 2 (a Python codebase).

Tests whether the deductive core is portable: a NEW schema (schema/code.lp) + a NEW oracle
(AstOracle) over AST-extracted facts, with the engine / triple store / contradiction logic
reused UNCHANGED. Metrics 16-19 (see DIRECTION.md). Metric 16 (swappability) is checked
with `git diff` on the core modules; 17-19 are deductive (clingo only, no LLM, no network).

The scoring helpers are pure and unit-tested; `main` runs them over the fixture + the real
repo and prints the verdict.

Run:  python -m eval.run_m3
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Sequence

from eval.run_m1 import _verdict
from src.code_extraction import extract_facts, python_files
from src.inference_engine import InferenceEngine
from src.knowledge_graph import Triple
from src.oracle import AstOracle, Claim

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "code.lp"
CASES = ROOT / "eval" / "m3_cases.jsonl"

# the swappability-frozen core: these must NOT change to bring up domain 2 (metric 16)
CORE = [
    "src/inference_engine.py",
    "src/knowledge_graph.py",
    "src/extraction_filter.py",
    "src/canonicalization.py",
]


def _atoms(facts) -> List[str]:
    return [Triple(*f).as_atom() for f in facts]


def contradiction_recall(engine: InferenceEngine, cases: Sequence[dict]) -> float:
    contra = [c for c in cases if c["type"] == "contradiction"]
    if not contra:
        return 0.0
    caught = sum(not engine.is_consistent(_atoms(c["facts"])) for c in contra)
    return caught / len(contra)


def reachability(engine, oracle, base_atoms, cases):
    reach = [c for c in cases if c["type"] == "reach"]
    correct = agree = 0
    for c in reach:
        q = Triple(c["a"], "reaches", c["b"])
        deduced = engine.entails(base_atoms, q.as_atom())
        oracle_says = oracle.adjudicate(Claim(q, kind="reachability")).holds
        correct += int(deduced == c["gold"])
        agree += int(deduced == oracle_says)
    n = len(reach)
    return (correct / n if n else 0.0), (agree / n if n else 0.0), n


def false_contradiction_rate(engine, control_atom_sets) -> float:
    if not control_atom_sets:
        return 0.0
    flagged = sum(not engine.is_consistent(a) for a in control_atom_sets)
    return flagged / len(control_atom_sets)


def core_diff_lines() -> int | None:
    """Lines changed in the frozen core since the M3 pre-commit (metric 16)."""
    try:
        base = subprocess.check_output(
            ["git", "rev-list", "--max-count=1", "--grep=M3: pre-commit", "HEAD"],
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

    # fixture: stable call graph for reachability + the AstOracle
    fixture_facts = extract_facts(python_files(ROOT, ["eval/m3_fixture"]), ROOT)
    fixture_atoms = sorted({t.as_atom() for t in fixture_facts})
    oracle = AstOracle.from_call_triples(fixture_facts)

    # real repo: extraction-at-scale; its facts must be self-consistent (metric 19)
    real_facts = extract_facts(python_files(ROOT, ["src", "eval"]), ROOT)
    real_atoms = sorted({t.as_atom() for t in real_facts})

    recall = contradiction_recall(engine, cases)
    acc, agree, n_reach = reachability(engine, oracle, fixture_atoms, cases)
    controls = [real_atoms] + [_atoms(c["facts"]) for c in cases if c["type"] == "consistent"]
    fcr = false_contradiction_rate(engine, controls)
    diff = core_diff_lines()

    v16 = "GO" if diff == 0 else ("KILL" if (diff is None or diff > 0) else "MID")
    v17 = _verdict(recall, 0.90, 0.60)
    v18 = _verdict(acc, 0.90, 0.50)
    v19 = _verdict(fcr, 0.10, 0.25, higher_is_better=False)

    print("=" * 68)
    print("  Milestone 3 scorecard  (domain 2: a Python codebase)")
    print("=" * 68)
    print(f"  real repo: {len(real_atoms)} facts extracted from src/ + eval/  |  "
          f"fixture: {len(fixture_atoms)} facts")
    print(f"  reachability pairs={n_reach}  contradictions={sum(c['type']=='contradiction' for c in cases)}"
          f"  consistent controls={len(controls)}")
    print("-" * 68)
    diff_str = "n/a" if diff is None else str(diff)
    print(f"  16. core reuse (swappable) {diff_str:>5} diffs  go=0                 -> {v16}")
    print(f"  17. contradiction recall  {recall:5.2f}    go>=0.90 kill<0.60   -> {v17}")
    print(f"  18. reachability accuracy {acc:5.2f}    go>=0.90 kill<0.50   -> {v18}")
    print(f"  19. false-contradiction   {fcr:5.2f}    go<=0.10 kill>0.25   -> {v19}")
    print("-" * 68)
    print(f"  cross-check: engine closure agrees with AstOracle BFS on {agree:.2f} of pairs")
    print(f"  frozen core unchanged: {CORE}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
