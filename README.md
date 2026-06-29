# neurosymbolic-kb

A research/learning vehicle. Successor to Tilda — carries its lessons, not its code or
vocabulary. See **`DIRECTION.md`** for the thesis and **`GLOSSARY.md`** for the
standard-terminology rule (no invented terms).

The bet, in one line: store knowledge in a **knowledge graph**, reason over it with a
**forward-chaining inference engine**, catch most contradictions **deductively** (zero LLM
calls), and spend a small **frozen base model** only at the boundary (extraction +
tie-breaking). Domain 1 is **algorithms & data structures** — chosen because it hands you a
*perfect, free oracle* (execution + the complexity lattice) to validate the engine against.

## Setup

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## Run the Milestone 1 scorecard

```powershell
# deductive metrics (1, 2, 3, 5) need only clingo; metric 4 needs a local Ollama.
.venv\Scripts\python -m eval.run_m1

# Milestone 2 (extraction path, metrics 6-9): needs a local Ollama for extraction.
.venv\Scripts\python -m eval.run_m2
```

## Tests

```powershell
.venv\Scripts\python -m pytest          # deterministic + offline (clingo used directly; no network)
```

## Layout

| Path | What it is (standard term) |
|---|---|
| `schema/ads.lp` | the typed schema as an **Answer Set Program**: relation property rules + integrity constraints |
| `schema/seeds.jsonl` | ~20 hand-authored **ground-truth triples** (the anchors) |
| `src/knowledge_graph.py` | the typed triple store |
| `src/inference_engine.py` | **clingo** wrapper: deductive closure (SAT) + contradiction (UNSAT) |
| `src/oracle.py` | the swappable **Oracle** interface + `ExecutionOracle` + `JudgeEntailmentOracle` |
| `src/reference_impls.py` | comparison-counting reference algorithms the execution oracle runs |
| `src/judge_ensemble.py` | **LLM-as-judge** ensemble over Ollama (injectable transport) |
| `src/relation_extraction.py` | LLM **relation extraction** at the boundary (injectable transport) |
| `src/extraction_filter.py` | **deductive consistency filter**: solver vets extracted triples, zero LLM calls |
| `eval/run_m1.py` | computes M1 metrics 1–5 against the draft thresholds |
| `eval/m1_cases.jsonl` | held-out test set: comparisons, conceptual claims, planted clashes, consistent controls |
| `eval/run_m2.py` | computes M2 extraction metrics 6–9 (raw P/R + consistency-filtered P + recall retention) |
| `eval/m2_corpus.jsonl` | hand-labeled extraction corpus: source texts + gold triples |

> Status: **M1 built + passing** (metrics 2–5 GO; see DIRECTION.md). **M2 (extraction path)
> built + measured** — raw P/R = 0.59/0.59 (MID); the consistency filter is correct but inert
> on a clean corpus (errors are canonicalization, not contradictions). See the M2 RESULT block
> in DIRECTION.md for the full finding.
