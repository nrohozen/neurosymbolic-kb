# Phase 1 pre-registration — the H1 composition-gap test (atoms = oracle)

> The first run in the project's whole lineage (Tilda included) that directly tests the
> thesis against a parametric baseline. Written and committed BEFORE the run (L3);
> thresholds mirrored as constants in `run_phase1.py`.

## What Phase 0.x earned and what it blocked

- **Earned (0.1):** the domain has the H1 signal — 7b/14b true-chain accuracy decays with
  depth (0.83→0.50 / 0.75→0.58); the monolith visibly fumbles deep composition.
- **Blocked (0.2):** `atoms = extracted` is DEAD — no qwen2.5 size can generatively
  enumerate exact direct edges (14b: 0.60 recall / 0.76 truth precision; it flattens
  hierarchies). So **H2 is shelved** pending an extraction design argued in a fresh doc.
- Phase 1 needs no extraction: the true atomic edges are handed to the `rag-model` and
  `deduce` conditions **by construction** (`atoms = oracle`, HYPOTHESIS_TEST.md §3/§7).

## H1, restated as run

On "is A a subclass of Z?" questions needing a chain of depth d: `monolith-direct`
declines with d; `deduce` (closure over presented atoms) stays high; the gap grows with d.

## Conditions (per question; same balanced question set for all three)

| Condition | What the model sees | What composes |
|---|---|---|
| `monolith-direct` | the bare question (Phase 0's `code` forced-choice, randomized letters — the same instrument, so pilot numbers stay comparable) | weights |
| `rag-model` | the **fact block** + "using ONLY these facts" + the same forced choice | weights, over presented atoms |
| `deduce` | the same fact block, zero LLM | the inference engine (`src/inference_engine.py`, reused untouched — transitive closure over `edge/2`) |

**Fact block** (identical for `rag-model` and `deduce`, per §3 "the same atomic edges"):
all direct edges within the ancestor sets of A and Z (so every true chain is present by
construction), padded with **distractor edges — true but irrelevant** (never false facts:
they would corrupt `deduce` too) to 30 facts, deterministically shuffled per question.
Format: `X -> Y` lines with a one-line legend.

## Question set

`generate_questions(n_per_bucket=50, seed=1)` — a **fresh seed** (seed 0 was the
diagnosed pilot draw): per depth bucket {1, 2, 3, 4+}, 50 true chains + 50 false
(25 reversed + 25 unrelated) = **100 per depth cell, 400 total**, the N the pilots lacked.
Wilson 95% intervals on every reported cell.

## Validity Checklist (§5) audit — declared BEFORE the run

1. ✔ atoms only: `rag`/`deduce` receive depth-1 edges; the model is never asked to produce
   a composed fact (it *answers* the composed question from presented atoms — that is the
   `rag-model` condition definition).
2. ✔ presented facts, not parametric recall.
3. ✔ `monolith-direct` on the same 400 questions.
4. ✔ four depth buckets.
5. ✘ **WAIVED, with cause:** item 5 (≥3 model sizes) guards H2, which is shelved — Phase
   0.1/0.2 showed no third in-family size is competent (sub-7b = degenerate at both
   verification and extraction). Phase 1 runs **7b + 14b** and claims nothing about
   parameter floors. The waiver is this pre-registration's one amendment to §5, made in
   writing, not silently.
6. ✔ computed ground truth (`issubclass`), not authored.
7. ✔ n/a by design: atoms are oracle-true; extraction accuracy was measured separately in
   Phase 0.2 (and is why H2 is shelved).
8. ✔ cost recorded per row (`prompt_eval_count`, `eval_count`, `total_duration` from
   Ollama) and reported per condition.

## Pre-registered metrics & thresholds (mirrored in `run_phase1.verdict_h1`)

Primary model = **14b** (the claim is against the *strongest* monolith); 7b reported in
full alongside. `gap(d)` = acc_deduce(d) − acc_monolith(d).

| Check | Rule | Meaning |
|---|---|---|
| Harness sanity | `acc_deduce(d=4+) >= 0.95` | the fact blocks really contain the chains; below this the harness is broken → **INVALID**, fix before interpreting anything |
| Monolith decay | `acc_mono(1) − acc_mono(4+) >= 0.10` | H1's premise: depth hurts the monolith |
| Gap growth | `gap(4+) − gap(1) >= 0.10` | **the H1 claim itself** |

- **H1_SUPPORTED** = sanity ✔, decay ✔, growth ✔ (on 14b).
- **H1_FALSIFIED** = sanity ✔ but decay < 0.05 **or** growth ≤ 0 — the monolith composes
  fine in-head, or deduction buys nothing that grows with depth. Reported as a kill.
- **MIXED** = anything between; stop and argue in writing.
- **Reported, not gated:** the `rag` curve. If `acc_rag(4+) ≥ acc_deduce(4+) − 0.05`,
  in-context composition suffices and the solver's edge is robustness/cost only — a real
  dent in the thesis's framing, flagged explicitly if it occurs.

## Budget (honest — this is not a 10-minute run)

~1,600 LLM calls (400 × 2 conditions × 2 models; `deduce` is free) with ~350-token fact
prompts on the rag side: ≈ **45–60 min** wall-clock total. Batched by model × condition,
every row persisted, fully resumable — run it in chunks if needed (`--models`,
`--conditions` flags). Deviation from the §8 10-min cap is declared here: it applies per
*attended background run*; this is a resumable batch the user launches deliberately.

## Predictions (recorded before the run, per L3)

- Monolith decay reproduces at N=100/cell (pilot saw it at N=24): ~85%.
- `deduce` ceiling holds (this is calibration, not the bet).
- The open question is **rag**: if models can compose over 30 presented facts, rag tracks
  deduce and the thesis narrows to robustness+cost; if rag decays like the monolith,
  composition itself is the deficit and the solver earns its seat. Honest priors:
  **H1_SUPPORTED ~60%, MIXED ~25%, H1_FALSIFIED ~15%**; rag-tracks-deduce ~40%.

> **RESULT — Phase 1 run (2026-07-01), 400 questions × 3 conditions × {7b, 14b}:
> H1_FALSIFIED on the pre-registered primary (14b). The kill bar fired on the thesis
> hypothesis itself; recorded, not argued away.**
>
> | condition (overall acc) | d=1 | d=2 | d=3 | d=4+ |
> |---|---|---|---|---|
> | deduce | 1.00 | 1.00 | 1.00 | 1.00 |
> | 14b monolith | 0.85 | 0.85 | 0.87 | **0.89** |
> | 14b rag | 0.99 | 0.87 | 0.88 | 0.95 |
> | 7b monolith | 0.90 | 0.88 | 0.83 | 0.79 |
> | 7b rag | 0.97 | 0.94 | 0.91 | 0.96 |
>
> Checks: deduce ceiling 1.00 ✔; **monolith decay (14b) = −0.04 FAIL** (it slightly
> *improves* with depth); gap growth = −0.04 FAIL (gap is +0.11…+0.15 at every depth —
> real, but **constant**, not growing). The rag flag fired: rag(d=4+) = 0.95 tracks
> deduce (1.00).
>
> Findings, in order of importance:
> 1. **H1's premise fails at the strongest monolith: depth does not hurt 14b in this
>    domain** (chain-only slice: 0.72→0.78, flat). The pilot's apparent decay
>    (0.88→0.79 at N=24) did not replicate at N=100 — it was sampling noise, which is
>    precisely why the sweep pre-committed to powered cells. The domain fails
>    HYPOTHESIS_TEST §4(e) (a difficulty regime with dynamic range) *in depth at the top
>    size* — a requirement Phase 0 checked across size but could not check in depth at
>    power. Any successor domain (WordNet) must demonstrate powered depth-decay at the
>    primary model BEFORE earning a Phase 1.
> 2. **With true atoms presented, in-context composition suffices** — rag ≈ deduce at
>    d=4+ for both models. Deduction's measured edge over the monolith is a **constant**
>    +0.11–0.15 (reliability), plus cost: 0 tokens vs ~345/question (and 0s vs 455s for
>    14b-rag over 400 questions), plus determinism. It is NOT depth-scaling accuracy.
> 3. Exploratory (not the pre-registered primary): **7b does decay** (0.90→0.79; chains
>    0.88→0.60), so H1's shape exists one size down — and 7b+rag (0.96 at d=4+) beats
>    the 14b monolith (0.89), an H2-flavored observation that would only matter if
>    extraction worked, which Phase 0.2 killed.
>
> Combined with Phase 0.2, the seam's honest value in this regime: extraction of exact
> structure from the model is unreliable (0.2), and composition over provided structure
> is nearly matched in-context (Phase 1) — the solver's surviving edges are **zero
> marginal cost, determinism, and the constant reliability gap**, not the
> depth-compounding advantage the thesis predicted.
