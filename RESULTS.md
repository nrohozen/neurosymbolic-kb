# Results — a consolidated synthesis (M1–M6)

A one-page summary of the five-domain curriculum. Per-milestone detail (pre-committed
metrics, kill criteria, RESULT blocks) lives in **`DIRECTION.md`**; this file is the
executive view. Re-run everything with `python -m eval.run_all`.

## The bet, restated

Store knowledge in a **knowledge graph**, reason over it with a **forward-chaining
inference engine** (clingo / ASP), catch contradictions **deductively** (zero LLM calls),
and spend a **small frozen base model** only at the boundary (extraction + tie-breaking).
The empirical question: does deductive *structure* keep buying "elimination power" as the
oracle weakens from a perfect one (run the code) to none at all (conflicting sources)?

## The curriculum, domain by domain

| Domain | Oracle | Strength | Headline result | Verdict |
|---|---|---|---|---|
| 1 — algorithms & data structures | execution + complexity lattice | strong | contradiction recall **1.00**, comparison accuracy **1.00** (vs Tilda's ~0.17 on the same shape), conceptual adjudication **0.88** | **GO** (M1) |
| 1 — extraction boundary | frozen LLM + canonicalization | boundary | raw P/R 0.59/0.59 → **0.82 / 0.78** after entity-linking + controlled-vocab | **GO** (M2.1) |
| — consistency filter | the solver vetting the LLM | — | catches 100% of contradiction-shaped extraction errors, false-drop 0.00, precision lift **+0.30** | **GO** (M2-filter) |
| 2 — a codebase | compiler / AST | strong | swappability **0 diffs**, code-contradiction recall **1.00**, reachability **1.00** (engine closure == independent BFS), 313 real facts consistent | **GO** (M3) |
| 3 — homelab / infra | live system snapshot | **temporal / mutable** | drift recall **1.00** (incl. the split-horizon DNS bug), active-learning caught 100% of changes at **60% fewer queries** | **GO** (M4) |
| 4 — CS-as-a-field | LLM-judge ensemble | **weak** | deductive reliability **1.00**, **structure lift +0.20** over judge-alone, belief-revision **1.00**, consistency **1.00** | **GO** (M5) |
| 4 — self-signal calibration | the model judging itself | — | over-abstention **0.62 KILL** (M5.1) → fix cut it to 0.38 but contested-detection collapsed to 0.17 (M5.2) | **KILL** (honest) |
| 5 — open / contested knowledge | none; conflicting sources | none | disagreement recall **1.00**, **latent-conflict recall 1.00 vs 0.00** for the pairwise baseline, faithful representation **1.00** | **GO** (M6) |

## Two load-bearing invariants

1. **Swappability held end to end.** Across M1–M6, "next domain" was always *a new schema
   + a new oracle*. The deductive core — `inference_engine.py`, `knowledge_graph.py`,
   `extraction_filter.py`, `canonicalization.py`, `belief_revision.py`, `calibration.py` —
   was reused **byte-for-byte** (verified by `git diff` as metrics 16/20/25/30/34/38, all
   **0**). The abstraction never leaked, across a domain change *and* four oracle-strength
   changes.

2. **The genomic-bottleneck claim reproduced at every oracle strength.** Deductive structure
   beat or matched the parametric alternative everywhere it applied — most sharply where it
   mattered most: comparison accuracy 1.00 vs Tilda's 0.17 (strong oracle, M1), +0.20 over
   judge-alone (weak oracle, M5), and 100% vs 0% latent-conflict detection (no oracle, M6).

## The one honest negative — and why it strengthened the project

Self-signal **calibrated abstention** (M5.1/M5.2) was **falsified, not tuned to green**: a
single overconfident 7–9B model family can't tell "settled" from "contested" by
introspection (the broken probe over-abstained on everything; the fixed probe, tested on a
*held-out* set, under-abstained on contested). Pre-committed kill bars fired and stayed on
the record. Crucially, the failure *specified the requirement* for domain 5 —
contestedness must come from **external source disagreement** — which M6 then satisfied.
That is the falsification discipline (L3) doing its job: the negative result was localized
(one approach to one sub-problem), informative, and load-bearing for what came next.

## Bottom line

The core thesis is validated end-to-end: a small frozen base at the boundary + a
non-parametric knowledge graph + a deductive engine spans **all five domains and every
oracle strength** (execution → AST → live-state → weak/judge → none/conflicting-sources),
with zero changes to the reasoning core. Deduction supplies cheap, reliable elimination
power that a parametric model alone does not — strongest exactly where ground truth is
scarce.

**Honest bounds.** Schemas and seed/claim sets are small and hand-authored; the live-judge
magnitudes (M5 lift, the calibration numbers) are local-model-dependent (the *signs* are the
falsifiable claims). Extraction's residual bottleneck is structural faithfulness, not surface
form. Deferred, by design: LLM source-credibility weighting and word-sense resolution (M6.1),
larger/decorrelated judges (M5.3), live-MCP provider for M4, and LLM code-extraction-at-scale
(M3.1).
