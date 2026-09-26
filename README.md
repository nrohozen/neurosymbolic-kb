# neurosymbolic-kb

A research/learning vehicle. Successor to Tilda — carries its lessons, not its code or
vocabulary. **Start with `FINDINGS.md`** — the skeptic-facing writeup of the completed
hypothesis test (H1 falsified; what the falsification split apart and which half of the
thesis survived). `DIRECTION.md` has the original thesis and per-milestone records,
`RESULTS.md` the M1–M6 synthesis (with retraction banner), `GLOSSARY.md` the
standard-terminology rule (no invented terms).

The bet, in one line: store knowledge in a **knowledge graph**, reason over it with a
**forward-chaining inference engine**, catch most contradictions **deductively** (zero LLM
calls), and spend a small **frozen base model** only at the boundary (extraction +
tie-breaking). The result, in one line: the store helped, the solver as composer didn't,
and the model couldn't write down the solver's facts. Details and numbers in `FINDINGS.md`.

## Setup

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest          # deterministic + offline (clingo used directly; no network)
```

## Reproduce the headline results

Every model answer from the pre-registered runs is committed in `experiments/results/`, so
the FINDINGS.md tables re-score from the saved answers with **no model calls**:

```powershell
# Phase 1 (the H1 test): accuracy table with Wilson CIs, cost, verdict H1_FALSIFIED.
.venv\Scripts\python -m experiments.run_phase1

# Phase 0.2 (generative extraction): verdict DEAD, re-parsed from the raw model text.
.venv\Scripts\python -m experiments.run_phase0_2 --rescore
```

Delete a results file to re-run that phase against a local Ollama (qwen2.5; Phase 1 is
about an hour on one consumer GPU, resumable). Pre-registrations, with thresholds committed
before each run and RESULT blocks after, are the `experiments/PHASE*.md` files; the
protocol is `experiments/HYPOTHESIS_TEST.md`.

## Earlier milestones (M1–M6: infrastructure validation, not a thesis test)

These scorecards validated the plumbing across five domains. Their gold sets were
self-authored and they ran no parametric baseline, so read them as engineering checks; see
the banner at the top of `RESULTS.md`. Domain 1 is **algorithms & data structures**, chosen
because it hands you a *perfect, free oracle* (execution + the complexity lattice).

```powershell
# deductive metrics (1, 2, 3, 5) need only clingo; metric 4 needs a local Ollama.
.venv\Scripts\python -m eval.run_m1

# Milestone 2 (extraction path, metrics 6-9): needs a local Ollama for extraction.
.venv\Scripts\python -m eval.run_m2

# Milestone 2-filter (consistency filter in isolation, metrics 10-12): clingo only, offline.
.venv\Scripts\python -m eval.run_m2_filter

# Milestone 3 (domain 2 = a codebase, metrics 16-19): clingo + ast, no LLM, offline.
.venv\Scripts\python -m eval.run_m3

# Milestone 4 (domain 3 = homelab/temporal oracle, metrics 20-24): clingo only, offline.
.venv\Scripts\python -m eval.run_m4

# Milestone 5 (domain 4 = CS-as-a-field/weak oracle, metrics 25-29): metric 27 needs Ollama.
.venv\Scripts\python -m eval.run_m5

# Milestone 5.1 (calibrated abstention, metrics 30-33): 31-33 need Ollama. (First run: KILL on 32.)
.venv\Scripts\python -m eval.run_m5_1

# Milestone 5.2 (probe fix on held-out set, metrics 34-37): 35-37 need Ollama.
.venv\Scripts\python -m eval.run_m5_2

# Milestone 6 (domain 5 = open/contested knowledge, metrics 38-42): clingo only, offline.
.venv\Scripts\python -m eval.run_m6

# Everything at once (all milestone scorecards M1-M6; live metrics skip without Ollama).
.venv\Scripts\python -m eval.run_all
```

## Layout

| Path | What it is (standard term) |
|---|---|
| `schema/ads.lp` | the typed schema as an **Answer Set Program**: relation property rules + integrity constraints |
| `schema/seeds.jsonl` | ~20 hand-authored **ground-truth triples** (the anchors) |
| `src/knowledge_graph.py` | the typed triple store |
| `src/inference_engine.py` | **clingo** wrapper: deductive closure (SAT) + contradiction (UNSAT) |
| `src/oracle.py` | the swappable **Oracle** interface + `ExecutionOracle` + `JudgeEntailmentOracle` + `AstOracle` + `StateOracle` |
| `src/reference_impls.py` | comparison-counting reference algorithms the execution oracle runs |
| `src/judge_ensemble.py` | **LLM-as-judge** ensemble over Ollama (injectable transport + claim-text) |
| `src/belief_revision.py` | **AGM belief revision** by epistemic entrenchment (pure fn over triples) |
| `src/calibration.py` | **calibrated abstention** (TRUE/FALSE/CONTESTED) via agreement + negation-consistency |
| `src/source_reconciliation.py` | **multi-source reconciliation**: MUS-localized conflicts, represent (not resolve) disagreement |
| `src/relation_extraction.py` | LLM **relation extraction** at the boundary (injectable transport) |
| `src/extraction_filter.py` | **deductive consistency filter**: solver vets extracted triples, zero LLM calls |
| `src/canonicalization.py` | **entity linking + controlled-vocabulary** normalization of extracted triples |
| `eval/run_m1.py` | computes M1 metrics 1–5 against the draft thresholds |
| `eval/m1_cases.jsonl` | held-out test set: comparisons, conceptual claims, planted clashes, consistent controls |
| `eval/run_m2.py` | computes M2 extraction metrics 6–9 (raw P/R + consistency-filtered P + recall retention) |
| `eval/m2_corpus.jsonl` | hand-labeled extraction corpus: source texts + gold triples |
| `eval/run_m2_filter.py` | computes M2-filter metrics 10–12 (filter in isolation: catch rate, false-drop, precision lift) |
| `eval/m2_filter_cases.jsonl` | labeled candidate triples (true / contradictory / consistent-error) with honesty meta-test |
| `schema/code.lp` | domain-2 schema: call/import/inherit closures + inheritance-cycle & layering constraints |
| `src/code_extraction.py` | deterministic **AST** fact extractor (`ast`) -> typed triples |
| `eval/run_m3.py` | computes M3 domain-2 metrics 16–19 (swappability, contradiction recall, reachability, false-contradiction) |
| `eval/m3_cases.jsonl` + `eval/m3_fixture/` | reachability/contradiction gold + a fixture codebase with a known structure |
| `schema/state.lp` | domain-3 schema: derived config-drift + impossible-snapshot integrity constraints |
| `src/state_extraction.py` | snapshot JSON -> `observed` triples (injectable provider) |
| `src/staleness.py` | active-learning / staleness re-query policy + snapshot diff |
| `eval/run_m4.py` | computes M4 domain-3 metrics 20–24 (swappability, drift recall, false-drift, active-learning) |
| `eval/m4_*.{json,jsonl}` | synthetic homelab snapshot (generic names and placeholder addresses) + desired-state intent + drift/consistent cases |
| `schema/csfield.lp` | domain-4 schema: subfield_of/subsumes strict partial orders (cycle = contradiction) |
| `eval/run_m5.py` | computes M5 domain-4 metrics 25–29 (swappability, deductive reliability, structure lift, belief revision, consistency) |
| `eval/m5_*.jsonl` | CS axioms + consensus-labeled claims + designed belief-revision scenarios |
| `eval/run_m5_1.py` + `eval/m5_contested.jsonl` | M5.1 calibrated-abstention metrics 30–33 + settled/contested calibration set |
| `eval/run_m5_2.py` + `eval/m5_contested_holdout.jsonl` | M5.2 probe-fix re-test (metrics 34–37) on a held-out set |
| `schema/open.lp` | domain-5 schema: broader_than order + same_as equivalence + disjointness |
| `eval/run_m6.py` + `eval/m6_sources.jsonl` | M6 domain-5 metrics 38–42 + multi-source agreed/surface/latent scenarios |
| `eval/run_all.py` | runs every milestone scorecard M1–M6 in order |
| `RESULTS.md` | consolidated one-page synthesis across all milestones |

> **Status update (2026-07-01): the milestone record below is infrastructure validation,
> not a thesis test.** Gold sets, schemas, and planted errors were self-authored (grader =
> author) and no parametric baseline was run, so the GO metrics are near-tautological — see
> the reframe at the top of `RESULTS.md`. The honest, pre-registered thesis test lives in
> `experiments/HYPOTHESIS_TEST.md`; its Phase 0 pilot (does the domain have dynamic range
> across model sizes?) is `python -m experiments.run_phase0` (pre-registration:
> `experiments/PHASE0.md`).

> Status: **M1** (A&DS core) 2–5 GO. **M2/M2.1** (extraction) — P/R 0.59→**0.82/0.78** after
> canonicalization. **M2-filter** — 10–12 GO. **M3 (codebase)** — 16–19 GO. **M4 (homelab/
> temporal oracle)** — 20–24 GO. **M5 (domain 4 = CS-as-a-field, the WEAK oracle) built +
> passing** — metrics 25–29 all GO: swappability 0 diffs, deductive reliability 1.00,
> **structure lift +0.20 (assisted 1.00 vs judge-alone 0.80)**, belief-revision 1.00, final
> consistency 1.00. **The genome holds across four domains and four oracle kinds (execution,
> AST, live-state, weak/judge) — the make-or-break 3→4 jump is cleared.** **M5.1 (calibrated
> abstention) — KILL on metric 32 (recorded honestly):** the negation-consistency probe
> over-abstains on settled claims with local 7–9B judges (judge-alone was already 1.00 on
> them), so the anti-graveyard guard isn't earned yet. **M5.2 (probe fix, held-out set)**
> confirmed both predictions: the fix cut over-abstention 0.62→0.38 (the bug was real), but
> contested-abstention collapsed to 0.17 — **self-signals from one overconfident model family
> can't detect contestedness; it needs external source disagreement (→ domain 5).** **M6
> (domain 5 = open/contested knowledge) built + passing** — metrics 38–42 all GO: deduction
> catches **100%** of latent (multi-source) conflicts vs **0%** for the pairwise baseline,
> faithful representation 1.00 (disagreement represented, never resolved), 0 core diffs.
> **Curriculum complete: the deductive genome spans all five domains and every oracle strength
> (execution → AST → live-state → weak/judge → none/conflicting-sources) with zero core
> changes.** See DIRECTION.md RESULT blocks.

## License

MIT. See `LICENSE`.
