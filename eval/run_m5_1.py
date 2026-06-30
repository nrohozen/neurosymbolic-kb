"""Milestone 5.1 scorecard: calibrated abstention for the weak oracle (domain 4).

Does the weak oracle know when NOT to answer? On a set of settled vs genuinely-contested CS
claims, the calibrated adjudicator should COMMIT (correctly) on settled claims and ABSTAIN
(CONTESTED) on disputed ones. Metrics 30-33 (see DIRECTION.md). 30 is deterministic
(git diff); 31-33 use the live judge ensemble (SKIPPED without Ollama).

The scoring (`evaluate`) is pure and unit-tested; `main` adds the live judge calls.

Run:  python -m eval.run_m5_1
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from eval.contested import build_signals, load_contested, negation_claim_text
from eval.run_m1 import _verdict
from eval.run_m5 import claim_text, deductive_verdict
from src.calibration import adjudicate
from src.inference_engine import InferenceEngine
from src.judge_ensemble import JudgeEnsemble
from src.knowledge_graph import KnowledgeGraph, Triple

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "csfield.lp"
SEEDS_FILE = ROOT / "eval" / "m5_seeds.jsonl"

CORE = [
    "src/inference_engine.py",
    "src/knowledge_graph.py",
    "src/extraction_filter.py",
    "src/canonicalization.py",
    "src/belief_revision.py",  # M5.1 must not touch revision either
]

_COMMITTED = {"committed", "deduced"}


@dataclass
class CalibrationScores:
    available: bool
    contested_recall: float
    settled_over_abstention: float
    committed_acc: Optional[float]
    judge_alone_acc: Optional[float]
    lift: Optional[float]
    n_contested: int
    n_settled: int
    n_committed_settled: int


def build_rows(engine, seed_atoms, cases, judge_pos, judge_neg) -> List[dict]:
    """Adjudicate each case into a scoring row. Shared by M5.1 and M5.2 (only the judges'
    claim-text / dataset differ between them)."""
    gold_of = {"settled_true": True, "settled_false": False, "contested": None}
    rows = []
    for c in cases:
        t = Triple(c["s"], c["r"], c["o"])
        ded = deductive_verdict(engine, seed_atoms, t)
        sig = build_signals(t, judge_pos, judge_neg)
        adj = adjudicate(ded, sig)
        rows.append({
            "status": c["status"],
            "gold": gold_of[c["status"]],
            "adj_status": adj.status,
            "adj_verdict": adj.verdict,
            "judge_mean": (sum(sig.model_scores) / len(sig.model_scores)) if sig.model_scores else None,
        })
    return rows


def evaluate(rows: List[dict]) -> CalibrationScores:
    """rows: {status, gold(bool|None), adj_status, adj_verdict, judge_mean(float|None)}."""
    available = any(r["judge_mean"] is not None for r in rows)
    contested = [r for r in rows if r["status"] == "contested"]
    settled = [r for r in rows if r["status"] in ("settled_true", "settled_false")]

    abstained = lambda r: r["adj_status"] not in _COMMITTED
    contested_recall = (sum(abstained(r) for r in contested) / len(contested)) if contested else 0.0
    settled_over = (sum(abstained(r) for r in settled) / len(settled)) if settled else 0.0

    committed = [r for r in settled if r["adj_status"] in _COMMITTED]
    committed_acc = (sum(r["adj_verdict"] == r["gold"] for r in committed) / len(committed)
                     if committed else None)
    judged = [r for r in settled if r["judge_mean"] is not None]
    judge_alone_acc = (sum((r["judge_mean"] >= 0.5) == r["gold"] for r in judged) / len(judged)
                       if judged else None)
    lift = (committed_acc - judge_alone_acc
            if (committed_acc is not None and judge_alone_acc is not None) else None)

    return CalibrationScores(
        available=available,
        contested_recall=contested_recall,
        settled_over_abstention=settled_over,
        committed_acc=committed_acc,
        judge_alone_acc=judge_alone_acc,
        lift=lift,
        n_contested=len(contested),
        n_settled=len(settled),
        n_committed_settled=len(committed),
    )


def core_diff_lines() -> Optional[int]:
    try:
        base = subprocess.check_output(
            ["git", "rev-list", "--max-count=1", "--grep=M5.1: pre-commit", "HEAD"],
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
    cases = load_contested()
    judge_pos = JudgeEnsemble(claim_text=claim_text)
    judge_neg = JudgeEnsemble(claim_text=negation_claim_text)

    rows = build_rows(engine, seed_atoms, cases, judge_pos, judge_neg)
    s = evaluate(rows)
    diff = core_diff_lines()
    v30 = "GO" if diff == 0 else "KILL"

    print("=" * 68)
    print("  Milestone 5.1 scorecard  (calibrated abstention for the weak oracle)")
    print("=" * 68)
    print(f"  claims={len(cases)}  ({s.n_contested} contested / {s.n_settled} settled)")
    print("-" * 68)
    diff_str = "n/a" if diff is None else str(diff)
    print(f"  30. core reuse (swappable) {diff_str:>5} diffs  go=0                 -> {v30}")
    if not s.available:
        print("  31-33. SKIPPED (no Ollama; live judge unavailable)")
        print("=" * 68)
        return 0

    v31 = _verdict(s.contested_recall, 0.60, 0.30)
    v32 = _verdict(s.settled_over_abstention, 0.30, 0.50, higher_is_better=False)
    lift = s.lift if s.lift is not None else 0.0
    v33 = "GO" if lift >= 0 else "KILL"
    ca = "n/a" if s.committed_acc is None else f"{s.committed_acc:.2f}"
    ja = "n/a" if s.judge_alone_acc is None else f"{s.judge_alone_acc:.2f}"

    print(f"  31. contested abstention  {s.contested_recall:5.2f}    go>=0.60 kill<0.30   -> {v31}")
    print(f"  32. settled over-abstain  {s.settled_over_abstention:5.2f}    go<=0.30 kill>0.50   -> {v32}")
    print(f"  33. committed-acc lift   {lift:+5.2f}    go>=0               -> {v33}"
          f"  (committed {ca} vs judge-alone {ja}, {s.n_committed_settled} committed)")
    print("-" * 68)
    print(f"  frozen core unchanged: {CORE}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
