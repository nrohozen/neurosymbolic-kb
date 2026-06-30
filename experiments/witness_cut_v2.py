"""Witness cut v2 — confound-controlled re-run.

Two principled fixes over v1 (which came out HARMFUL, but with a leading yes/no probe and
confidence as the tie-break):
  1. FORCED-CHOICE elicitation: per unordered pair, "A) X subclass of Y / B) Y subclass of X
     / C) neither" -- removes acquiescence, probes direction, abstains with no majority.
  2. STABILITY, not confidence, as the truth-proxy: sample across two decorrelated model
     families (qwen + gemma), K times at temperature; an edge's weight = how often independent
     samples agree on it (weight-of-evidence). The consistency filter breaks ties by stability.

Same external ground truth (issubclass) and same `evaluate` yardstick as v1.

Pre-registered reading:
  lift >= 0, recall retained  -> v1 negative was probe-induced; cross-examination can distill.
  lift <= 0 / recall collapse -> negative is robust; verifier can't distill even clean input.
  crux diagnostic: mean stability of TRUE asserted edges vs FALSE. If not higher, stability is
  as useless as confidence and the loop is dead regardless of elicitation.

Stochastic (temperature>0 by design). Run:  python -m experiments.witness_cut_v2
"""
from __future__ import annotations

import re
from typing import Callable, Dict, List, Tuple

from experiments.witness_cut import CLASSES, SCHEMA, evaluate, ground_truth
from src.extraction_filter import consistency_filter
from src.inference_engine import InferenceEngine
from src.judge_ensemble import _urllib_transport
from src.knowledge_graph import Triple

Edge = Tuple[str, str]
MODELS = ["qwen2.5:7b", "gemma2:9b"]
K = 3            # samples per (model, pair)
TEMP = 0.7
HOST = "http://localhost:11434"
_LETTER = re.compile(r"\b([ABC])\b")


def _prompt(x: str, y: str) -> str:
    return (
        f"In Python's class hierarchy, what is the relationship between {x} and {y}?\n"
        f"A) {x} is a subclass of {y}\n"
        f"B) {y} is a subclass of {x}\n"
        f"C) neither\n"
        f"Answer with only the letter A, B, or C."
    )


def forced_choice_vote(transport: Callable, model: str, x: str, y: str) -> str | None:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": _prompt(x, y)}],
        "stream": False,
        "options": {"temperature": TEMP},
    }
    try:
        content = transport(f"{HOST}/api/chat", payload)["message"]["content"]
    except Exception:
        return None
    m = _LETTER.search(content.upper())
    return m.group(1) if m else None


def elicit_stable(
    transport: Callable, models=MODELS, k: int = K, log: Callable[[str], None] = lambda _m: None,
) -> List[Tuple[Edge, float]]:
    """Forced-choice over every unordered pair, sampled k times per model. Batched BY MODEL
    (outer loop) so each model loads into Ollama once instead of thrashing on every call.
    Returns the majority-direction edges with their stability (agreement fraction)."""
    names = list(CLASSES)
    pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
    votes: Dict[Edge, List[int]] = {p: [0, 0, 0, 0] for p in pairs}  # xy, yx, neither, total
    for model in models:
        log(f"eliciting with {model} ({len(pairs)} pairs x {k}) ...")
        for x, y in pairs:
            for _ in range(k):
                v = forced_choice_vote(transport, model, x, y)
                if v is None:
                    continue
                rec = votes[(x, y)]
                rec[3] += 1
                rec[0 if v == "A" else 1 if v == "B" else 2] += 1
        log(f"  {model} done")

    out: List[Tuple[Edge, float]] = []
    for (x, y), (xy, yx, _neither, total) in votes.items():
        if total == 0:
            continue
        if xy > total / 2:
            out.append(((x, y), xy / total))
        elif yx > total / 2:
            out.append(((y, x), yx / total))
        # no majority -> abstain (genuinely unstable)
    return out


def main() -> int:
    engine = InferenceEngine.from_schema_file(SCHEMA)
    try:
        engine.run([])
    except ImportError:
        print("clingo is not installed.  pip install -r requirements.txt")
        return 1

    truth = ground_truth()
    elicited = elicit_stable(_urllib_transport, log=lambda m: print(f"  {m}", flush=True))
    if not elicited:
        print("no assertions elicited -> SKIPPED (is Ollama running at :11434?)")
        return 0

    asserted = {e for e, _ in elicited}
    stab: Dict[Edge, float] = dict(elicited)
    # cross-examine, breaking conflicts by STABILITY (highest agreement survives)
    ordered = [Triple(a, "is_a", b) for (a, b), _ in sorted(elicited, key=lambda x: -x[1])]
    kept = consistency_filter(engine, [], ordered).kept
    survivors = {(t.s, t.o) for t in kept}

    s = evaluate(asserted, survivors, truth)

    true_edges = asserted & truth
    false_edges = asserted - truth
    mean_stab_true = sum(stab[e] for e in true_edges) / len(true_edges) if true_edges else 0.0
    mean_stab_false = sum(stab[e] for e in false_edges) / len(false_edges) if false_edges else 0.0

    print("=" * 68)
    print(f"  Witness cut v2  (forced-choice, stability; models={MODELS}, k={K})")
    print("=" * 68)
    print(f"  ground-truth edges={len(truth)}   asserted={s.n_asserted}   "
          f"survivors={s.n_survivors}   dropped={s.n_dropped}")
    print("-" * 68)
    print(f"  raw precision       {s.raw_precision:5.2f}   (recall {s.raw_recall:.2f})  "
          f"[v1 raw was 0.26]")
    print(f"  filtered precision  {s.filt_precision:5.2f}   (recall {s.filt_recall:.2f})")
    print(f"  lift                {s.lift:+5.2f}")
    print(f"  dropped: {s.good_drops} false (good) / {s.bad_drops} true (bad)")
    print("-" * 68)
    print(f"  CRUX: mean stability  true={mean_stab_true:.2f}  false={mean_stab_false:.2f}  "
          f"(proxy works iff true > false)")
    verdict = ("SIGNAL" if s.lift > 0.02 else "INERT" if s.lift >= -0.02 else "HARMFUL")
    proxy = "USABLE" if mean_stab_true > mean_stab_false + 0.05 else "USELESS"
    print(f"  -> filter: {verdict}   |   stability proxy: {proxy}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
