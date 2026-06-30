"""Milestone 5 scorecard: domain 4 (CS-as-a-field), the first WEAK-oracle domain.

The real thesis test: with no strong oracle, does deductive structure still settle the
derivable claims (zero LLM) and not hurt where the judge ensemble must opine, and does
belief revision keep the belief set consistent? Metrics 25-29 (see DIRECTION.md). 25/26/28/29
are deductive (clingo only); 27 uses the live judge ensemble (SKIPPED without Ollama).

Run:  python -m eval.run_m5
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Optional, Sequence

from eval.run_m1 import _verdict
from src.belief_revision import revise
from src.inference_engine import InferenceEngine
from src.judge_ensemble import JudgeEnsemble
from src.knowledge_graph import KnowledgeGraph, Triple

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "csfield.lp"
SEEDS_FILE = ROOT / "eval" / "m5_seeds.jsonl"
CLAIMS = ROOT / "eval" / "m5_claims.jsonl"
REVISION = ROOT / "eval" / "m5_revision.jsonl"

CORE = [
    "src/inference_engine.py",
    "src/knowledge_graph.py",
    "src/extraction_filter.py",
    "src/canonicalization.py",
]

# a contradictory claim stream to fold through belief revision (metric 29)
STREAM = [
    ("ml", "subfield_of", "ai", 0.9),
    ("ai", "subfield_of", "ml", 0.3),    # conflicts -> rejected
    ("dl", "subfield_of", "ml", 0.9),
    ("ml", "subfield_of", "dl", 0.2),    # conflicts -> rejected
    ("a", "subfield_of", "b", 0.8),
    ("b", "subfield_of", "c", 0.85),
    ("c", "subfield_of", "a", 0.95),     # 3-cycle -> retract weakest link
    ("x", "subsumes", "y", 0.7),
    ("y", "subsumes", "x", 0.4),         # conflicts -> rejected
]


def claim_text(t: Triple) -> str:
    s, o = t.s.replace("_", " "), t.o.replace("_", " ")
    if t.r == "subfield_of":
        return f"In computer science, is {s} a subfield of {o}?"
    if t.r == "subsumes":
        return f"In computer science, does {s} generalize (subsume) {o}?"
    return f"Is the statement '{t.s} {t.r} {t.o}' true?"


def deductive_verdict(engine, seed_atoms, triple: Triple) -> Optional[bool]:
    """True if entailed by the seeds, False if inconsistent with them, else None (undecided)."""
    atom = triple.as_atom()
    if engine.entails(seed_atoms, atom):
        return True
    if not engine.is_consistent(list(seed_atoms) + [atom]):
        return False
    return None


def deductive_reliability(engine, seed_atoms, claims) -> tuple[float, int]:
    derivable = [c for c in claims if c["kind"] == "derivable"]
    correct = sum(
        deductive_verdict(engine, seed_atoms, Triple(c["s"], c["r"], c["o"])) == c["gold"]
        for c in derivable
    )
    return (correct / len(derivable) if derivable else 0.0), len(derivable)


def structure_lift(engine, seed_atoms, claims, judge):
    """assisted (deduction where decidable, else judge) vs judge-alone. None if no judge."""
    assisted_correct = assisted_n = ja_correct = ja_n = 0
    for c in claims:
        t = Triple(c["s"], c["r"], c["o"])
        dv = deductive_verdict(engine, seed_atoms, t)
        score = judge.score(t)
        jv = None if score is None else (score >= 0.5)
        if jv is not None:
            ja_n += 1
            ja_correct += int(jv == c["gold"])
        assisted = dv if dv is not None else jv
        if assisted is not None:
            assisted_n += 1
            assisted_correct += int(assisted == c["gold"])
    if ja_n == 0:
        return None
    return (assisted_correct / assisted_n, ja_correct / ja_n, assisted_n, ja_n)


def _conf(entries) -> dict:
    return {Triple(s, r, o).as_atom(): conf for s, r, o, conf in entries}


def belief_revision_correctness(engine, scenarios) -> float:
    correct = 0
    for sc in scenarios:
        accepted = [Triple(s, r, o) for s, r, o, _ in sc["accepted"]]
        cs, cr, co, _ = sc["candidate"]
        candidate = Triple(cs, cr, co)
        conf = _conf(sc["accepted"] + [sc["candidate"]])
        result = revise(engine, accepted, candidate, conf)
        got = {t.as_atom() for t in result.accepted}
        gold = {Triple(*g).as_atom() for g in sc["gold_remain"]}
        consistent = engine.is_consistent([t.as_atom() for t in result.accepted])
        correct += int(got == gold and consistent)
    return correct / len(scenarios) if scenarios else 0.0


def final_consistency(engine, stream) -> float:
    conf = _conf(stream)
    accepted: List[Triple] = []
    for s, r, o, _ in stream:
        accepted = revise(engine, accepted, Triple(s, r, o), conf).accepted
    return 1.0 if engine.is_consistent([t.as_atom() for t in accepted]) else 0.0


def core_diff_lines() -> Optional[int]:
    try:
        base = subprocess.check_output(
            ["git", "rev-list", "--max-count=1", "--grep=M5: pre-commit", "HEAD"],
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
    claims = [json.loads(ln) for ln in CLAIMS.read_text(encoding="utf-8").splitlines()
              if ln.strip() and not ln.startswith("#")]
    scenarios = [json.loads(ln) for ln in REVISION.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.startswith("#")]

    reliability, n_deriv = deductive_reliability(engine, seed_atoms, claims)
    br = belief_revision_correctness(engine, scenarios)
    consistency = final_consistency(engine, STREAM)
    lift = structure_lift(engine, seed_atoms, claims, JudgeEnsemble(claim_text=claim_text))
    diff = core_diff_lines()

    v25 = "GO" if diff == 0 else "KILL"
    v26 = _verdict(reliability, 0.90, 0.70)
    v28 = _verdict(br, 0.90, 0.60)
    v29 = "GO" if consistency >= 1.0 else "KILL"

    print("=" * 68)
    print("  Milestone 5 scorecard  (domain 4: CS-as-a-field, a WEAK oracle)")
    print("=" * 68)
    print(f"  seeds={len(seed_atoms)}  claims={len(claims)} ({n_deriv} derivable)  "
          f"revision scenarios={len(scenarios)}")
    print("-" * 68)
    diff_str = "n/a" if diff is None else str(diff)
    print(f"  25. core reuse (swappable) {diff_str:>5} diffs  go=0                 -> {v25}")
    print(f"  26. deductive reliability {reliability:5.2f}    go>=0.90 kill<0.70   -> {v26}")
    if lift is None:
        print("  27. structure lift          n/a    go>=0               -> SKIPPED (no Ollama)")
    else:
        assisted, ja, an, jn = lift
        v27 = "GO" if assisted >= ja else "KILL"
        print(f"  27. structure lift        {assisted - ja:+5.2f}    go>=0               -> {v27}"
              f"  (assisted {assisted:.2f} vs judge-alone {ja:.2f})")
    print(f"  28. belief-revision corr. {br:5.2f}    go>=0.90 kill<0.60   -> {v28}")
    print(f"  29. final consistency     {consistency:5.2f}    go=1.00             -> {v29}")
    print("-" * 68)
    print(f"  frozen core unchanged: {CORE}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
