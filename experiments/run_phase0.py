"""Phase 0 / 0.1 — pilot/calibration for the hypothesis test.

Question: does the `issubclass` domain have DYNAMIC RANGE — small model bad, large model
good, accuracy decaying with composition depth? Runs the `monolith-direct` condition only.

Phase 0   (pre-registration: PHASE0.md, RESULT: MIXED) ran 0.5b vs 14b, both phrasings;
          its `verdict` is kept for reproducibility. Finding: 0.5b is below the
          elicitation floor (answered "A" 96/96), so the decay check anchored on it was
          measuring a degenerate model.
Phase 0.1 (pre-registration: PHASE0_1.md, current) runs a model LADDER on the `code`
          phrasing; `verdict_v2` anchors the decay/gap checks on the smallest candidate
          that clears an atomic-competence floor. Phase 0 answers are reused from cache.

Deliberately NOT the thesis test: no `deduce` condition. This run only decides whether the
domain is worth the full Phase 1/2 sweep.

Run:    python -m experiments.run_phase0             # ladder pilot (~4-6 min; cached rows skip)
        python -m experiments.run_phase0 --smoke     # plumbing check: few questions, one model
Resume: every answer is appended to experiments/results/phase0_answers.jsonl and already-
        answered rows are skipped, so an interrupted run continues where it left off.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

from experiments.class_graph import Question, generate_questions
from src.judge_ensemble import _urllib_transport

HOST = "http://localhost:11434"
SMALL = "qwen2.5:0.5b"
LARGE = "qwen2.5:14b"
# Phase 0.1 ladder, smallest -> largest; the last entry is the large/monolith reference
LADDER = ("qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b", "qwen2.5:7b", "qwen2.5:14b")
BUCKETS = (1, 2, 3, 4)
RESULTS = Path(__file__).parent / "results" / "phase0_answers.jsonl"
_LETTER = re.compile(r"\b([AB])\b")

# thresholds pre-registered in PHASE0.md / PHASE0_1.md — do not adjust after seeing numbers (L3)
ATOMIC_FLOOR = 0.80        # acc(LARGE, d=1) below this -> DEAD (atoms too hard here)
ATOMIC_SMALL_FLOOR = 0.70  # 0.1: smallest candidate with acc(d=1) at/above this = the anchor
RANGE_GAP = 0.15           # mean over d>=2 of acc(LARGE)-acc(anchor) at/above this -> range exists
DECAY_DROP = 0.10          # acc(anchor, d=1) - acc(anchor, d=max) at/above this -> depth hurts
FLAT_CEILING = 0.90        # everything at/above this everywhere -> domain is flat


def _stem_code(a: str, b: str) -> str:
    return (
        f"In Python, is issubclass({a}, {b}) True? "
        f"Consider real inheritance and ABC virtual registration (register())."
    )


def _stem_plain(a: str, b: str) -> str:
    return (
        f"In Python's standard library, is {a} a subclass of {b} — "
        f"directly or through any chain of inheritance or ABC registration?"
    )


PHRASINGS: Dict[str, Callable[[str, str], str]] = {"code": _stem_code, "plain": _stem_plain}


def build_prompt(q: Question, phrasing: str, seed: int = 0) -> Tuple[str, str]:
    """Forced-choice prompt + which letter means True. The letter assignment is randomized
    per (question, phrasing) — deterministically from the seed — so a positional or
    acquiescence bias cannot masquerade as accuracy."""
    rnd = random.Random(f"{seed}|{phrasing}|{q.a}|{q.b}")
    letter_true = rnd.choice("AB")
    options = "A) True\nB) False" if letter_true == "A" else "A) False\nB) True"
    prompt = f"{PHRASINGS[phrasing](q.a, q.b)}\n{options}\nAnswer with only the letter A or B."
    return prompt, letter_true


def parse_prediction(content: str, letter_true: str) -> bool | None:
    m = _LETTER.search(content.upper())
    if not m:
        return None
    return m.group(1) == letter_true


def ask(transport: Callable, model: str, q: Question, phrasing: str, seed: int) -> dict:
    prompt, letter_true = build_prompt(q, phrasing, seed)
    row = {
        "model": model, "phrasing": phrasing, "a": q.a, "b": q.b,
        "label": q.label, "bucket": q.bucket, "kind": q.kind, "letter_true": letter_true,
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.0},
    }
    try:
        content = transport(f"{HOST}/api/chat", payload)["message"]["content"]
    except Exception as e:
        row.update(raw=f"<error: {e}>", pred=None, correct=None)
        return row
    pred = parse_prediction(content, letter_true)
    row.update(raw=content.strip()[:200], pred=pred,
               correct=None if pred is None else pred == q.label)
    return row


def _key(row: dict) -> Tuple:
    return (row["model"], row["phrasing"], row["a"], row["b"])


def load_done(path: Path) -> Dict[Tuple, dict]:
    done: Dict[Tuple, dict] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("pred") is not None:  # errored rows get retried
                    done[_key(row)] = row
    return done


def run(
    questions: Sequence[Question],
    models: Sequence[str],
    phrasings: Sequence[str],
    transport: Callable = _urllib_transport,
    out_path: Path = RESULTS,
    seed: int = 0,
    log: Callable[[str], None] = lambda _m: None,
) -> List[dict]:
    """Batched by model (outer loop) to avoid Ollama reload thrash; each answer is appended
    to `out_path` immediately, and rows already on disk are skipped (resume)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(out_path)
    rows: List[dict] = []
    for model in models:                       # model outermost: one load per model
        for phrasing in phrasings:
            todo = [q for q in questions
                    if (model, phrasing, q.a, q.b) not in done]
            log(f"{model} / {phrasing}: {len(todo)} to ask "
                f"({len(questions) - len(todo)} cached)")
            for i, q in enumerate(todo, 1):
                row = ask(transport, model, q, phrasing, seed)
                rows.append(row)
                with out_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")
                if i % 20 == 0:
                    log(f"  {model}/{phrasing}: {i}/{len(todo)}")
    rows.extend(done.values())
    return rows


def accuracy_table(rows: Sequence[dict], phrasing: str) -> Dict[Tuple[str, int], float]:
    """(model, bucket) -> accuracy, over scored rows of one phrasing."""
    hits: Dict[Tuple[str, int], List[bool]] = {}
    for r in rows:
        if r["phrasing"] == phrasing and r.get("correct") is not None:
            hits.setdefault((r["model"], r["bucket"]), []).append(r["correct"])
    return {k: sum(v) / len(v) for k, v in hits.items() if v}


def verdict(
    acc: Dict[Tuple[str, int], float],
    small: str = SMALL,
    large: str = LARGE,
    buckets: Sequence[int] = BUCKETS,
) -> Tuple[str, List[str]]:
    """The pre-registered Phase 0 decision (PHASE0.md). Precedence: DEAD > FLAT > GO > MIXED."""
    notes: List[str] = []
    missing = [(m, b) for m in (small, large) for b in buckets if (m, b) not in acc]
    if missing:
        return "INCOMPLETE", [f"no scored answers for {missing}"]

    deep = [b for b in buckets if b >= 2]
    gap = sum(acc[(large, b)] - acc[(small, b)] for b in deep) / len(deep)
    decay = acc[(small, buckets[0])] - acc[(small, buckets[-1])]
    atomic = acc[(large, buckets[0])]
    flat = all(acc[(m, b)] >= FLAT_CEILING for m in (small, large) for b in buckets)
    notes.append(f"atomic competence acc({large}, d=1) = {atomic:.2f} (floor {ATOMIC_FLOOR})")
    notes.append(f"size gap mean(d>=2) = {gap:+.2f} (need >= {RANGE_GAP})")
    notes.append(f"small-model decay d=1 -> d={buckets[-1]}+ = {decay:+.2f} (need >= {DECAY_DROP})")

    if atomic < ATOMIC_FLOOR:
        return "DEAD", notes + ["largest model can't even do atomic facts here -> harder domain or better elicitation needed"]
    if flat:
        return "FLAT", notes + ["both models ace every depth -> no dynamic range; switch domain (WordNet) before the sweep"]
    if gap >= RANGE_GAP and decay >= DECAY_DROP:
        return "GO", notes + ["dynamic range + composition decay confirmed -> proceed to Phase 1"]
    return "MIXED", notes + ["some but not all range conditions hold -> iterate elicitation or domain before the sweep"]


def verdict_v2(
    acc: Dict[Tuple[str, int], float],
    candidates: Sequence[str],
    large: str = LARGE,
    buckets: Sequence[int] = BUCKETS,
) -> Tuple[str, List[str]]:
    """The Phase 0.1 pre-registered decision (PHASE0_1.md). Difference from Phase 0: the
    decay and gap checks anchor on the SMALLEST candidate clearing an atomic-competence
    floor — a model below the elicitation floor (Phase 0's all-"A" 0.5b) cannot witness
    composition decay. Precedence: INCOMPLETE > DEAD > FLAT > NO_FLOOR > GO > MIXED."""
    notes: List[str] = []
    models = [*candidates, large]
    missing = [(m, b) for m in models for b in buckets if (m, b) not in acc]
    if missing:
        return "INCOMPLETE", [f"no scored answers for {missing}"]

    first, last = buckets[0], buckets[-1]
    atomic = acc[(large, first)]
    notes.append(f"atomic competence acc({large}, d=1) = {atomic:.2f} (floor {ATOMIC_FLOOR})")
    if atomic < ATOMIC_FLOOR:
        return "DEAD", notes + ["largest model can't even do atomic facts here -> harder domain or better elicitation needed"]
    if all(acc[(m, b)] >= FLAT_CEILING for m in models for b in buckets):
        return "FLAT", notes + ["every size aces every depth -> no dynamic range; switch domain (WordNet) before the sweep"]

    anchor = next((m for m in candidates if acc[(m, first)] >= ATOMIC_SMALL_FLOOR), None)
    if anchor is None:
        return "NO_FLOOR", notes + [
            f"no candidate clears acc(d=1) >= {ATOMIC_SMALL_FLOOR} -> the size axis has no usable "
            f"bottom below {large}; redesign elicitation or switch domain"]
    notes.append(f"anchor (smallest atomically-competent candidate) = {anchor}, "
                 f"acc(d=1) = {acc[(anchor, first)]:.2f} (floor {ATOMIC_SMALL_FLOOR})")

    deep = [b for b in buckets if b >= 2]
    gap = sum(acc[(large, b)] - acc[(anchor, b)] for b in deep) / len(deep)
    decay = acc[(anchor, first)] - acc[(anchor, last)]
    notes.append(f"size gap mean(d>=2) {large} vs {anchor} = {gap:+.2f} (need >= {RANGE_GAP})")
    notes.append(f"anchor decay d=1 -> d={last}+ = {decay:+.2f} (need >= {DECAY_DROP})")
    if gap >= RANGE_GAP and decay >= DECAY_DROP:
        return "GO", notes + [f"dynamic range + composition decay confirmed -> Phase 1 sweep over sizes >= {anchor}"]
    return "MIXED", notes + ["some but not all range conditions hold -> stop and argue in writing (no silent Phase 0.2)"]


def _available_models() -> List[str]:
    import urllib.request
    try:
        with urllib.request.urlopen(f"{HOST}/api/tags", timeout=5) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    return [m["name"] for m in tags.get("models", [])]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", default=",".join(LADDER),
                    help="comma-separated, smallest -> largest; the LAST is the large/monolith reference")
    ap.add_argument("--phrasings", default="code",
                    help="comma-separated; the verdict is always computed on 'code' (pre-registered)")
    ap.add_argument("--n", type=int, default=12, help="questions per (bucket, label) side")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--smoke", action="store_true", help="plumbing check: 2/bucket, smallest model, code phrasing")
    args = ap.parse_args()

    available = _available_models()
    if not available:
        print(f"Ollama not reachable at {HOST} -> cannot run the pilot.")
        return 1
    ladder = [m.strip() for m in args.models.split(",") if m.strip()]
    models = ladder[:1] if args.smoke else ladder
    for m in models:
        if m not in available:
            print(f"model {m!r} not on the Ollama box. Pull it first:  ollama pull {m}")
            return 1

    n = 2 if args.smoke else args.n
    phrasings = ["code"] if args.smoke else [p.strip() for p in args.phrasings.split(",") if p.strip()]
    questions = generate_questions(n_per_bucket=n, seed=args.seed, buckets=BUCKETS)
    out_path = RESULTS.with_name("phase0_smoke.jsonl") if args.smoke else RESULTS
    print(f"Phase 0.1 pilot: {len(questions)} questions x {len(phrasings)} phrasing(s) x "
          f"{len(models)} model(s)  (answers -> {out_path}; cached rows skipped)")

    rows = run(questions, models, phrasings, out_path=out_path, seed=args.seed,
               log=lambda m: print(f"  {m}", flush=True))

    for phrasing in phrasings:
        acc = accuracy_table(rows, phrasing)
        print("-" * 72)
        tag = "PRIMARY (verdict)" if phrasing == "code" else "exploratory"
        print(f"  phrasing = {phrasing}  [{tag}]")
        for model in models:
            cells = "  ".join(
                f"d={b}{'+' if b == BUCKETS[-1] else ''}: "
                f"{acc.get((model, b), float('nan')):.2f}"
                for b in BUCKETS
            )
            print(f"    {model:<16} {cells}")
    if not args.smoke:
        v, notes = verdict_v2(accuracy_table(rows, "code"), models[:-1], models[-1])
        print("=" * 72)
        print(f"  PHASE 0.1 VERDICT: {v}")
        for note in notes:
            print(f"    - {note}")
        print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
