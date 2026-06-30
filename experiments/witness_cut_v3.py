"""Witness cut v3 — the Goldilocks regime.

v1 (yes/no probe) made a good witness look like garbage; v2 (Python builtins) made it look
perfect. Neither hit the regime the thesis is about: a witness that KNOWS a lot but is
genuinely UNRELIABLE, so deduction has real errors to catch and stability has variance to
read. This run picks an obscure-but-computable hierarchy: the `numbers` ABC tower
(bool < int < Integral < Rational < Real < Complex < Number) + collections.abc registration.
Ground truth is still free and external (issubclass, incl. virtual subclass registration).

Same harness as v2: forced-choice elicitation, stability-as-truth-proxy, consistency filter,
single model / K=3 to fit the 10-min budget. Question anchored on issubclass and names
qualified (numbers.Real) so the model isn't confused by the English words.

Pre-registered:
  raw ~0.5-0.8 (genuinely noisy)  -> finally the right regime.
  lift > 0                        -> deduction distills from a noisy witness (thesis supported).
  lift <= 0                       -> it doesn't, even with real errors to work on.
  crux: stability(true) > stability(false)  -> sampling-stability is a usable truth-proxy.
  raw still ~0.95                 -> structured knowledge is robustly in-weights; the
                                     apparatus is broadly redundant (anti-thesis; stop).

Run:  python -m experiments.witness_cut_v3
"""
from __future__ import annotations

import re
from collections.abc import Collection, Iterable, Sequence
from numbers import Complex, Integral, Number, Rational, Real
from typing import Callable, Dict, List, Tuple

from experiments.witness_cut import SCHEMA, CutScores, evaluate
from src.extraction_filter import consistency_filter
from src.inference_engine import InferenceEngine
from src.judge_ensemble import _urllib_transport
from src.knowledge_graph import Triple

Edge = Tuple[str, str]
MODEL = "qwen2.5:7b"
K = 3
TEMP = 0.9
HOST = "http://localhost:11434"
_LETTER = re.compile(r"\b([ABC])\b")

CLASSES: Dict[str, type] = {
    "bool": bool, "int": int, "float": float,
    "integral": Integral, "rational": Rational, "real": Real, "complex": Complex, "number": Number,
    "list": list, "str": str,
    "sequence": Sequence, "collection": Collection, "iterable": Iterable,
}
DISPLAY: Dict[str, str] = {
    "bool": "bool", "int": "int", "float": "float",
    "integral": "numbers.Integral", "rational": "numbers.Rational", "real": "numbers.Real",
    "complex": "numbers.Complex", "number": "numbers.Number",
    "list": "list", "str": "str",
    "sequence": "collections.abc.Sequence", "collection": "collections.abc.Collection",
    "iterable": "collections.abc.Iterable",
}


def ground_truth() -> set:
    names = list(CLASSES)
    return {(a, b) for a in names for b in names
            if a != b and issubclass(CLASSES[a], CLASSES[b])}


def _prompt(x: str, y: str) -> str:
    dx, dy = DISPLAY[x], DISPLAY[y]
    return (
        f"In Python, considering issubclass (including ABC registration), what is the "
        f"relationship between {dx} and {dy}?\n"
        f"A) issubclass({dx}, {dy}) is True\n"
        f"B) issubclass({dy}, {dx}) is True\n"
        f"C) neither\n"
        f"Answer with only the letter A, B, or C."
    )


def forced_choice_vote(transport: Callable, x: str, y: str) -> str | None:
    payload = {
        "model": MODEL,
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


def elicit_stable(transport: Callable, k: int = K,
                  log: Callable[[str], None] = lambda _m: None) -> List[Tuple[Edge, float]]:
    names = list(CLASSES)
    pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
    log(f"eliciting {MODEL} over {len(pairs)} pairs x {k} ...")
    out: List[Tuple[Edge, float]] = []
    for x, y in pairs:
        xy = yx = total = 0
        for _ in range(k):
            v = forced_choice_vote(transport, x, y)
            if v is None:
                continue
            total += 1
            xy += (v == "A")
            yx += (v == "B")
        if total == 0:
            continue
        if xy > total / 2:
            out.append(((x, y), xy / total))
        elif yx > total / 2:
            out.append(((y, x), yx / total))
    log("done")
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
    ordered = [Triple(a, "is_a", b) for (a, b), _ in sorted(elicited, key=lambda x: -x[1])]
    survivors = {(t.s, t.o) for t in consistency_filter(engine, [], ordered).kept}

    s = evaluate(asserted, survivors, truth)
    true_edges, false_edges = asserted & truth, asserted - truth
    st_true = sum(stab[e] for e in true_edges) / len(true_edges) if true_edges else 0.0
    st_false = sum(stab[e] for e in false_edges) / len(false_edges) if false_edges else 0.0

    print("=" * 68)
    print(f"  Witness cut v3  (numbers/abc tower; {MODEL}, k={K}, temp={TEMP})")
    print("=" * 68)
    print(f"  ground-truth edges={len(truth)}   asserted={s.n_asserted}   "
          f"survivors={s.n_survivors}   dropped={s.n_dropped}")
    print("-" * 68)
    print(f"  raw precision       {s.raw_precision:5.2f}   (recall {s.raw_recall:.2f})")
    print(f"  filtered precision  {s.filt_precision:5.2f}   (recall {s.filt_recall:.2f})")
    print(f"  lift                {s.lift:+5.2f}")
    print(f"  dropped: {s.good_drops} false (good) / {s.bad_drops} true (bad)")
    print("-" * 68)
    print(f"  CRUX: mean stability  true={st_true:.2f}  false={st_false:.2f}  "
          f"(proxy works iff true > false)")
    verdict = ("SIGNAL" if s.lift > 0.02 else "INERT" if s.lift >= -0.02 else "HARMFUL")
    proxy = "USABLE" if st_true > st_false + 0.05 else ("USELESS" if false_edges else "untestable")
    print(f"  -> filter: {verdict}   |   stability proxy: {proxy}")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
