"""Milestone 2-filter scorecard: isolating the consistency-filter claim (metrics 10-12).

Feeds labeled candidate triples (eval/m2_filter_cases.jsonl) straight to the deductive
filter -- no extractor, so canonicalization noise can't confound the signal. Fully offline
and deterministic (clingo only). Tests whether the deductive immune system that caught
planted contradictions in M1 also catches contradiction-shaped EXTRACTION errors here.

The scoring (`evaluate_filter`) is pure and unit-tested; `main` just prints the verdict.

Run:  python -m eval.run_m2_filter
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from eval.filter_cases import FilterCase, load_filter_cases
from eval.run_m1 import _verdict
from src.extraction_filter import consistency_filter
from src.inference_engine import InferenceEngine
from src.knowledge_graph import KnowledgeGraph

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "ads.lp"
SEEDS = ROOT / "schema" / "seeds.jsonl"


@dataclass
class FilterScores:
    n_true: int
    n_contra: int
    n_consistent: int
    n_total: int
    catch_rate: float          # metric 10: contradiction-shaped errors dropped
    false_drop_rate: float     # metric 11: true facts wrongly dropped
    consistent_dropped: int    # ceiling: error_consistent the filter cannot catch
    precision_raw: float
    precision_filt: float
    lift: float                # metric 12


def evaluate_filter(
    engine: InferenceEngine,
    seed_atoms: Sequence[str],
    cases: Sequence[FilterCase],
) -> FilterScores:
    label_of = {c.triple.as_atom(): c.label for c in cases}
    candidates = [c.triple for c in cases]

    fr = consistency_filter(engine, seed_atoms, candidates)
    kept = {t.as_atom() for t in fr.kept}
    dropped = {t.as_atom() for t in fr.dropped}

    n_true = sum(1 for c in cases if c.label == "true")
    n_contra = sum(1 for c in cases if c.label == "error_contradictory")
    n_consistent = sum(1 for c in cases if c.label == "error_consistent")
    n_total = len(cases)

    caught = sum(1 for a in dropped if label_of[a] == "error_contradictory")
    true_dropped = sum(1 for a in dropped if label_of[a] == "true")
    consistent_dropped = sum(1 for a in dropped if label_of[a] == "error_consistent")

    kept_true = sum(1 for a in kept if label_of[a] == "true")
    precision_raw = n_true / n_total if n_total else 0.0
    precision_filt = kept_true / len(kept) if kept else 0.0

    return FilterScores(
        n_true=n_true,
        n_contra=n_contra,
        n_consistent=n_consistent,
        n_total=n_total,
        catch_rate=caught / n_contra if n_contra else 0.0,
        false_drop_rate=true_dropped / n_true if n_true else 0.0,
        consistent_dropped=consistent_dropped,
        precision_raw=precision_raw,
        precision_filt=precision_filt,
        lift=precision_filt - precision_raw,
    )


def main() -> int:
    engine = InferenceEngine.from_schema_file(SCHEMA)
    try:
        engine.run([])
    except ImportError:
        print("clingo is not installed.  pip install -r requirements.txt")
        return 1

    seed_atoms = KnowledgeGraph.from_seeds(SEEDS).atoms()
    cases = load_filter_cases()
    s = evaluate_filter(engine, seed_atoms, cases)

    v10 = _verdict(s.catch_rate, 0.95, 0.80)
    v11 = _verdict(s.false_drop_rate, 0.00, 0.05, higher_is_better=False)
    v12 = "GO" if s.lift > 0 else "KILL"

    print("=" * 68)
    print("  Milestone 2-filter scorecard  (isolating the consistency filter)")
    print("=" * 68)
    print(f"  candidates={s.n_total}  ({s.n_true} true / {s.n_contra} contradictory / "
          f"{s.n_consistent} consistent-error)  seeds={len(seed_atoms)}")
    print("-" * 68)
    print(f"  10. error-catch rate     {s.catch_rate:5.2f}    go>=0.95 kill<0.80   -> {v10}")
    print(f"  11. false-drop rate      {s.false_drop_rate:5.2f}    go=0.00  kill>0.05   -> {v11}")
    print(f"  12. precision lift      {s.lift:+5.2f}    go>0                 -> {v12}")
    print("-" * 68)
    print(f"  precision {s.precision_raw:.2f} -> {s.precision_filt:.2f} (zero LLM calls); "
          f"ceiling: {s.consistent_dropped}/{s.n_consistent} consistent-errors caught "
          f"(by design the filter cannot catch these)")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
