# Phase 0.2 pre-registration — atomic-extraction pilot (after the Phase 0.1 MIXED)

> The argued-in-writing follow-up PHASE0_1.md's MIXED rule demands (no silent
> reinterpretation). Written and committed BEFORE the run (L3); thresholds mirrored as
> constants in `run_phase0_2.py`.

## The argument (why this check, and why the 0.1 check asked the wrong question)

Phase 0.1 found a **verification cliff**, not a size gradient: sub-7b qwen2.5 is
format-competent but denies nearly every positive claim (3b: 0.00 on depth-1 true chains,
including `tuple -> object`), while 7b ≈ 14b (gap +0.01). The pre-registered gap check
therefore anchored on 7b and failed.

But the gap check conflated two capabilities. Phase 2's small base is **never asked the
composed question** — the design's own core rule (Validity Checklist item 1) is that the
model is only ever asked for depth-1 atoms, *in extraction form*. Extraction is
**generative**; the observed sub-7b failure is a **verification truth-value bias**. Whether
that bias transfers to generation is an empirical question this pilot answers — it is
Checklist item 7 (extraction accuracy measured separately from composition) pulled forward
to where it belongs: before the sweep.

The stakes for H2, both ways: sub-7b models sit at the 0.50 floor on the direct task while
14b-direct is ~0.85 — so if a sub-7b model CAN extract atoms, "small + extract + deduce ≥
large monolith" becomes a *dramatic* crossover; if none can, H2 is honestly dead in this
domain × family and only H1 survives here.

## Design (decides section-9 item 4)

- **Open generation, no candidate leak:** "list the direct base classes of {X} — exactly
  the contents of {X}.__bases__", temperature 0, one shot. Forced-choice over candidate
  parents is rejected: it leaks the answer set and inherits the verification bias this
  pilot exists to escape.
- **Parsing:** output matched (case-sensitively) against the ~127 known inventory names;
  qualified aliases always match, bare qualnames only when unambiguous
  (`Integral` → `numbers.Integral`; builtin `set` vs abc `Set` stay distinct);
  longest-alias-first so qualified mentions aren't double-counted. Names outside the
  inventory are invisible to the parser — acceptable because only inventory edges feed the
  deduce condition.
- **Gold = nominal `__bases__` edges** (inventory-restricted) — the only unambiguous
  meaning of "direct base classes." Known bound, stated: the 27 virtual (ABC-registration)
  edges are not probed here; Phase 1/2 must handle them separately (a registration-specific
  question, or oracle-provided).
- **Sample:** 60 classes (seeded, from the 117 with an in-inventory nominal base — the
  concrete `io` classes are excluded along with `object`: their real `__bases__` are
  private `_io._*IOBase` classes, so "direct base classes" has no in-inventory gold for
  them), full ladder → 300 calls, ≈ 6–8 min, batched by model, resumable
  (`experiments/results/phase0_2_answers.jsonl`).

## Scoring (pre-registered; the reason truth precision, not strict precision, gates)

| Metric | Definition | Why it gates |
|---|---|---|
| **Direct recall** | nominal gold edges found ÷ gold | chains need every link; missing direct edges are what break closure |
| **Truth precision** | matched names that are true ancestors (any depth) ÷ matched | only a FALSE edge corrupts closure; an ancestor edge (`bool -> object` for `bool`) is entailed-true and harmless, so it must not count against the model |
| Strict precision | exact direct-base matches ÷ matched | reported for the record, not gated |

**Extraction-competent at size s** = direct recall ≥ **0.70** AND truth precision ≥ **0.80**.

## Pre-registered verdict rules (`run_phase0_2.verdict_extraction`)

Precedence: **INCOMPLETE > DEAD > GO_FULL > GO_H1_ONLY.** The **H2 anchor** = the smallest
extraction-competent size on the ladder.

- **DEAD** — no size (14b included) is extraction-competent → the domain cannot feed the
  LLM↔solver seam at all; rethink domain or extraction elicitation.
- **GO_FULL** — the anchor is sub-7b (0.5b / 1.5b / 3b) → Phase 1/2 proceeds with BOTH
  hypotheses; H2's size axis runs anchor → 14b.
- **GO_H1_ONLY** — the anchor is 7b or 14b → Phase 1 tests H1 on 7b/14b (monolith vs rag
  vs deduce across depths — a real result on its own); H2 moves to WordNet or a
  cross-family ladder, argued in a fresh pre-registration.

## Predictions (recorded before the run, per L3)

- Generation ≠ verification: the sub-7b denial bias should NOT fully transfer — `__bases__`
  of stdlib classes is heavily memorized training data. 3b plausibly clears both floors;
  1.5b is the coin flip; 0.5b likely fails on truth precision (hallucinated parents).
- 7b/14b clear both floors comfortably (if not, something is wrong with the parser, not
  the models — check raw dumps before believing a DEAD).
- Honest priors: **GO_FULL ~50%, GO_H1_ONLY ~35%, DEAD ~5%, parser/format surprise
  requiring a fix-and-rerun ~10%.**

> **RESULT — Phase 0.2 run (2026-07-01), 60 classes × full ladder: DEAD — and it survives
> the instrument fix.** The as-run scoring WAS contaminated (the pre-registered 10%
> branch): models answer `builtins.OSError` etc., and the parser scored ~1/5 of 14b's
> correct rows as zero. Fixed at the decode layer only (strip `builtins.`, map private
> `_io.`/`_collections_abc.`, accept module-ish dotted prefixes); scoring now re-parses
> the persisted raw text, so the same answers were re-scored with **zero new model calls**
> (`--rescore`). Thresholds untouched. Re-scored, micro-averaged:
>
> | model | direct recall | truth precision | strict precision |
> |---|---|---|---|
> | 0.5b | 0.16 | 0.36 | 0.10 |
> | 1.5b | 0.31 | 0.41 | 0.25 |
> | 3b | 0.12 | 0.20 | 0.15 |
> | 7b | 0.29 | **0.79** | 0.33 |
> | 14b | **0.60** | 0.76 | 0.49 |
>
> No size clears either floor (0.70 recall / 0.80 truth precision) → **DEAD, honestly.**
>
> **The finding (the real payload):** generative enumeration of exact `__bases__` is far
> harder than depth-1 *verification* of the same knowledge — 14b verifies d=1 pairs at
> 0.88 (Phase 0.1) but reconstructs exact direct edges at 0.60, with half of what it emits
> true-but-indirect (truth precision 0.76 vs strict 0.49: it **flattens the hierarchy**,
> naming ancestors instead of parents, e.g. `IndexError -> Exception` skipping
> `LookupError`; plus direction errors like `numbers.Real` as a base of `numbers.Complex`).
> The models hold the hierarchy as a soft partial order, not as exact hops. This converges
> with M2's structure-drift finding and the witness-cut lessons: **LLMs emit semantically-
> true but structurally-imprecise facts** — a consistent failure shape across the whole
> project, now measured at five sizes.
>
> **Routing (per the DEAD remit "rethink domain/elicitation"):** Phase 2 (`atoms =
> extracted`) is blocked as designed — generative direct-edge extraction cannot feed the
> seam in this domain/family. Phase 1 (`atoms = oracle`) was NEVER blocked: it hands the
> true atomic edges to `rag-model` and `deduce` by construction and needs no extraction.
> So the argued next step is a **Phase 1 pre-registration testing H1 only** (7b/14b,
> monolith-direct vs rag-model vs deduce, N ≥ 100/cell, Wilson CIs) — supported by Phase
> 0.1's decay evidence. H2 stays open pending an extraction design that works (e.g.
> extraction-by-verification — which must first answer how to bound candidate pairs to
> depth-1 without leaking the answer set; argued in a fresh doc, not improvised).
