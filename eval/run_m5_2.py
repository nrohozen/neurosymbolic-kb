"""Milestone 5.2 scorecard: the calibration-probe fix, on HELD-OUT data.

Same machinery as M5.1, two changes only: (1) the negation probe scores a clean negated
STATEMENT (`negation_statement_text`) instead of the double-negative question that local
models fumbled; (2) it runs on `m5_contested_holdout.jsonl`, disjoint from the set the bug
was diagnosed on. Metrics 34-37 (see DIRECTION.md). 34 is deterministic; 35-37 use the live
judge (SKIPPED without Ollama).

Run:  python -m eval.run_m5_2
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from eval.contested import build_signals, load_contested, negation_statement_text  # noqa: F401
from eval.run_m1 import _verdict
from eval.run_m5 import claim_text
from eval.run_m5_1 import build_rows, evaluate
from src.inference_engine import InferenceEngine
from src.judge_ensemble import JudgeEnsemble
from src.knowledge_graph import KnowledgeGraph

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "csfield.lp"
SEEDS_FILE = ROOT / "eval" / "m5_seeds.jsonl"
HOLDOUT = ROOT / "eval" / "m5_contested_holdout.jsonl"

CORE = [
    "src/inference_engine.py",
    "src/knowledge_graph.py",
    "src/extraction_filter.py",
    "src/canonicalization.py",
    "src/belief_revision.py",
    "src/calibration.py",  # the adjudication logic was never the bug -> must stay unchanged
]


def core_diff_lines() -> Optional[int]:
    try:
        base = subprocess.check_output(
            ["git", "rev-list", "--max-count=1", "--grep=M5.2: pre-commit", "HEAD"],
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

    seed_atoms = KnowledgeGraph.from_seeds(SEEDS_FILE).atoms()
    cases = load_contested(HOLDOUT)
    judge_pos = JudgeEnsemble(claim_text=claim_text)
    judge_neg = JudgeEnsemble(claim_text=negation_statement_text)  # THE FIX

    s = evaluate(build_rows(engine, seed_atoms, cases, judge_pos, judge_neg))
    diff = core_diff_lines()
    v34 = "GO" if diff == 0 else "KILL"

    print("=" * 68)
    print("  Milestone 5.2 scorecard  (probe fix, HELD-OUT calibration set)")
    print("=" * 68)
    print(f"  held-out claims={len(cases)}  ({s.n_contested} contested / {s.n_settled} settled)")
    print("-" * 68)
    diff_str = "n/a" if diff is None else str(diff)
    print(f"  34. core reuse (swappable) {diff_str:>5} diffs  go=0                 -> {v34}")
    if not s.available:
        print("  35-37. SKIPPED (no Ollama; live judge unavailable)")
        print("=" * 68)
        return 0

    v35 = _verdict(s.contested_recall, 0.60, 0.30)
    v36 = _verdict(s.settled_over_abstention, 0.30, 0.50, higher_is_better=False)
    lift = s.lift if s.lift is not None else 0.0
    v37 = "GO" if lift >= 0 else "KILL"
    ca = "n/a" if s.committed_acc is None else f"{s.committed_acc:.2f}"
    ja = "n/a" if s.judge_alone_acc is None else f"{s.judge_alone_acc:.2f}"

    print(f"  35. contested abstention  {s.contested_recall:5.2f}    go>=0.60 kill<0.30   -> {v35}")
    print(f"  36. settled over-abstain  {s.settled_over_abstention:5.2f}    go<=0.30 kill>0.50   -> {v36}")
    print(f"  37. committed-acc lift   {lift:+5.2f}    go>=0               -> {v37}"
          f"  (committed {ca} vs judge-alone {ja}, {s.n_committed_settled} committed)")
    print("-" * 68)
    print(f"  (M5.1 over-abstention was 0.62 KILL; this run is the probe-fix re-test)")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
