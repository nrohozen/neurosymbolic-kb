"""Milestone 1 scorecard.

Computes the five M1 metrics against the draft thresholds in DIRECTION.md and prints a
verdict per metric. Metrics 2/3/5 need only clingo; metric 4 needs a local Ollama (if
unreachable it reports SKIPPED, not failed).

NOTE on metric 1 (closure leverage): leverage is a *descriptive* measure of how much the
deductive structure fans out for THIS schema + seed set — it is fan-out-dependent, not a
correctness measure. So the first run CALIBRATES its bar; it is not pass/failed here.
Metrics 2-5 are the genuine pre-committed gates (they're recall / accuracy / error rates,
which have principled bars regardless of the domain).

Run:  python -m eval.run_m1
"""
from __future__ import annotations

import json
from pathlib import Path

from src.inference_engine import InferenceEngine
from src.judge_ensemble import JudgeEnsemble
from src.knowledge_graph import KnowledgeGraph, Triple
from src.oracle import Claim, ExecutionOracle, JudgeEntailmentOracle, OracleRouter
from src.reference_impls import REFERENCE_IMPLS

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "ads.lp"
SEEDS = ROOT / "schema" / "seeds.jsonl"
CASES = ROOT / "eval" / "m1_cases.jsonl"


def _verdict(value: float, go: float, kill: float, higher_is_better: bool = True) -> str:
    if higher_is_better:
        if value >= go:
            return "GO"
        return "KILL" if value < kill else "MID"
    else:
        if value <= go:
            return "GO"
        return "KILL" if value > kill else "MID"


def main() -> int:
    engine = InferenceEngine.from_schema_file(SCHEMA)
    kg = KnowledgeGraph.from_seeds(SEEDS)
    seed_atoms = kg.atoms()

    try:
        base = engine.run([])
    except ImportError:
        print("clingo is not installed.  pip install -r requirements.txt")
        return 1

    full = engine.run(seed_atoms)
    if not full.satisfiable:
        print("ERROR: the seed set is itself inconsistent. Fix schema/seeds.jsonl first.")
        return 1

    cases = [json.loads(ln) for ln in CASES.read_text(encoding="utf-8").splitlines() if ln.strip()]
    comp = [c for c in cases if c["type"] == "comparison"]
    conc = [c for c in cases if c["type"] == "conceptual"]
    contra = [c for c in cases if c["type"] == "contradiction"]
    consist = [c for c in cases if c["type"] == "consistent"]

    # --- metric 1: closure leverage (descriptive / calibration) ---
    derived = set(full.atoms) - set(base.atoms) - set(seed_atoms)
    leverage = len(derived) / max(1, len(seed_atoms))

    # --- metric 2: contradiction recall (zero LLM calls) ---
    caught = sum(
        not engine.is_consistent(seed_atoms + [Triple(*f).as_atom() for f in c["facts"]])
        for c in contra
    )
    recall = caught / len(contra) if contra else 0.0

    # --- metric 3: comparison accuracy via deductive closure ---
    comp_correct = sum(
        engine.entails(seed_atoms, Triple(c["s"], "faster_than", c["o"]).as_atom()) == c["gold"]
        for c in comp
    )
    comp_acc = comp_correct / len(comp) if comp else 0.0

    # --- metric 5: false-contradiction rate ---
    false_flags = sum(
        not engine.is_consistent(seed_atoms + [Triple(*f).as_atom() for f in c["facts"]])
        for c in consist
    )
    fcr = false_flags / len(consist) if consist else 0.0

    # --- metric 4: conceptual-claim adjudication (weak oracle; needs Ollama) ---
    router = OracleRouter([JudgeEntailmentOracle(JudgeEnsemble())])
    conc_total = conc_correct = conc_unknown = 0
    for c in conc:
        verdict = router.adjudicate(Claim(Triple(c["s"], "has_property", c["p"]), kind="conceptual"))
        if verdict.holds is None:
            conc_unknown += 1
            continue
        conc_total += 1
        conc_correct += int(verdict.holds == c["gold"])
    conc_acc = (conc_correct / conc_total) if conc_total else None

    # --- bonus: execution oracle cross-checks the deductive comparisons it can run ---
    exo = ExecutionOracle(REFERENCE_IMPLS)
    exec_checked = exec_agree = 0
    for c in comp:
        claim = Claim(Triple(c["s"], "faster_than", c["o"]), kind="performance")
        if not exo.handles(claim):
            continue
        try:
            v = exo.adjudicate(claim)
        except Exception:
            continue
        if v.holds is None:
            continue
        exec_checked += 1
        exec_agree += int(v.holds == c["gold"])

    # --- scorecard ---
    print("=" * 68)
    print("  Milestone 1 scorecard  (domain 1: algorithms & data structures)")
    print("=" * 68)
    print(f"  seeds={len(seed_atoms)}  derived-from-seeds={len(derived)}  "
          f"cases: {len(comp)} comp / {len(conc)} conc / {len(contra)} contra / {len(consist)} consist")
    print("-" * 68)
    print(f"  1. closure leverage      {leverage:5.2f}x   [CALIBRATE - descriptive, not gated]")
    print(f"  2. contradiction recall  {recall:5.2f}    go>=0.90 kill<0.60   -> {_verdict(recall, 0.90, 0.60)}")
    print(f"  3. comparison accuracy   {comp_acc:5.2f}    go>=0.90 kill<0.50   -> {_verdict(comp_acc, 0.90, 0.50)}")
    if conc_acc is None:
        print(f"  4. conceptual adjudic.    n/a    go>=0.80 kill<0.60   -> SKIPPED "
              f"(no Ollama; {conc_unknown} unknown)")
    else:
        print(f"  4. conceptual adjudic.   {conc_acc:5.2f}    go>=0.80 kill<0.60   -> "
              f"{_verdict(conc_acc, 0.80, 0.60)}  ({conc_total} scored, {conc_unknown} unknown)")
    print(f"  5. false-contradiction   {fcr:5.2f}    go<=0.10 kill>0.25   -> "
          f"{_verdict(fcr, 0.10, 0.25, higher_is_better=False)}")
    print("-" * 68)
    if exec_checked:
        print(f"  bonus: execution oracle agrees with deduction on "
              f"{exec_agree}/{exec_checked} runnable comparisons")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
