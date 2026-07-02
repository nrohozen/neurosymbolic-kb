"""Phase 1 — the H1 composition-gap test with oracle atoms (pre-registration: PHASE1.md).

Three conditions on the same 400-question balanced set (100 per depth bucket, seed 1):
- monolith-direct : the bare composed question (Phase 0's `code` instrument, unchanged).
- rag-model       : the true atomic edges (+ true-but-irrelevant distractors) presented
                    in-context; the model composes.
- deduce          : the SAME fact block, composed by the inference engine — zero LLM.

H2 is shelved (Phase 0.2 DEAD), so this runs 7b + 14b only; Validity Checklist item 5 is
waived in writing in PHASE1.md. Cost (tokens, duration) is recorded per row (item 8).

Run:    python -m experiments.run_phase1                      # full (~45-60 min, resumable)
        python -m experiments.run_phase1 --conditions deduce  # the free condition first
        python -m experiments.run_phase1 --smoke              # plumbing: few questions, 7b
Resume: rows append to experiments/results/phase1_answers.jsonl; answered rows skip.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from experiments.class_graph import Question, class_graph, generate_questions
from experiments.run_phase0 import HOST, _available_models, build_prompt, parse_prediction
from src.inference_engine import InferenceEngine
from src.judge_ensemble import _urllib_transport
from src.knowledge_graph import normalize

RESULTS = Path(__file__).parent / "results" / "phase1_answers.jsonl"
MODELS = ("qwen2.5:7b", "qwen2.5:14b")
PRIMARY = "qwen2.5:14b"          # pre-registered: the claim is against the strongest monolith
BUCKETS = (1, 2, 3, 4)
N_PER_BUCKET = 50
SEED = 1                          # fresh draw; seed 0 was the diagnosed pilot set
FACTS_PER_QUESTION = 30

# pre-registered thresholds (PHASE1.md) — do not adjust after seeing numbers (L3)
DEDUCE_CEILING = 0.95   # acc_deduce(4+) below this -> INVALID (harness bug, not a finding)
MONO_DECAY = 0.10       # acc_mono(1) - acc_mono(4+) at/above this -> depth hurts the monolith
GAP_GROWTH = 0.10       # gap(4+) - gap(1) at/above this -> H1 supported

# the deductive core, reused untouched: transitive closure over presented atomic edges
SUBCLASS_ASP = """\
reaches(X,Y) :- edge(X,Y).
reaches(X,Z) :- edge(X,Y), reaches(Y,Z).
#show reaches/2.
"""


# ---------- the shared fact block (atoms = oracle) ----------

def relevant_edges(q: Question) -> List[Tuple[str, str]]:
    """Every direct edge within the ancestor sets of both question entities — so for a
    true pair the full chain is present by construction."""
    g = class_graph()
    nodes = {q.a, q.b}
    nodes.update(y for (x, y) in g.true_pairs if x == q.a or x == q.b)
    return sorted((x, y) for x in nodes for y in g.edges[x] if y in nodes)


def fact_set(q: Question, seed: int = SEED) -> List[Tuple[str, str]]:
    """Relevant edges padded to FACTS_PER_QUESTION with distractors — TRUE but irrelevant
    edges (false facts would corrupt `deduce` just as much as the model), deterministically
    shuffled per question."""
    g = class_graph()
    rel = relevant_edges(q)
    rel_set = set(rel)
    pool = sorted((x, y) for x, es in g.edges.items() for y in es if (x, y) not in rel_set)
    rnd = random.Random(f"{seed}|facts|{q.a}|{q.b}")
    facts = rel + rnd.sample(pool, min(max(0, FACTS_PER_QUESTION - len(rel)), len(pool)))
    rnd.shuffle(facts)
    return facts


def deduce_answer(q: Question, facts: Sequence[Tuple[str, str]]) -> bool:
    engine = InferenceEngine(SUBCLASS_ASP)
    atoms = [f"edge({normalize(x)},{normalize(y)})" for x, y in facts]
    return engine.entails(atoms, f"reaches({normalize(q.a)},{normalize(q.b)})")


def rag_prompt(q: Question, facts: Sequence[Tuple[str, str]], seed: int = SEED) -> Tuple[str, str]:
    rnd = random.Random(f"{seed}|rag|{q.a}|{q.b}")
    letter_true = rnd.choice("AB")
    options = "A) True\nB) False" if letter_true == "A" else "A) False\nB) True"
    lines = "\n".join(f"- {x} -> {y}" for x, y in facts)
    prompt = (
        "Facts about Python classes: each line 'X -> Y' means X is a DIRECT subclass of Y.\n"
        f"{lines}\n\n"
        f"Using ONLY these facts, is {q.a} a subclass of {q.b} "
        f"(directly or through a chain of the facts above)?\n"
        f"{options}\nAnswer with only the letter A or B."
    )
    return prompt, letter_true


# ---------- running ----------

def _base_row(q: Question, model: str, condition: str) -> dict:
    return {"model": model, "condition": condition, "a": q.a, "b": q.b,
            "label": q.label, "bucket": q.bucket, "kind": q.kind}


def ask_llm(transport: Callable, model: str, q: Question, condition: str, seed: int = SEED) -> dict:
    if condition == "monolith":
        prompt, letter_true = build_prompt(q, "code", seed)   # the pilot's exact instrument
    else:
        prompt, letter_true = rag_prompt(q, fact_set(q, seed), seed)
    row = _base_row(q, model, condition)
    row["letter_true"] = letter_true
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.0},
    }
    try:
        resp = transport(f"{HOST}/api/chat", payload)
        content = resp["message"]["content"]
    except Exception as e:
        row.update(raw=f"<error: {e}>", pred=None, correct=None)
        return row
    pred = parse_prediction(content, letter_true)
    row.update(
        raw=content.strip()[:200],
        pred=pred,
        correct=None if pred is None else pred == q.label,
        prompt_tokens=resp.get("prompt_eval_count"),
        gen_tokens=resp.get("eval_count"),
        duration_ns=resp.get("total_duration"),
    )
    return row


def deduce_row(q: Question, seed: int = SEED) -> dict:
    pred = deduce_answer(q, fact_set(q, seed))
    row = _base_row(q, "deduce", "deduce")
    row.update(raw="", pred=pred, correct=pred == q.label,
               prompt_tokens=0, gen_tokens=0, duration_ns=0)
    return row


def _key(row: dict) -> Tuple:
    return (row["model"], row["condition"], row["a"], row["b"])


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
    conditions: Sequence[str],
    transport: Callable = _urllib_transport,
    out_path: Path = RESULTS,
    seed: int = SEED,
    log: Callable[[str], None] = lambda _m: None,
) -> List[dict]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(out_path)
    rows: List[dict] = []

    def emit(row: dict) -> None:
        rows.append(row)
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    if "deduce" in conditions:
        todo = [q for q in questions if ("deduce", "deduce", q.a, q.b) not in done]
        log(f"deduce: {len(todo)} questions (zero LLM calls; {len(questions) - len(todo)} cached)")
        for q in todo:
            emit(deduce_row(q, seed))
    for model in models:                                   # model outermost: one load each
        for condition in [c for c in conditions if c != "deduce"]:
            todo = [q for q in questions if (model, condition, q.a, q.b) not in done]
            log(f"{model} / {condition}: {len(todo)} to ask "
                f"({len(questions) - len(todo)} cached)")
            for i, q in enumerate(todo, 1):
                emit(ask_llm(transport, model, q, condition, seed))
                if i % 25 == 0:
                    log(f"  {model}/{condition}: {i}/{len(todo)}")
    rows.extend(done.values())
    return rows


# ---------- scoring ----------

def wilson(p: float, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def accuracy_table(rows: Sequence[dict]) -> Dict[Tuple[str, str, int], Tuple[float, int]]:
    """(model, condition, bucket) -> (accuracy, n) over scored rows."""
    hits: Dict[Tuple[str, str, int], List[bool]] = defaultdict(list)
    for r in rows:
        if r.get("correct") is not None:
            hits[(r["model"], r["condition"], r["bucket"])].append(r["correct"])
    return {k: (sum(v) / len(v), len(v)) for k, v in hits.items()}


def cost_table(rows: Sequence[dict]) -> Dict[Tuple[str, str], Dict[str, float]]:
    """(model, condition) -> mean tokens / total wall-seconds (Checklist item 8)."""
    agg: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for r in rows:
        if r.get("pred") is not None and r.get("duration_ns") is not None:
            agg[(r["model"], r["condition"])].append(r)
    out = {}
    for k, rs in agg.items():
        out[k] = {
            "mean_prompt_tokens": sum(r.get("prompt_tokens") or 0 for r in rs) / len(rs),
            "mean_gen_tokens": sum(r.get("gen_tokens") or 0 for r in rs) / len(rs),
            "total_seconds": sum(r.get("duration_ns") or 0 for r in rs) / 1e9,
        }
    return out


def verdict_h1(
    acc: Dict[Tuple[str, str, int], Tuple[float, int]],
    primary: str = PRIMARY,
    buckets: Sequence[int] = BUCKETS,
) -> Tuple[str, List[str]]:
    """The pre-registered Phase 1 decision (PHASE1.md), on the PRIMARY model.
    Precedence: INCOMPLETE > INVALID > H1_SUPPORTED > H1_FALSIFIED > MIXED."""
    first, last = buckets[0], buckets[-1]
    notes: List[str] = []
    needed = [("deduce", "deduce", b) for b in (first, last)] + \
             [(primary, "monolith", b) for b in (first, last)]
    missing = [k for k in needed if k not in acc]
    if missing:
        return "INCOMPLETE", [f"no scored answers for {missing}"]

    ded1, ded4 = acc[("deduce", "deduce", first)][0], acc[("deduce", "deduce", last)][0]
    mono1, mono4 = acc[(primary, "monolith", first)][0], acc[(primary, "monolith", last)][0]
    decay = mono1 - mono4
    growth = (ded4 - mono4) - (ded1 - mono1)
    notes.append(f"deduce ceiling acc(d={last}+) = {ded4:.2f} (need >= {DEDUCE_CEILING})")
    notes.append(f"monolith decay ({primary}) d=1 -> d={last}+ = {decay:+.2f} (need >= {MONO_DECAY})")
    notes.append(f"gap growth = gap(d={last}+) {ded4 - mono4:+.2f} - gap(d=1) {ded1 - mono1:+.2f} "
                 f"= {growth:+.2f} (need >= {GAP_GROWTH})")

    rag_key = (primary, "rag", last)
    if rag_key in acc:
        rag4 = acc[rag_key][0]
        if rag4 >= ded4 - 0.05:
            notes.append(f"FLAG: rag(d={last}+) = {rag4:.2f} tracks deduce ({ded4:.2f}) — "
                         f"in-context composition suffices; the solver's edge is robustness/cost")

    if ded4 < DEDUCE_CEILING:
        return "INVALID", notes + ["fact blocks are missing chains -> harness bug; fix before interpreting"]
    if decay >= MONO_DECAY and growth >= GAP_GROWTH:
        return "H1_SUPPORTED", notes + ["the gap between deduction and the monolith grows with depth"]
    if decay < 0.05 or growth <= 0:
        return "H1_FALSIFIED", notes + ["the monolith composes in-head, or deduction buys nothing that grows with depth"]
    return "MIXED", notes + ["between the bars -> stop and argue in writing"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--conditions", default="deduce,monolith,rag",
                    help="comma-separated subset of deduce,monolith,rag (resumable chunks)")
    ap.add_argument("--n", type=int, default=N_PER_BUCKET)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--smoke", action="store_true", help="plumbing: 3/bucket, 7b only, all conditions")
    args = ap.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    if args.smoke:
        models, n = models[:1], 3
    else:
        n = args.n

    if any(c != "deduce" for c in conditions):
        available = _available_models()
        if not available:
            print(f"Ollama not reachable at {HOST} -> only '--conditions deduce' can run.")
            return 1
        for m in models:
            if m not in available:
                print(f"model {m!r} not on the Ollama box. Pull it first:  ollama pull {m}")
                return 1

    questions = generate_questions(n_per_bucket=n, seed=args.seed, buckets=BUCKETS)
    out_path = RESULTS.with_name("phase1_smoke.jsonl") if args.smoke else RESULTS
    print(f"Phase 1: {len(questions)} questions, conditions={conditions}, models={models}  "
          f"(answers -> {out_path}; cached rows skipped)")

    rows = run(questions, models, conditions, out_path=out_path, seed=args.seed,
               log=lambda m: print(f"  {m}", flush=True))

    acc = accuracy_table(rows)
    print("-" * 78)
    lines = [("deduce", "deduce")] + [(m, c) for m in models for c in ("monolith", "rag")]
    for model, condition in lines:
        cells = []
        for b in BUCKETS:
            entry = acc.get((model, condition, b))
            if entry:
                p, cnt = entry
                lo, hi = wilson(p, cnt)
                cells.append(f"d={b}{'+' if b == BUCKETS[-1] else ''}: {p:.2f} [{lo:.2f},{hi:.2f}]")
        if cells:
            print(f"  {model:<12} {condition:<9} " + "  ".join(cells))
    costs = cost_table(rows)
    for k, c in sorted(costs.items()):
        print(f"  cost {k[0]}/{k[1]}: ~{c['mean_prompt_tokens']:.0f}+{c['mean_gen_tokens']:.0f} "
              f"tokens/q, {c['total_seconds']:.0f}s total")
    if not args.smoke:
        v, notes = verdict_h1(acc)
        print("=" * 78)
        print(f"  PHASE 1 VERDICT (primary={PRIMARY}): {v}")
        for note in notes:
            print(f"    - {note}")
        print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
