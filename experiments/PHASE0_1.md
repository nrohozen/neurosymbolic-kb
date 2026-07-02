# Phase 0.1 pre-registration — model-ladder re-pilot (after the Phase 0 MIXED)

> The single fresh iteration PHASE0.md's MIXED rule allows. Written and committed BEFORE
> the run (L3); thresholds mirrored as constants in `run_phase0.py` (`verdict_v2`).
> Phase 0 answers are reused from cache (`experiments/results/phase0_answers.jsonl`) —
> only the new sizes generate live calls.

## What Phase 0 established (see its RESULT block)

The domain is not flat and not dead: atomic competence 0.88, size gap +0.36. The decay
check failed **because it was anchored on a model below the elicitation floor** — 0.5b
answered "A" 96/96 times regardless of content. Measuring composition decay requires a
model that is at least *answering*; 0.5b is not.

## Changes from Phase 0 (each one motivated by Phase 0 data, none a threshold re-tune)

1. **Model ladder, not a pair:** `qwen2.5:0.5b / 1.5b / 3b / 7b` as small-end candidates
   (smallest → largest), `qwen2.5:14b` as the large/monolith reference. 3b pulled
   2026-07-01; the rest were already on the box. Same family throughout, so size stays
   the only variable.
2. **Anchor rule:** the decay and gap checks are measured against the **smallest candidate
   that clears an atomic-competence floor** — `acc(m, d=1) >= 0.70` — instead of the
   smallest model on disk. That is what the Phase 0 decay check was always trying to mean;
   Phase 0 hard-coded it to a degenerate model. The anchor also becomes the bottom of the
   Phase 1 size axis.
3. **`code` phrasing only.** Phase 0 pre-registered `code` as the verdict phrasing and the
   data confirmed it ≥ `plain` for both models; `plain` is retired, halving call count.

Unchanged: the question set (`generate_questions(n_per_bucket=12, seed=0)`), the
forced-choice elicitation with randomized letter assignment, temperature 0, all Phase 0
thresholds (atomic floor 0.80, flat ceiling 0.90, gap 0.15, decay 0.10), resume-from-cache.

## Pre-registered verdict rules (`run_phase0.verdict_v2`)

Precedence: **INCOMPLETE > DEAD > FLAT > NO_FLOOR > GO > MIXED.**

| Check | Rule | Meaning if it decides |
|---|---|---|
| Atomic competence | `acc(14b, d=1) >= 0.80` | **DEAD** — the big model can't do depth-1 facts; domain/elicitation hopeless |
| Flatness | all models `>= 0.90` at every depth | **FLAT** — no dynamic range anywhere on the ladder; switch to WordNet |
| Anchor exists | some candidate has `acc(d=1) >= 0.70` | **NO_FLOOR** if none — the size axis has no usable bottom below 14b; the finding is then "forced-choice elicitation has a ~7b floor in this domain," and Phase 1 needs either an elicitation redesign or a different domain |
| Size range | mean over d≥2 of `acc(14b) − acc(anchor)` `>= 0.15` | without a gap, H2 is unmeasurable here |
| Composition decay | `acc(anchor, d=1) − acc(anchor, d=4+)` `>= 0.10` | without decay, H1 has nothing to explain |

**GO** = anchor exists, not flat/dead, gap AND decay hold → Phase 1 sweep over sizes ≥ anchor.
**MIXED** = anything else → stop and argue in writing (Phase 0.2 would need a *reframed
check*, e.g. anchoring H1's decay on the large model's own 0.88→0.79 slide — argued in a
doc first, never silently reinterpreted).

## Budget

~288 new calls (1.5b + 3b + 7b × 96 questions, code only; 0.5b and 14b fully cached),
batched per model, ≈ 4–6 min wall-clock. Same answers file; interrupted runs resume.

## Predictions (recorded before the run, per L3)

- 0.5b stays degenerate (cached — known).
- 1.5b likely *follows the format* (0.5b was the outlier) but may hover near chance on
  content → the anchor most plausibly lands on **3b or 7b**.
- 7b at ~0.78–0.96 on adjacent regimes (v2/v3) suggests it clears the floor easily; the
  live question is whether the anchor *decays* ≥ 0.10 with depth.
- Honest priors: **GO ~45%, MIXED ~35% (decay just misses at the anchor), NO_FLOOR ~10%,
  FLAT ~5%, DEAD ~5%.**

> **RESULT — Phase 0.1 run (2026-07-01), full ladder, code phrasing: MIXED** (the predicted
> 35% branch, though not for the predicted reason). Anchor = **7b** (acc(d=1) = 0.88);
> anchor decay **+0.17 GO**; but size gap 14b−7b = **+0.01 FAIL** — 7b and 14b are
> equivalent here. The ladder's real shape is a **competence cliff, not a gradient**:
>
> | model | overall by depth (code) | true-chain by depth | diagnosis |
> |---|---|---|---|
> | 0.5b | 0.58 / 0.58 / 0.33 / 0.58 | — | format-degenerate (all "A", known from Phase 0) |
> | 1.5b | 0.58 / 0.71 / 0.54 / 0.54 | 0.17 / 0.50 / 0.08 / 0.08 | format OK, **near-universal "False"** |
> | 3b | 0.50 / 0.54 / 0.54 / 0.50 | **0.00** / 0.08 / 0.08 / **0.00** | format OK, universal "False" — denies `tuple -> object` |
> | 7b | 0.88 / 0.92 / 0.92 / 0.71 | 0.83 / 0.83 / 0.83 / 0.50 | competent; decays with depth |
> | 14b | 0.88 / 0.88 / 0.92 / 0.79 | 0.75 / 0.75 / 0.83 / 0.58 | competent; decays; ≈ 7b |
>
> Three findings: (1) sub-7b qwen2.5 fails by **truth-value bias** (systematic denial of
> positive claims — 3b's 0.00 on trivial d=1 truths is *anti*-knowledge, not guessing),
> a failure mode letter-randomization exposes but cannot fix; (2) at the competent end the
> H1-relevant signal is REAL — true-chain accuracy decays 0.83→0.50 (7b) and 0.75→0.58
> (14b): the monolith visibly fumbles deep composition; (3) the pre-registered gap check
> conflated "verification-competent at the direct task" with "usable as the small base" —
> Phase 2's small base needs **atomic-extraction** competence (generative), which this
> pilot never measured. Per the MIXED rule: STOP; the argument for what follows is made in
> writing before anything runs (→ Phase 0.2 proposal: an extraction pilot, §9.4 decided).
