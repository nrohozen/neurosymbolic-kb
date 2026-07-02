"""Phase 0.2 — atomic-extraction pilot (pre-registration: PHASE0_2.md).

Phase 0.1 found a verification CLIFF: sub-7b qwen2.5 denies almost every positive claim in
forced choice (3b denied `tuple -> object`), while 7b == 14b above the cliff. But Phase 2's
small base is never asked to verify — it is asked to EXTRACT atoms (Validity Checklist
item 1), which is generative. This pilot measures generative atomic extraction per size:
"list the direct base classes of X", scored against the computed graph. It is Checklist
item 7 (extraction accuracy measured separately) pulled forward, and it decides section-9
item 4: OPEN GENERATION, no candidate leak — parsing is tractable because output only needs
matching against the ~127 known inventory names.

Scoring (see PHASE0_2.md for the argument):
- direct recall   — nominal `__bases__` edges found / gold. Chains need every link, so this
                    is what decides whether closure can be BUILT at size s.
- truth precision — matched names that are true ancestors (any depth) / matched. An
                    ancestor edge (e.g. `bool -> object`) is entailed-true and harmless to
                    deductive closure, so it does not count against the model; only a FALSE
                    edge corrupts closure.
- strict precision (reported, not gated) — exact-direct-base matches / matched.

Run:    python -m experiments.run_phase0_2            # ladder pilot (~6-8 min)
        python -m experiments.run_phase0_2 --smoke    # plumbing check: few classes, one model
Resume: answers append to experiments/results/phase0_2_answers.jsonl; answered rows skip.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

from experiments.class_graph import class_graph
from experiments.run_phase0 import HOST, LADDER, _available_models
from src.judge_ensemble import _urllib_transport

RESULTS = Path(__file__).parent / "results" / "phase0_2_answers.jsonl"

# thresholds pre-registered in PHASE0_2.md — do not adjust after seeing numbers (L3)
RECALL_FLOOR = 0.70           # direct recall at/above this ...
TRUTH_PRECISION_FLOOR = 0.80  # ... AND truth precision at/above this = extraction-competent


@lru_cache(maxsize=1)
def alias_map() -> Dict[str, str]:
    """Case-sensitive alias -> inventory display name. Qualified names always map; a bare
    qualname (e.g. 'Integral' for 'numbers.Integral') maps only if it is unambiguous across
    the inventory (case-sensitive, so builtin 'set' and abc 'Set' stay distinct)."""
    g = class_graph()
    amap: Dict[str, str] = {}
    dropped: set = set()
    for name in g.names:
        amap[name] = name
        bare = name.rsplit(".", 1)[-1]
        if bare == name:
            continue
        if bare in amap and amap[bare] != name:
            dropped.add(bare)
        else:
            amap.setdefault(bare, name)
    for bare in dropped:
        amap.pop(bare, None)
    return amap


_BUILTINS_PREFIX = re.compile(r"(?i)\bbuiltins\s*\.\s*")
_PRIVATE_MODULE = re.compile(r"(?<![\w.])_(io|collections_abc)\.")


def _normalize_text(text: str) -> str:
    """Decode-layer normalization of module spellings the models actually emit (found in
    the Phase 0.2 raw dumps): 'builtins.X' -> 'X' (builtin display names carry no module
    prefix) and the private implementation modules '_io.' / '_collections_abc.' -> their
    public names."""
    text = _BUILTINS_PREFIX.sub("", text)
    return _PRIVATE_MODULE.sub(
        lambda m: "io." if m.group(1) == "io" else "collections.abc.", text
    )


def extract_names(text: str, exclude: str) -> List[str]:
    """Inventory names mentioned in `text`, longest-alias-first so 'collections.abc.Set'
    is not double-counted as bare 'Set'; the queried class itself is excluded. A bare
    qualname is accepted after a module-ish dotted prefix ('abc.Iterable',
    'unicodedata_errors.UnicodeError' — the class name is what matters), but not inside a
    larger identifier ('_OSError', 'Iterableprotocols' stay unmatched)."""
    text = _normalize_text(text)
    amap = alias_map()
    taken: List[Tuple[int, int]] = []
    found: Dict[str, None] = {}
    for alias in sorted(amap, key=len, reverse=True):
        for m in re.finditer(rf"(?<!\w){re.escape(alias)}(?!\w)", text):
            span = m.span()
            if any(s < span[1] and span[0] < e for s, e in taken):
                continue
            taken.append(span)
            found.setdefault(amap[alias], None)
    found.pop(exclude, None)
    return sorted(found)


def _prompt(cls_name: str) -> str:
    return (
        f"In Python, list the direct base classes of {cls_name} — exactly the contents of "
        f"{cls_name}.__bases__. Answer with only the class names, comma-separated "
        f"(qualified with their module if not builtin). No explanation."
    )


def eligible_classes() -> List[str]:
    """Classes with at least one in-inventory nominal base. Excluded: `object` (no bases)
    and the concrete `io` classes, whose real __bases__ are private `_io._*IOBase` classes
    outside the inventory (their public membership is virtual registration — unprobeable as
    "direct base classes" gold)."""
    g = class_graph()
    return [n for n in g.names if g.nominal_edges[n]]


def ask(transport: Callable, model: str, cls_name: str) -> dict:
    g = class_graph()
    row = {"model": model, "cls": cls_name, "gold": sorted(g.nominal_edges[cls_name])}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": _prompt(cls_name)}],
        "stream": False,
        "options": {"temperature": 0.0},
    }
    try:
        content = transport(f"{HOST}/api/chat", payload)["message"]["content"]
    except Exception as e:
        row.update(raw=f"<error: {e}>", matched=None)
        return row
    row.update(raw=content.strip()[:300], matched=extract_names(content, cls_name))
    return row


def load_done(path: Path) -> Dict[Tuple[str, str], dict]:
    done: Dict[Tuple[str, str], dict] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("matched") is not None:  # errored rows get retried
                    done[(row["model"], row["cls"])] = row
    return done


def run(
    classes: Sequence[str],
    models: Sequence[str],
    transport: Callable = _urllib_transport,
    out_path: Path = RESULTS,
    log: Callable[[str], None] = lambda _m: None,
) -> List[dict]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(out_path)
    rows: List[dict] = []
    for model in models:                       # model outermost: one load per model
        todo = [c for c in classes if (model, c) not in done]
        log(f"{model}: {len(todo)} classes to ask ({len(classes) - len(todo)} cached)")
        for i, cls_name in enumerate(todo, 1):
            row = ask(transport, model, cls_name)
            rows.append(row)
            with out_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            if i % 20 == 0:
                log(f"  {model}: {i}/{len(todo)}")
    rows.extend(done.values())
    return rows


def stats_by_model(rows: Sequence[dict]) -> Dict[str, Dict[str, float]]:
    """Micro-averaged direct recall / truth precision / strict precision per model.
    `matched` is RE-PARSED from the stored raw text, so a decoder fix re-scores past runs
    without new model calls — the raw transcript is the record; the stored `matched` is
    only what the parser saw at ask time. (Bound: raw is stored truncated to 300 chars,
    which only affects rambling degenerate answers.)"""
    g = class_graph()
    agg: Dict[str, List[int]] = defaultdict(lambda: [0, 0, 0, 0])  # gold_hit, gold, truth_hit, matched
    for r in rows:
        if r.get("matched") is None:
            continue
        gold, matched = set(r["gold"]), set(extract_names(r["raw"], r["cls"]))
        a = agg[r["model"]]
        a[0] += len(matched & gold)
        a[1] += len(gold)
        a[2] += sum(1 for m in matched if m in gold or (r["cls"], m) in g.true_pairs)
        a[3] += len(matched)
    return {
        m: {
            "direct_recall": gh / gt if gt else 0.0,
            "truth_precision": th / mt if mt else 0.0,
            "strict_precision": gh / mt if mt else 0.0,
            "n_matched": mt,
        }
        for m, (gh, gt, th, mt) in agg.items()
    }


def verdict_extraction(
    stats: Dict[str, Dict[str, float]], ladder: Sequence[str] = LADDER
) -> Tuple[str, List[str]]:
    """The pre-registered Phase 0.2 decision (PHASE0_2.md). The H2 anchor is the smallest
    size that extracts atoms (direct recall AND truth precision above their floors).
    Precedence: INCOMPLETE > DEAD > GO_FULL > GO_H1_ONLY."""
    notes: List[str] = []
    missing = [m for m in ladder if m not in stats]
    if missing:
        return "INCOMPLETE", [f"no scored rows for {missing}"]

    def competent(m: str) -> bool:
        s = stats[m]
        return s["direct_recall"] >= RECALL_FLOOR and s["truth_precision"] >= TRUTH_PRECISION_FLOOR

    for m in ladder:
        s = stats[m]
        notes.append(
            f"{m}: direct recall {s['direct_recall']:.2f} (floor {RECALL_FLOOR}), "
            f"truth precision {s['truth_precision']:.2f} (floor {TRUTH_PRECISION_FLOOR}), "
            f"strict precision {s['strict_precision']:.2f}"
        )
    anchor = next((m for m in ladder if competent(m)), None)
    if anchor is None:
        return "DEAD", notes + [
            f"not even {ladder[-1]} extracts atoms -> this domain cannot feed the seam; rethink domain/elicitation"]
    if anchor in ladder[-2:]:
        return "GO_H1_ONLY", notes + [
            f"only {anchor}+ extracts -> Phase 1 tests H1 on 7b/14b; H2 needs WordNet or a cross-family ladder"]
    return "GO_FULL", notes + [
        f"H2 anchor = {anchor} (sub-7b extraction works) -> Phase 1/2 with BOTH hypotheses"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", default=",".join(LADDER),
                    help="comma-separated, smallest -> largest")
    ap.add_argument("--n-classes", type=int, default=60, help="seeded sample size")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--smoke", action="store_true", help="plumbing check: 6 classes, smallest model")
    ap.add_argument("--rescore", action="store_true",
                    help="no model calls: re-parse the stored raw answers and re-print the scorecard/verdict")
    args = ap.parse_args()

    if args.rescore:
        ladder = [m.strip() for m in args.models.split(",") if m.strip()]
        rows = [json.loads(l) for l in RESULTS.read_text(encoding="utf-8").splitlines() if l.strip()]
        stats = stats_by_model(rows)
        present = [m for m in ladder if m in stats]
        print(f"Re-scored {len(rows)} stored answers (zero model calls).")
        for model in present:
            s = stats[model]
            print(f"  {model:<16} direct recall {s['direct_recall']:.2f}   "
                  f"truth precision {s['truth_precision']:.2f}   "
                  f"strict precision {s['strict_precision']:.2f}   (matched {s['n_matched']})")
        v, notes = verdict_extraction(stats, present)
        print("=" * 72)
        print(f"  PHASE 0.2 VERDICT (re-scored): {v}")
        for note in notes:
            print(f"    - {note}")
        print("=" * 72)
        return 0

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

    pool = eligible_classes()
    n = 6 if args.smoke else min(args.n_classes, len(pool))
    classes = random.Random(args.seed).sample(sorted(pool), n)
    out_path = RESULTS.with_name("phase0_2_smoke.jsonl") if args.smoke else RESULTS
    print(f"Phase 0.2 extraction pilot: {n} classes x {len(models)} model(s)  "
          f"(answers -> {out_path}; cached rows skipped)")

    rows = run(classes, models, out_path=out_path, log=lambda m: print(f"  {m}", flush=True))

    stats = stats_by_model(rows)
    print("-" * 72)
    for model in models:
        s = stats.get(model)
        if s:
            print(f"  {model:<16} direct recall {s['direct_recall']:.2f}   "
                  f"truth precision {s['truth_precision']:.2f}   "
                  f"strict precision {s['strict_precision']:.2f}   (matched {s['n_matched']})")
    if not args.smoke:
        v, notes = verdict_extraction(stats, models)
        print("=" * 72)
        print(f"  PHASE 0.2 VERDICT: {v}")
        for note in notes:
            print(f"    - {note}")
        print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
