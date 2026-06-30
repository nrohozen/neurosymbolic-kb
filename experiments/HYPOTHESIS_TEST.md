# Hypothesis Test Protocol — v0.1 (DRAFT, meant to be iterated)

> This document exists to stop us building **shadows** — buildable proxies that feel like the
> experiment but don't test the hypothesis (we've done it twice: M1–M6, and the witness-cut).
> **Rule: no run counts as "the test" unless it passes the Validity Checklist (§5).** Iterate
> on this doc *before* writing code. Each pass should make a vague clause concrete or kill one.

---

## 1. The hypothesis (precise)

**Plain:** split the substrates like biology — knowledge in non-parametric memory (RAG/KG),
reasoning split into a *proposer* (the model's weights) and an *eliminator/composer* (a
deductive solver) — and a **small frozen base can match a much larger monolith** on
knowledge-heavy **compositional** reasoning, because the base only has to extract atomic facts
and the solver does the composition.

**The mechanism we are actually betting on is COMPOSITION, not error-catching.** (v3 showed
consistency-filtering is weak: a competent-but-wrong witness's errors are consistent-but-wrong,
so there's little to catch. Demote error-catching to secondary.) The bet is that *deductive
closure over retrieved atomic facts answers multi-hop questions the model fumbles in-head.*

Two falsifiable sub-hypotheses:

- **H1 (composition gap).** On multi-hop questions, `deduction-over-extracted-atoms` beats
  `monolith-direct`, and **the gap grows with hop depth**.
  - *Falsified if:* the monolith's accuracy stays flat with depth (it composes fine in-head),
    or deduction-over-atoms is ≤ monolith at every depth.
- **H2 (parameter floor).** A **small** base + (extract + deduce) matches a **much larger**
  monolith-alone at a hard depth — i.e. there is a crossover size where small+structure ≈
  big-alone, at a fraction of the inference cost.
  - *Falsified if:* no small base + structure reaches large-monolith accuracy; or it only does
    so when the base is already large enough to answer directly (structure bought nothing).

The deep point both share: **the model should only ever be asked for depth-1 (atomic) facts —
what it's reliable at — and the solver does every hop beyond that.** The witness-cut's fatal
error was asking the model the *transitive* question and using its answer as the graph.

---

## 2. Variables

| Variable | Meaning | Range (to finalize in §9) |
|---|---|---|
| `d` | hop depth of the question (min path length in the true graph) | 1, 2, 3, 4(+) |
| `s` | base-model size | ≥3 points, e.g. 0.5B / 1.5B / 3B / 7B / 14B (local) |
| `C` | condition | `monolith-direct`, `rag-model`, `deduce` |
| `atoms` | where the depth-1 facts come from | `oracle` (Phase 1) → `extracted` (Phase 2) |

---

## 3. Conditions (exact procedures)

For a question "is A `R` Z?" whose true answer needs a chain `A → … → Z` of length `d`:

- **`monolith-direct`** — prompt only the question; model answers from parametric memory +
  in-context reasoning. (Knowledge & reasoning both in weights — the thing we claim to beat.)
- **`rag-model`** — retrieve the relevant **atomic** edges into context; ask the model to
  answer *using only those facts*. (Proposer over presented data; composition still in weights.)
- **`deduce`** — take the **same** atomic edges, build the KG, run closure; answer = entailed?
  (Composition externalized to the solver; weights do no reasoning.)

`atoms = oracle` → the atomic edges are the *true* depth-1 edges (isolates composition).
`atoms = extracted` → the **base model** produced the depth-1 edges (adds extraction noise —
this is where the thesis actually lives).

---

## 4. Domain & ground truth

Requirements: (a) a transitive (or richer) relation; (b) **ground truth we did NOT author**,
computable; (c) atomic facts separable from composed questions; (d) tunable depth; (e) a
difficulty regime with *dynamic range across model size* (small models wrong, big models right).

- **Primary candidate:** Python `issubclass` over a large, deep class graph (numbers tower,
  collections.abc, exceptions, stdlib). Free, computed, deep chains, no deps. v2/v3 showed 7B
  is ~0.78–0.96 here → likely strong dynamic range for 0.5B–14B. Depth = path length in the
  true subclass DAG.
- **Fallback / richer:** WordNet hypernymy (needs `nltk`+data) — more "open knowledge," genuine
  rare-term difficulty. Use if the size sweep needs a harder atomic layer.
- **Question generation:** build the true DAG; BFS for all (A,Z) with their min hop-distance;
  bucket by `d`; balance true vs false (false = unrelated pairs and reversed pairs); cap per
  bucket for power (§9). Atomic edges for RAG = the true direct edges among the entities in the
  question's neighborhood, mixed with distractor edges so retrieval isn't trivial.

---

## 5. Validity Checklist (anti-shadow) — a run is INVALID unless ALL hold

1. ☐ The model is asked for **atomic (depth-1) facts only** in the RAG/deduce conditions —
   never the composed answer.
2. ☐ RAG conditions use **retrieved/presented facts**, not the model's parametric recall.
3. ☐ The **`monolith-direct` baseline** runs on the **same** questions.
4. ☐ Tested at **≥3 composition depths**.
5. ☐ Tested at **≥3 model sizes** (H2 is meaningless otherwise).
6. ☐ Graded against ground truth **we did not author**.
7. ☐ **Atomic-extraction accuracy** is measured and reported **separately** from composition
   accuracy (so we can attribute failure to extraction vs reasoning).
8. ☐ **Cost** (tokens / wall-clock) reported per condition (the efficiency half of the claim).

If any box is unchecked, it is a shadow. Abort and fix the design, do not run.

---

## 6. Metrics & pre-registered predictions

- `accuracy(C, d, s)` on the balanced question set; `extraction_accuracy(s)`; `cost(C, s)`.
- **H1 plot:** accuracy vs `d` at fixed `s`. Pre-register: `monolith-direct` declines with `d`;
  `deduce` stays high; `gap(d) = deduce − monolith` increases. Report the slope.
- **H2 plot:** accuracy vs `s` at a hard `d`. Pre-register a crossover: `deduce@small_s ≥
  monolith-direct@large_s`. Report the smallest `s` for `deduce` that matches the largest
  monolith.
- **Cost:** deduction inference ≈ free vs large-model forward passes — quantify the saving at
  the crossover.
- **Kill criteria:** H1 dead if `gap(d)` is flat or negative; H2 dead if no small `deduce`
  configuration reaches large-monolith accuracy.

---

## 7. Staged plan (each phase pre-registers prediction + kill before running)

- **Phase 0 — pilot/calibration.** Confirm the domain has dynamic range: run `monolith-direct`
  at the smallest and largest sizes on a few depths. We need small≈bad, large≈good and
  composition decay. If the domain is flat (all sizes ace it, like v2), pick a harder one
  *before* spending the full sweep. Also pilot the **elicitation** (forced-choice; v1→v2 proved
  elicitation dominates).
- **Phase 1 — clean composition (`atoms=oracle`).** Conditions × depth × size with *true*
  atomic edges. Establishes the monolith decay curve, the `rag-model` curve, and `deduce` as the
  ceiling. This is calibration, not the thesis.
- **Phase 2 — the real test (`atoms=extracted`).** The base extracts the depth-1 edges (noisy);
  `deduce` composes over them. Compare to `monolith-direct`. **This is where the hypothesis
  lives** — does a small base's *atomic* extraction + deduction beat a large monolith's in-head
  composition, despite extraction noise? (The witness-cut's open question, finally aimed right.)
- **Phase 3 — the learning loop (only if Phase 2 is positive).** Consolidate validated
  extrapolations (novelty × survives-the-solver) into the base; re-measure the floor. Tests the
  growth rule. Do not build until Phase 2 earns it.

---

## 8. Lessons baked in (constraints from this session — do not relearn the hard way)

- **Elicitation dominates** (v1 0.26 → v2 0.96 from probe alone). Pilot and fix the probe first;
  forced-choice, not leading yes/no.
- **Self-signals are useless as a truth-proxy** (M5.1, M5.2, v3: confidence *and* sampling
  stability fail — the model is stably, confidently wrong). The validator is the solver or
  external ground truth, never the model's own credence.
- **Errors are consistent-but-wrong** → center the design on **composition** (deduction
  computes what the model can't), not error-catching (which needs a constraint-dense schema and
  was weak).
- **Infra:** background runs are capped at ~10 min; batch by model (avoid Ollama reload thrash),
  persist intermediate results, keep each run bounded.
- **Design→implementation drift is the main risk** — hence §5. When coding, check each box
  against the actual code before running.

---

## 9. Open decisions (iterate these — fill in / argue each pass)

1. Which local model sizes are actually pullable on the GPU box? (Determines the `s` axis.)
2. Final domain: Python `issubclass` vs WordNet vs other. Does `issubclass` have size dynamic
   range down to 0.5–1.5B? (Phase 0 answers this.)
3. Retrieval mechanism in Phase 2: oracle-subset of edges, vs real embedding retrieval over a
   text corpus? (Cleaner vs more realistic.)
4. How are atomic edges *extracted* from the base in Phase 2 — forced-choice over candidate
   pairs, or open generation ("name the direct superclass of X")? Open generation is more
   honest (no candidate leak) but harder to parse.
5. Question-set size per (d, label) bucket for adequate statistical power.
6. How to handle ABC virtual-subclass / word-sense edge cases so ground truth is unambiguous.
7. Stop conditions: what result makes us conclude the thesis is supported / dead / scoped.

---

*Changelog:* v0.1 — initial draft. Centers composition over error-catching; separates atomic
extraction from composition; adds the validity checklist and the staged plan.
