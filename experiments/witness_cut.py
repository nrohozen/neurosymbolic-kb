"""The cheap cut: does deductive cross-examination distill signal from a noisy LLM witness?

Witness  : a local model, asked "is every X a kind of Y?" over real Python classes.
Truth    : `issubclass` -- external, deterministic, transitive, NOT authored by us.
Examiner : the is_a schema (transitive+acyclic) + consistency_filter, fed the witness's
           "yes" edges in CONFIDENCE order. Keyless: it uses only the witness's own credence
           and logic, never the answer key.
Measure  : precision of raw assertions vs precision of the consistency-surviving set, graded
           against issubclass ONLY at the end.

Pre-registered reading (see DIRECTION discussion):
  filtered >> raw  -> deduction distills signal; the loop's verifier is sound.
  filtered ~= raw  -> witness rarely self-contradicts; errors are consistent-but-wrong;
                      the verifier has no purchase (the loop would launder noise).
  filtered <  raw  -> it drops true edges; actively harmful.

`evaluate` is pure and unit-tested; `main` does the live elicitation (needs Ollama).

Run:  python -m experiments.witness_cut
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

from src.extraction_filter import consistency_filter
from src.inference_engine import InferenceEngine
from src.judge_ensemble import JudgeEnsemble
from src.knowledge_graph import Triple

ROOT = Path(__file__).resolve().parent
SCHEMA = ROOT / "isa.lp"
MODEL = "qwen2.5:7b"

# Real classes spanning a deep exception chain, the numeric tower, and misc builtins. Names
# are unique lowercased; issubclass over the actual types is the (free, external) ground truth.
CLASSES: Dict[str, type] = {
    "object": object,
    "baseexception": BaseException,
    "exception": Exception,
    "arithmeticerror": ArithmeticError,
    "zerodivisionerror": ZeroDivisionError,
    "valueerror": ValueError,
    "typeerror": TypeError,
    "int": int,
    "bool": bool,
    "float": float,
    "str": str,
    "list": list,
    "dict": dict,
}

Edge = Tuple[str, str]


def ground_truth() -> Set[Edge]:
    names = list(CLASSES)
    return {
        (a, b)
        for a in names for b in names
        if a != b and issubclass(CLASSES[a], CLASSES[b])
    }


def isa_claim_text(t: Triple) -> str:
    return f"In Python, is every {t.s} a kind of (a subclass of) {t.o}?"


@dataclass
class CutScores:
    n_asserted: int
    raw_precision: float
    raw_recall: float
    n_survivors: int
    filt_precision: float
    filt_recall: float
    n_dropped: int
    good_drops: int   # dropped edges that were actually FALSE (correctly removed)
    bad_drops: int    # dropped edges that were actually TRUE (wrongly removed)
    lift: float       # filt_precision - raw_precision


def evaluate(asserted: Set[Edge], survivors: Set[Edge], truth: Set[Edge]) -> CutScores:
    raw_p = len(asserted & truth) / len(asserted) if asserted else 0.0
    raw_r = len(asserted & truth) / len(truth) if truth else 0.0
    filt_p = len(survivors & truth) / len(survivors) if survivors else 0.0
    filt_r = len(survivors & truth) / len(truth) if truth else 0.0
    dropped = asserted - survivors
    good = len(dropped - truth)   # removed a false edge -> good
    bad = len(dropped & truth)    # removed a true edge -> bad
    return CutScores(
        n_asserted=len(asserted), raw_precision=raw_p, raw_recall=raw_r,
        n_survivors=len(survivors), filt_precision=filt_p, filt_recall=filt_r,
        n_dropped=len(dropped), good_drops=good, bad_drops=bad, lift=filt_p - raw_p,
    )


def elicit(judge: JudgeEnsemble) -> List[Tuple[Edge, float]]:
    """Ask the witness every ordered pair; return [(edge, prob)] for the YES answers."""
    names = list(CLASSES)
    out: List[Tuple[Edge, float]] = []
    for a in names:
        for b in names:
            if a == b:
                continue
            prob = judge.score(Triple(a, "is_a", b))
            if prob is not None and prob >= 0.5:
                out.append(((a, b), prob))
    return out


def main() -> int:
    engine = InferenceEngine.from_schema_file(SCHEMA)
    try:
        engine.run([])
    except ImportError:
        print("clingo is not installed.  pip install -r requirements.txt")
        return 1

    truth = ground_truth()
    judge = JudgeEnsemble(models=[MODEL], claim_text=isa_claim_text)
    yes = elicit(judge)
    if not yes:
        print("no assertions elicited -> SKIPPED (is Ollama running at :11434?)")
        return 0

    asserted: Set[Edge] = {e for e, _ in yes}
    # cross-examine: feed edges high-confidence-first so conflicts drop the LEAST-trusted edge
    ordered = [Triple(a, "is_a", b) for (a, b), _ in sorted(yes, key=lambda x: -x[1])]
    kept = consistency_filter(engine, [], ordered).kept
    survivors: Set[Edge] = {(t.s, t.o) for t in kept}

    s = evaluate(asserted, survivors, truth)

    print("=" * 68)
    print(f"  Witness cut  (model={MODEL}, {len(CLASSES)} classes, truth=issubclass)")
    print("=" * 68)
    print(f"  ground-truth edges={len(truth)}   asserted (yes)={s.n_asserted}   "
          f"survivors={s.n_survivors}   dropped={s.n_dropped}")
    print("-" * 68)
    print(f"  raw precision       {s.raw_precision:5.2f}   (recall {s.raw_recall:.2f})")
    print(f"  filtered precision  {s.filt_precision:5.2f}   (recall {s.filt_recall:.2f})")
    print(f"  lift                {s.lift:+5.2f}")
    print("-" * 68)
    print(f"  of {s.n_dropped} dropped edges: {s.good_drops} were false (good drops), "
          f"{s.bad_drops} were true (bad drops)")
    verdict = ("SIGNAL (deduction distills)" if s.lift > 0.02 else
               "INERT (errors consistent-but-wrong)" if s.lift >= -0.02 else
               "HARMFUL (drops truths)")
    print(f"  -> {verdict}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
