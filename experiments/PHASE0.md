# Phase 0 pre-registration — pilot/calibration (HYPOTHESIS_TEST.md §7)

> Written and committed BEFORE the run (L3). Thresholds here are mirrored as constants in
> `run_phase0.py`; neither may be adjusted after seeing numbers. The run answers ONE
> question: does the domain have dynamic range worth spending the Phase 1/2 sweep on?
> It is NOT the thesis test — no `deduce` condition runs here.

## Decisions (resolving HYPOTHESIS_TEST.md §9 open items)

- **§9.1 — model sizes.** On the local Ollama box: `qwen2.5:0.5b` (pulled 2026-07-01),
  `qwen2.5:1.5b`, `qwen2.5:7b`, `qwen2.5:14b`. Phase 0 uses the extremes: **0.5b vs 14b**,
  same family so size is the only variable. (`qwen2.5:3b` to be pulled for the Phase 1
  sweep; cross-family checks are Phase 1+ concerns.)
- **§9.2 — domain.** Python `issubclass` over a ~127-class stdlib inventory
  (`experiments/class_graph.py`): all builtin exceptions + core value/container types +
  `numbers` + `collections.abc` + `io`. 502 true pairs, depth 1–6 (91 pairs at depth ≥ 4).
  Ground truth is computed, not authored (Validity Checklist item 6). WordNet remains the
  pre-registered fallback if the verdict is FLAT.
- **§9.6 — virtual-subclass / ambiguity handling.** Direct edges = `__bases__`, plus a
  **minimal completion** for ABC-registered covering pairs, derived from `issubclass`
  itself. The closure of the direct-edge graph is asserted equal to `issubclass` on every
  ordered pair, so truth and hop-depth cannot disagree. Two hygiene exclusions:
  `ByteString` (deprecated, warns) and `Hashable` (its `__subclasshook__` makes `object` a
  virtual subclass → mutual subclassing → `issubclass` stops being a partial order and
  depth is undefined; caught by the antisymmetry assertion, not discovered post-hoc).
- **Elicitation (§8: it dominates — piloted first).** Forced-choice two-option letter
  answer, temperature 0, one vote. The True/False **letter assignment is randomized per
  question** (seeded, deterministic) so positional/acquiescence bias cannot masquerade as
  accuracy. Two phrasings run: `code` (issubclass-anchored, the v3-proven style) and
  `plain` (natural language). **The verdict is computed on `code` only** — pre-registered
  here so there is no post-hoc phrasing choice; `plain` is exploratory.
- **Question set.** `generate_questions(n_per_bucket=12, seed=0)`: per depth bucket
  {1, 2, 3, 4+}, 12 true pairs + 12 false (6 reversed true pairs — the lexical-association
  control — + 6 unrelated). 96 questions total; balanced labels, deterministic from the
  seed. Pilot-sized on purpose: Phase 0 decides range, not effect sizes. Phase 1/2 will
  use N ≥ 100 per cell with Wilson intervals.
- **Budget/infra (§8).** ≈ 384 calls (96 × 2 phrasings × 2 models), batched by model to
  avoid Ollama reload thrash; every answer persisted immediately to
  `experiments/results/phase0_answers.jsonl`; interrupted runs resume (answered rows
  skipped). Expected wall-clock ≤ 10 min.

## Pre-registered verdict rules (mirrored in `run_phase0.verdict`)

On the `code`-phrasing accuracy table `acc(model, bucket)`, precedence DEAD > FLAT > GO > MIXED:

| Check | Rule | Meaning if it fails |
|---|---|---|
| Atomic competence | `acc(14b, d=1) >= 0.80` | **DEAD** — the big model can't even do depth-1 facts; extraction (Phase 2) would be hopeless here. Fix elicitation or pick another domain. |
| Flatness | not all `acc(m, d) >= 0.90` | **FLAT** — no dynamic range (the v2 failure mode); switch to WordNet before the sweep. |
| Size range | `mean over d>=2 of [acc(14b) − acc(0.5b)] >= 0.15` | without a size gap, H2 (the parameter floor) is unmeasurable in this domain |
| Composition decay | `acc(0.5b, d=1) − acc(0.5b, d=4+) >= 0.10` | without decay, H1 (the composition gap) has nothing to explain |

- **GO** = atomic competence holds, not flat, size range AND composition decay hold →
  proceed to Phase 1 (`atoms = oracle` sweep) on this domain.
- **MIXED** = atomic competence holds but range/decay partly missing → iterate elicitation
  once (it dominated v1→v2) or harden the domain; re-run Phase 0 as a fresh pre-registered
  attempt. Do NOT proceed to the sweep on a MIXED.

## Predictions (recorded before the run, per L3)

v2/v3 measured qwen2.5:**7b** at ~0.78–0.96 on adjacent regimes, so: 14b should clear the
atomic floor comfortably; the open question is entirely the 0.5b end — if 0.5b also scores
high, the domain is FLAT and `issubclass` is simply too memorized even at 0.5b. Honest
prior: **GO ~55%, FLAT ~25%, MIXED ~15%, DEAD ~5%.**

> **RESULT — Phase 0 run (2026-07-01), qwen2.5:0.5b vs 14b, both phrasings, 384 answers:
> MIXED.** Atomic competence GO (acc(14b, d=1) = **0.88**); size gap GO (**+0.36** mean
> over d≥2); small-model decay FAIL (**+0.00**) — but diagnosably a **floor effect, not a
> flat domain**: the 0.5b answered the letter "A" on **96/96** code-phrasing questions
> (pure positional bias, zero task engagement). The randomized letter assignment did its
> job — the degenerate strategy scored ~chance (0.33–0.58) instead of fake-passing, and
> the failure is visible in the raw dumps. A model below the elicitation floor cannot
> witness composition decay, so the decay check was aimed at the wrong model.
> Secondary findings: (a) 14b decays 0.88 → 0.79 with depth (just under the 0.10 bar) and
> **under-asserts true chains (0.73) while perfect (1.00) on both false kinds** — exactly
> the in-head composition failure H1 predicts deduction should rescue; (b) `code` ≥
> `plain` for both models, confirming the pre-registered primary phrasing.
> Per the MIXED rule (one fresh pre-registered iteration): → **`PHASE0_1.md`** — a model
> ladder (0.5b/1.5b/3b/7b vs 14b) with the decay/gap checks anchored on the smallest
> *atomically-competent* candidate. Not a re-tune of this run: thresholds unchanged, new
> sizes, cached answers reused verbatim.
