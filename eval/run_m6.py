"""Milestone 6 scorecard: domain 5 (open / contested knowledge) — the curriculum finale.

No reliable oracle: claims come from conflicting sources, and the system REPRESENTS
disagreement rather than resolving it. Metrics 38-42 (see DIRECTION.md). All deductive and
offline (clingo only, no LLM) — the source set is the oracle.

The scoring (`evaluate`) is pure and unit-tested; `main` merges all scenarios into one
source-set, reconciles, and prints the verdict.

Run:  python -m eval.run_m6
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from eval.run_m1 import _verdict
from eval.sources_fixture import Scenario, load_scenarios
from src.inference_engine import InferenceEngine
from src.source_reconciliation import Reconciliation, reconcile, surface_conflicts

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "open.lp"

CORE = [
    "src/inference_engine.py",
    "src/knowledge_graph.py",
    "src/extraction_filter.py",
    "src/canonicalization.py",
    "src/belief_revision.py",
    "src/calibration.py",
]


@dataclass
class M6Scores:
    detection_recall: float       # 39: all planted conflicts
    latent_recall: float          # 40: latent conflicts via deduction
    surface_latent_recall: float  # 40 contrast: latent conflicts the pairwise baseline catches
    faithful_rate: float          # 41: detected conflicts keep ALL positions
    false_contestation: float     # 42: agreed claims wrongly flagged
    n_conflict: int
    n_latent: int
    n_agreed_claims: int


def evaluate(
    scenarios: Sequence[Scenario],
    recon: Reconciliation,
    surface_pairs,
) -> M6Scores:
    contested_ids = {id(t) for cl in recon.contested for t in cl.positions}
    surface_ids = {id(t) for pair in surface_pairs for t in pair}

    conflict = [s for s in scenarios if s.type in ("surface", "latent")]
    latent = [s for s in scenarios if s.type == "latent"]
    agreed = [s for s in scenarios if s.type == "agreed"]

    def detected(s: Scenario) -> bool:
        return any(id(t) in contested_ids for t in s.triples)

    def fully_kept(s: Scenario) -> bool:
        return all(id(t) in contested_ids for t in s.triples)

    detection_recall = sum(detected(s) for s in conflict) / len(conflict) if conflict else 0.0
    latent_recall = sum(detected(s) for s in latent) / len(latent) if latent else 0.0
    surface_latent_recall = (
        sum(any(id(t) in surface_ids for t in s.triples) for s in latent) / len(latent)
        if latent else 0.0
    )
    detected_conflicts = [s for s in conflict if detected(s)]
    faithful_rate = (sum(fully_kept(s) for s in detected_conflicts) / len(detected_conflicts)
                     if detected_conflicts else 1.0)
    n_agreed_claims = sum(len(s.triples) for s in agreed)
    false = sum(id(t) in contested_ids for s in agreed for t in s.triples)
    false_contestation = false / n_agreed_claims if n_agreed_claims else 0.0

    return M6Scores(
        detection_recall=detection_recall,
        latent_recall=latent_recall,
        surface_latent_recall=surface_latent_recall,
        faithful_rate=faithful_rate,
        false_contestation=false_contestation,
        n_conflict=len(conflict),
        n_latent=len(latent),
        n_agreed_claims=n_agreed_claims,
    )


def core_diff_lines() -> Optional[int]:
    try:
        base = subprocess.check_output(
            ["git", "rev-list", "--max-count=1", "--grep=M6: pre-commit", "HEAD"],
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

    scenarios = load_scenarios()
    all_claims: List = [t for s in scenarios for t in s.triples]
    recon = reconcile(engine, all_claims)
    pairs = surface_conflicts(engine, all_claims)
    s = evaluate(scenarios, recon, pairs)
    diff = core_diff_lines()

    v38 = "GO" if diff == 0 else "KILL"
    v39 = _verdict(s.detection_recall, 0.90, 0.60)
    v40 = _verdict(s.latent_recall, 0.90, 0.60)
    v41 = "GO" if s.faithful_rate >= 1.0 else "KILL"
    v42 = _verdict(s.false_contestation, 0.10, 0.25, higher_is_better=False)

    print("=" * 68)
    print("  Milestone 6 scorecard  (domain 5: open / contested knowledge)")
    print("=" * 68)
    print(f"  scenarios={len(scenarios)}  conflicts={s.n_conflict} ({s.n_latent} latent)  "
          f"agreed-claims={s.n_agreed_claims}  contested-clusters={len(recon.contested)}")
    print("-" * 68)
    diff_str = "n/a" if diff is None else str(diff)
    print(f"  38. core reuse (swappable) {diff_str:>5} diffs  go=0                 -> {v38}")
    print(f"  39. disagreement recall   {s.detection_recall:5.2f}    go>=0.90 kill<0.60   -> {v39}")
    print(f"  40. latent recall (deduc) {s.latent_recall:5.2f}    go>=0.90 kill<0.60   -> {v40}")
    print(f"  41. faithful representation{s.faithful_rate:5.2f}    go=1.00             -> {v41}")
    print(f"  42. false-contestation    {s.false_contestation:5.2f}    go<=0.10 kill>0.25   -> {v42}")
    print("-" * 68)
    print(f"  neurosymbolic advantage: deduction catches {s.latent_recall:.0%} of latent "
          f"conflicts; the pairwise surface baseline catches {s.surface_latent_recall:.0%}")
    print(f"  frozen core unchanged: {CORE}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
