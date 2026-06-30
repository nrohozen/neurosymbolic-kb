# Direction & Kickoff Brief

> Provisional working name: **neurosymbolic-kb** (a standard-term descriptor, not a codename — rename at will). Successor to Tilda: carries its *lessons*, not its code and not its vocabulary.

## Posture

A research/learning vehicle, not a product. Read first, plan second, code third — do not write code until the repo (when it exists) is read and a plan is agreed. Optimize for **correct, inspectable, and falsifiable**. Do not optimize for shipping or competing with frontier models.

## The standard-terminology rule (load-bearing — a reason this project is separate from Tilda)

- Every component is named with the **established term from its field**. See `GLOSSARY.md`.
- A metaphor is allowed **only** as a one-line intuition pump, explicitly flagged as such. The standard term is canonical in code, docs, and — most importantly — literature search.
- If something seems to have no standard name, that is a signal to **search harder** (it almost always does), not a license to coin one. Invented terms hide prior art.
- Module files are named after the standard concept (`relation_extraction.py`, `inference_engine.py`, `truth_maintenance.py`, `judge_ensemble.py`, `replay_buffer.py`) — never after a metaphor.

## The thesis (plain, standard terms)

Frontier models store the world's *knowledge* in their *parameters*. Biology does not: the genome is information-poor (~750 MB) and cannot specify the connectome (~10^14 synapses), so it encodes priors, architecture, and learning rules, and the environment grows the rest — the **genomic bottleneck** (Zador, 2019).

Bet: split the substrates the way biology does, and a **small frozen base model** can suffice, because it is no longer asked to be the encyclopedia.

- **Priors / reasoning** = a frozen pretrained base model + a hand-authored **typed schema** (this project's analog of innate **core knowledge**, Spelke). Never trained on the domain.
- **Knowledge** = a **knowledge graph** (non-parametric memory), grown from the environment.
- **Inference** = a **forward-chaining inference engine** computing **deductive closure** over the graph and its relation properties.
- **Consistency** = mostly **deductive contradiction detection** (truth maintenance), with an **LLM-as-judge ensemble** only at the boundary, for what inference cannot decide.

The parameter floor is set by the *reasoning* the base must do at the boundary (relation extraction + tie-breaking), **not** by how much it must memorize. Whether that floor is 9B / 3B / larger is an **empirical question this project measures**, not an assumption.

## Architecture (every noun is a literature search)

1. **Frozen pretrained base model** — priors; served locally via Ollama.
2. **Relation extraction / OpenIE** (LLM-based knowledge-graph construction) — text → typed triples, at the boundary.
3. **Knowledge graph** with typed relations carrying **OWL-style property characteristics** (transitive / symmetric / inverse / functional).
4. **Forward-chaining inference engine** — Datalog / Answer Set Programming (clingo) / or an SMT solver. Use an existing engine; do not hand-roll.
5. **Truth maintenance + belief revision** — detect contradictions, localize, retract (de Kleer/Doyle TMS; AGM belief revision).
6. **LLM-as-judge ensemble + NLI/entailment check** — boundary tie-breaker for candidates inference cannot settle (self-consistency; decorrelated model families).
7. **Replay buffer + offline re-evaluation** — uncertain items revisited later (continual-learning / RL terminology).
8. **Active learning / uncertainty sampling** — decides when to query an external source instead of deriving.
9. **PEFT / LoRA adapters** — domain adaptation / expression **only**. Not knowledge storage, not judgment (see L2).

## Lessons carried from Tilda (explicit)

- **L1.** Separate knowing / reasoning / judgment — kept, but most judgment is now **deductive** (cheap), not an LLM vote per fact.
- **L2.** **Do not grow judgment in weights.** Tilda's judge-LoRA overfit and degraded held-out judging below an already-strong base (measured 2026-06-26, seventh convergent signal). Growth here = deductive closure over seeds, not training. PEFT is for expression, never knowledge or judgment.
- **L3.** **Falsification or it didn't happen.** Every milestone pre-commits a metric *and* a kill criterion **before** running. Adding components forever without moving a pre-committed number is avoidance in new clothes.
- **L4.** **Reuse engines, reuse terms.** Stand on Datalog/clingo/SMT/TMS libraries and standard vocabulary. The entire novelty budget is the **LLM-frontend ↔ solver-backend seam** — spend it nowhere else.
- **L5.** **Provenance on every fact:** `seed` / `extracted+judged` / `derived` — stamped with the rule or vote that admitted it.

## Milestone 0 — pick the domain (DECIDE FIRST; it sizes everything)

A domain fits iff: (a) closed-ish entity types + relation set; (b) relations have real logical properties to exploit (transitive / inverse / functional); (c) contradiction detection is cheap and ideally checkable against ground truth; (d) you have seeds + stakes; (e) non-sensitive (a cloud tie-breaker is then allowed) or kept fully local.

**DECIDED (2026-06-29): a five-domain curriculum, ordered by *descending oracle strength*.** Build the transferable engine against the strongest oracle first, then weaken the oracle one notch per domain — each notch forcing a new capability (a curriculum in Bengio's sense; the developmental / genomic-bottleneck spirit). Each domain is a **gate, not a commitment** (L3): it must move a pre-committed number or the project stops. Domains 1–2 may already prove or kill the core thesis; 4–5 may never be reached.

1. **Algorithms & data structures** — oracle: **execution + the complexity lattice** (strongest). New muscle: validate the engine + property library against a *perfect* oracle, and debut the judge/entailment path on the conceptual subset execution can't settle. **← domain 1, built first.**
2. **A specific software codebase** — oracle: compiler / AST (deterministic, real artifact). New muscle: extraction-at-scale, cross-artifact correspondence, intent-vs-reality contradiction (stale docs, arch violations). Prior art: **CodeQL, Glean, Doop, Soufflé, tree-sitter, ArchUnit** — the syntactic half is mature, do not reinvent it.
3. **Homelab / infrastructure** — oracle: the live system via the MCP (deterministic but *temporal / mutable*). New muscle: time-stamped facts, active-learning (when to re-query reality), contradiction-as-product (config drift = real bug — cf. the 2026-06-29 split-horizon DNS issue).
4. **Computer science as a field** — oracle: reference consensus + the judge ensemble (first *weak* oracle). New muscle: adjudicate without ground truth — judge ensemble + NLI/entailment + belief revision + confidence. **The 3→4 jump is the real thesis test.**
5. **Open / contested knowledge** — oracle: none reliable; conflicting sources (Tilda's graveyard). New muscle: ambiguity / word-sense resolution, source reconciliation, *representing* genuine disagreement rather than resolving it. Earned only after 1–4 harden the machinery.

**Domain-1 consequence (this sizes M1): A&DS has TWO oracles, and that duality is the point** — it lets you build the strong-oracle *and* weak-oracle paths in one domain, so the weak-oracle machinery the later domains need is exercised, not skipped.

- **Execution oracle** — runnable claims (`quicksort faster-than bubblesort, average case`): run both, measure, settle deterministically.
- **Judge / entailment oracle** — conceptual/definitional claims (`a stack is LIFO`, `mergesort is stable`, `Dijkstra requires non-negative weights`): execution can't adjudicate; the deductive schema handles what it can, the LLM-judge handles the novel ones.

Treat the oracle as a **swappable interface** from day one (strategy pattern / pluggable ground-truth source); A&DS registers both implementations. "Next domain" then = author a new schema + register a new oracle — the engine, property library, contradiction logic, and replay buffer stay untouched. If domain 2 forces a rewrite of any of those, the abstraction leaked.

## Milestone 1 — the smallest falsifiable test (A&DS: "does structure buy elimination power, and is the weak-oracle path actually built?")

**Schema = 3 relations with declared properties:**
- `complexity-leq` — a **total order** over complexity classes (`O(1) ≤ O(log n) ≤ O(n) ≤ O(n log n) ≤ O(n²) ≤ O(2ⁿ)`).
- `is-a` — **transitive** (`red-black-tree is-a balanced-BST is-a BST is-a tree`).
- `has-property` — **typed** over a small enum (`stable`, `in-place`, `comparison-based`, `LIFO`, `FIFO`), with declared disjointness where it applies.

Seed **~20 hand-authored ground-truth triples** (the anchors). Have the base model extract candidate triples from a handful of source texts (algorithm descriptions / docstrings). Run the claims through an existing **Datalog / forward-chaining engine** (Soufflé or a small Datalog). Wire **both oracles** behind one interface: an *execution oracle* for runnable performance claims, a *judge/entailment oracle* for conceptual claims.

**Pre-commit, then measure (DRAFT thresholds — approve or adjust before the run, per L3):**

| # | Metric | What it tests | Draft go / kill |
|---|---|---|---|
| 1 | **Closure leverage** = derived ÷ admitted-seed facts | does structure multiply knowledge | **descriptive — calibrate from run 1** (leverage is fan-out-dependent, not a correctness measure, so it can't be honestly pre-committed like a recall/accuracy bar) |
| 2 | **Contradiction recall** on N≥15 planted inconsistencies, **zero LLM calls at check time** | is the deductive immune system real | go ≥ **0.90**, kill < 0.60 |
| 3 | **Comparison accuracy** (`is X faster than Y?` via `complexity-leq` closure) — the shape Tilda failed at ~83% | does deduction fix the measured gap | go ≥ **0.90** (vs Tilda's ~17%), kill < 0.50 |
| 4 | **Conceptual-claim adjudication** — judge/entailment-oracle accuracy on the *non-executable* subset (`stable`, `LIFO`) | is the weak-oracle path built, not skipped | go ≥ **0.80**, kill < 0.60 |
| 5 | **False-contradiction rate** — flagged "violations" that are actually fine | over-strictness (Tilda logged these) | go ≤ **0.10**, kill > 0.25 |

Clearing 1–3 but failing 4 = the engine works but the weak-oracle muscle was skipped (the transfer trap). **Clearing 1–5 = the genome is proven *and* portable.**

> **RESULT — first run (2026-06-29), clingo 5.8 + local Ollama (qwen2.5:7b + gemma2:9b):**
> metric 2 = **1.00**, metric 3 = **1.00** (vs Tilda's ~0.17 on the same comparison shape),
> metric 4 = **0.88** (live judge ensemble, 8/8 scored), metric 5 = **0.00** → **2–5 all GO.**
> Metric 1 = **0.65×** (descriptive; small because the seed set is small and the `is_a`
> chains are shallow — grows with more algorithms/deeper hierarchies). Notable finding from
> the bonus check: the execution oracle disagrees with deduction on **1/4** runnable
> comparisons — the same-complexity-class pair (`quicksort` vs `mergesort`), where the
> coarse deductive order says "neither strictly faster" but execution measures a real
> difference. That's a *genuine resolution gap* between the strong and weak oracles, not a
> bug — worth representing explicitly in later work.

## Milestone 2 — the extraction path ("can the LLM frontend populate the graph, and does the solver backend recover its precision for free?")

M1 proved the solver backend (metrics 2/3/5) and the weak-oracle *tie-breaking* boundary task (metric 4, judge). It left the **other** boundary task untested: **relation extraction** — turning text into typed triples. The thesis names extraction as half of what sets the parameter floor ("the reasoning the base must do at the boundary = relation extraction + tie-breaking"), and L4 names the LLM-frontend ↔ solver-backend seam as the *entire* novelty budget. M1 built only one side of that seam. M2 builds the seam itself and tests one falsifiable claim:

> **The deductive solver recovers extraction precision for free** — an extracted triple that makes the graph UNSAT against the trusted seeds is a likely extraction error, droppable with **zero extra LLM calls**, at near-zero cost to recall.

**Setup.** Hand-label an extraction corpus (`eval/m2_corpus.jsonl`): short algorithm / data-structure descriptions, each with the gold triples it should yield (restricted to the M1 schema — `is_a` / `has_complexity` / `has_property` + the enum). The frozen base model (Ollama) extracts candidate triples; the **consistency filter** (`src/extraction_filter.py`) adds candidates incrementally onto the trusted seed atoms, keeping each iff the graph stays SAT. Extracted triples are stamped `extracted` with their source id (L5).

**Pre-commit, then measure (DRAFT thresholds — approved 2026-06-29, per L3):**

| # | Metric | What it tests | Go / kill |
|---|---|---|---|
| 6 | **Extraction precision** = correct ÷ total extracted | can a *frozen* base populate a typed graph at all | go ≥ **0.80**, kill < 0.50 |
| 7 | **Extraction recall** = correct ÷ gold | does it find enough of the facts | go ≥ **0.70**, kill < 0.40 |
| 8 | **Consistency-filtered precision** — precision after dropping UNSAT-inducing triples (zero LLM calls) | does the solver backend recover precision for free | go: **≥ raw precision** |
| 9 | **Recall retention under filter** = recall after ÷ recall before | the filter must remove errors, not truths | go ≥ **0.95** |

**Kill criterion.** If 6 or 7 falls below its kill bar, a frozen base cannot drive the seam in this domain (revisit prompt / base size — *not* training, L2). If 8 < raw precision **or** 9 < 0.95, the consistency filter buys nothing (or costs truths) and the headline claim is **falsified** — report it and drop the filter rather than tuning it into looking good. The honest finding either way is metrics 8+9 together.

> Caveat (inspectability): the incremental filter is **order-dependent** — when two mutually consistent-with-seeds candidates jointly violate a constraint, which one survives depends on arrival order. M2 documents this; full minimal-conflict-set localization (TMS/ATMS) is later work, not M2.

> **RESULT — first run (2026-06-29), qwen2.5:7b via Ollama, 15-text corpus / 41 gold triples:**
> raw extraction precision = **0.59**, recall = **0.59** (both **MID** — below go, above kill).
> The filter dropped **0** candidates → filtered precision = raw, recall retention = 1.00, so
> metrics **8/9 are *vacuously* GO**: the filter neither helped nor hurt. The headline claim
> ("the solver recovers extraction precision for free") is therefore **untested, not
> confirmed** — *none of the extraction errors were contradiction-shaped* against the seeds.
>
> Error breakdown (diagnostic) — the failures are overwhelmingly **canonicalization, not
> reasoning**; the base grasped every text but emitted non-schema surface forms:
> - **entity drift** — `bubble_sort` ≠ `bubblesort` (this one mismatch sank the whole
>   bubblesort entry, all facts semantically correct) — and it is *why the filter caught
>   nothing*: a fact under a different constant can't violate a seed constraint.
> - **value drift** — `sorts_in_place`/`operates_in_place` ≠ `in_place`,
>   `last_in_first_out_ordering` ≠ `lifo`, `first_in__first_out` ≠ `fifo`.
> - **structure drift** — property folded into the object: `is_a(quicksort,
>   comparison_based_sorting_algorithm)` instead of `is_a … sorting_algorithm` + `has_property
>   … comparison_based`.
> - **a few world-knowledge extras** not stated in the text (`binary_search_tree`/
>   `red_black_tree` `has_complexity o_logn`).
>
> Reading: the M1-domain extraction bottleneck is **entity linking / lexical normalization to
> the controlled vocabulary** (a standard NLP sub-task), *not* the base model's semantic
> competence — true precision/recall are materially higher than 0.59 once surface forms are
> canonicalized. And the consistency filter, though correct (unit-tested), is **inert on a
> clean corpus + competent model**; it earns its keep where errors *are* contradiction-shaped
> (planted clashes; domain-3 config drift), not on first-pass extraction here. No tuning to
> make 6–9 look better (L3) — the honest next move is a canonicalization step, then re-measure.

### M2-filter — isolating the consistency-filter claim (does the deductive immune system catch *extraction* errors?)

Metrics 8/9 came out *vacuous*: on a clean corpus a competent base makes canonicalization errors, not contradiction-shaped ones, so the filter had nothing to catch. This sub-milestone tests what 8/9 should have — the **filter mechanism itself** — by feeding it labeled candidate triples directly (no extractor, so the 0.59 canonicalization noise can't confound the signal; fully offline / deterministic, clingo only).

**Candidate set (`eval/m2_filter_cases.jsonl`), each triple tagged:**
- `true` — consistent with ground truth; the filter **must keep** (includes near-misses on seeded entities to stress soundness).
- `error_contradictory` — false *and* contradiction-shaped vs the seeds/schema; the filter **should drop**.
- `error_consistent` — false but *not* contradiction-shaped (wrong fact on an unseeded entity); the filter **cannot** drop — the honest ceiling, reported not gated.

An **honesty meta-test** asserts every `error_contradictory` really is UNSAT against the seeds and every `true`/`error_consistent` really is SAT — so the set cannot silently rig the metric by mislabeling.

**Pre-commit, then measure (DRAFT thresholds — approved 2026-06-29, per L3):**

| # | Metric | What it tests | Go / kill |
|---|---|---|---|
| 10 | **Filter error-catch rate** = dropped ÷ `error_contradictory` | does the deductive filter catch contradiction-shaped extraction errors | go ≥ **0.95** (expect 1.0), kill < 0.80 |
| 11 | **Filter false-drop rate** = `true` dropped ÷ `true` | soundness — it must remove errors, not truths | go = **0.00**, kill > 0.05 |
| 12 | **Precision lift** = filtered precision − raw precision (on the mixed set) | does filtering actually recover precision where errors are catchable | go **> 0** (+ report the `error_consistent` ceiling) |

**Kill criterion.** 10 < 0.80 → the deductive immune system is broken (it scored 1.00 on M1 metric 2, so this would be a regression). 11 > 0.05 → unsound (drops truths) → the "for free" claim is **falsified**. 12 ≤ 0 → filtering buys nothing even where errors are catchable → **falsified**. Order-dependence is a known limitation (a `true` fact can be dropped if a prior batch candidate already pushed the graph to a state where it conflicts) — measured on natural order and demonstrated separately, not hidden.

> **RESULT — M2-filter run (2026-06-29), clingo only, 24 labeled candidates (10 true /
> 10 contradictory / 4 consistent-error):**
> metric 10 (error-catch) = **1.00**, metric 11 (false-drop) = **0.00**, metric 12
> (precision lift) = **+0.30** (0.42 → 0.71, zero LLM calls) → **10–12 all GO.**
> The honest ceiling held exactly: **0/4** consistent-but-wrong errors caught — by
> construction the filter cannot see errors that don't violate a constraint. The
> order-dependence limitation is real and reproduced in a focused test (an unseeded
> entity given two complexities: the first-arriving one survives).
>
> Reading: the consistency-filter claim is **confirmed where it applies** — the deductive
> immune system that caught planted contradictions in M1 (metric 2 = 1.00) also catches
> *contradiction-shaped extraction errors*, soundly and for free. Its leverage is bounded
> by two things M2 measured: (a) errors must be contradiction-shaped — wrong-but-consistent
> facts pass (the 0/4 ceiling); (b) the extracted entity must be *canonicalized to a
> constrained constant*, or it conflicts with nothing (the `bubble_sort`≠`bubblesort`
> finding from the M2 run). So filtering and canonicalization are **complementary**: the
> filter's reach grows as canonicalization and seed coverage grow.

### M2.1 — canonicalization (attack the measured extraction bottleneck)

The M2 run located the bottleneck: a competent base extracts the right *meaning* in the wrong *surface form* (`bubble_sort`≠`bubblesort`, `last_in_first_out_ordering`≠`lifo`, `sorts_in_place`≠`in_place`). The standard fix is **entity linking / lexical normalization** (mention → canonical KB entry) plus **normalization to a controlled vocabulary** (the closed property/complexity enums) — see GLOSSARY.

`src/canonicalization.py` is a **pure, deterministic post-processor** (no training — L2; no LLM call), derived from the *schema's semantics*, NOT from the corpus's specific mistakes (memorizing the eval's error strings would be cheating):
- **Entity linking (open set):** canonical key = lowercase + strip non-alphanumeric; exact-key match to the known entity set (conservative — no fuzzy matching, so no false merges); unknown mentions fall back to lexical-normal form.
- **Controlled-vocabulary mapping (closed sets):** negation-aware keyword rules encoding what each enum value *means*, plus an asymptotic-notation normalizer (`O(n log n)`/`linearithmic` → `o_nlogn`). Unmappable closed-slot values are dropped.

**Out of scope (honest bounds):** *structure drift* (a property folded into an `is_a` object) and *hallucinated extras* not in the source text — canonicalization fixes surface forms, not mis-parses or faithfulness. If the residual error is dominated by these, that is the finding and the next bottleneck.

**Pre-commit, then measure (DRAFT thresholds — approved 2026-06-29, per L3):**

| # | Metric | What it tests | Go / kill |
|---|---|---|---|
| 13 | **Canonicalized precision** — live extraction, post-canon, vs gold | does surface-form normalization recover precision | go ≥ **0.80**, kill < 0.60 |
| 14 | **Canonicalized recall** — post-canon, vs gold | does it recover the missed-by-surface-form truths | go ≥ **0.70**, kill < 0.50 |
| 15 | **Idempotence / soundness** — `canonicalize(t) == t` for every gold & seed triple | already-canonical input is untouched; no entity false-merge | go = **1.00** (must) |

**Kill criterion.** 13 < 0.60 or 14 < 0.50 → surface forms weren't the real bottleneck (or the approach failed) — reconsider. 15 < 1.00 → the canonicalizer corrupts good data → bug, fix before trusting 13/14. A **MID** on 13/14 is itself informative: canonicalization is necessary-but-not-sufficient and the residual (structure drift / faithfulness) is the next lever. The run reports raw → canon side by side so the lift is explicit; no tuning the alias rules to the eval (L3).

> **RESULT — M2.1 run (2026-06-29), qwen2.5:7b via Ollama, same 15-text corpus:**
> canonicalized precision = **0.82** (go ≥ 0.80) and recall = **0.78** (go ≥ 0.70) → **13/14
> both GO**; idempotence (15) = **1.00** (offline test: untouched on all seeds + gold, no
> false merge). The lift over the M2 baseline: **precision 0.59 → 0.82, recall 0.59 → 0.78**
> (2 unmappable candidates correctly dropped). The bottleneck was confirmed to be surface
> form, not the base's competence — entity linking (`bubble_sort`→`bubblesort`) and
> controlled-vocabulary mapping (`sorts_in_place`→`in_place`, `last_in_first_out_ordering`→
> `lifo`) recovered ~8 facts for zero LLM calls and zero training (L2).
>
> The post-canon consistency filter still dropped **0** — the residual errors are structure
> drift and world-knowledge extras (both schema-*consistent*), exactly the M2-filter ceiling.
> So the residual bottleneck has moved from surface form to **structural extraction
> faithfulness** (e.g. a property folded into an `is_a` object); that, not canonicalization,
> is the next lever if extraction P/R needs to climb further.

## Milestone 3 — domain 2 (a codebase): "is the engine swappable, and does the deductive core transfer?"

The load-bearing architectural bet (Milestone 0): moving domains = **author a new schema + register a new oracle**, with *the engine, the typed triple store, and the contradiction logic untouched*. If domain 2 forces a rewrite of any of those, the abstraction leaked. M3 is the first test of that bet — and the curriculum's first oracle weakening (execution → compiler/AST: still deterministic and a real artifact, but now over static structure).

**Prior art / standard terms (do NOT reinvent the syntactic half):** CodeQL, Glean, Doop, Soufflé, tree-sitter, ArchUnit. Target is a **Python** codebase (this repo, dogfooding), so the mature syntactic tool is the **stdlib `ast`** module — used as the deterministic fact source, no new parser dependency. The architecture-rule check is the **ArchUnit** idea (a declared constraint vs reality).

**First cut (scoping):** deterministic AST extraction + hand-authored architecture rules (the "intent"). The new domain-2 muscle exercised here is **intent-vs-reality contradiction** ("contradiction-as-product": stale docs / architecture violations). LLM extraction-at-scale and cross-artifact correspondence are **deferred to M3.1** — the LLM extraction path is already proven (M2/M2.1); the first cut isolates *swappability + the new oracle*.

**New components (all new files except one new Oracle impl):**
- `schema/code.lp` — relations `defines` / `calls` / `imports` / `inherits`; `calls`→`reaches` and `imports`→`imports_trans` as **transitive closures**; integrity constraints = **no inheritance cycle** + a **layering rule** (core `src/` must not import the `eval/` harness).
- `src/code_extraction.py` — deterministic `ast` → typed `Triple`s.
- `AstOracle` (in `oracle.py`) — the new **strong oracle**: answers `reaches(A,B)?` by independent graph BFS over the AST call facts, cross-checking the engine's transitive closure (as `ExecutionOracle` cross-checked deductive order in domain 1). Registered behind the **unchanged** `Oracle` interface.

**Reused UNTOUCHED (the headline claim):** `inference_engine.py`, `knowledge_graph.py`, `extraction_filter.py`, `canonicalization.py`.

**Pre-commit, then measure (DRAFT thresholds — approved 2026-06-29, per L3):**

| # | Metric | What it tests | Go / kill |
|---|---|---|---|
| 16 | **Core reuse / swappability** — line diffs in engine/KG/filter/canon across M3 | did the abstraction hold | go = **0 diffs**, kill = any change needed |
| 17 | **Code contradiction recall** — planted arch-violations + inheritance cycles (N≥10) caught deductively, zero LLM | does the immune system transfer | go ≥ **0.90**, kill < 0.60 |
| 18 | **Reachability accuracy** — deductive `reaches(A,B)` closure vs AST+BFS oracle (N≥15 pairs) | does closure transfer + does the new oracle agree | go ≥ **0.90**, kill < 0.50 |
| 19 | **False-contradiction rate** — real repo facts + consistent controls produce no spurious violations | over-strictness | go ≤ **0.10**, kill > 0.25 |

**Kill criterion.** 16 ≠ 0 → the seam leaked: the whole architectural bet fails for now — report *exactly* what forced the change rather than papering over it. 17 < 0.60 or 18 < 0.50 → the deductive core does not transfer. 19 > 0.25 → the code schema is over-strict. Clearing 16–19 = the engine is proven portable across a domain *and* an oracle change — the genome is not A&DS-specific.

> **RESULT — M3 run (2026-06-29), clingo only (no LLM), `ast` extraction over this repo:**
> metric 16 (swappability) = **0 diffs** in engine/KG/filter/canon, metric 17 (code
> contradiction recall) = **1.00** (11/11 planted inheritance cycles + layering violations),
> metric 18 (reachability accuracy) = **1.00** (16/16 vs gold, and the engine's ASP closure
> agrees with the independent `AstOracle` BFS on **1.00** of pairs), metric 19
> (false-contradiction) = **0.00** → **16–19 all GO.**
> Extraction-at-scale: **313 facts** pulled from the real `src/` + `eval/` tree, all
> deductively consistent — the dogfooded layering rule (`src/` must not import `eval/`)
> *holds in reality*. The whole new domain is a new `schema/code.lp` + a new `AstOracle`
> (registered behind the unchanged `Oracle` interface) + a deterministic AST extractor; the
> engine, typed triple store, contradiction logic, and canonicalizer were reused **byte-for-
> byte**. **The swappability bet is confirmed — the genome is not A&DS-specific.**
>
> Honest bounds: this first cut is deterministic (no LLM) and the call graph is resolved by
> *unique simple name* (ambiguous/dynamic calls are conservatively skipped), so reachability
> is exact only on the unambiguous subgraph. LLM extraction-at-scale, cross-artifact
> correspondence, and intent-extracted-from-docs are **M3.1** (next), not claimed here.

## Milestone 4 — domain 3 (homelab/infrastructure): "does the engine transfer to a temporal/mutable oracle, and is config drift caught as contradiction-as-product?"

The curriculum's first oracle weakening into **time**: the oracle is the live system via the MCP — still deterministic when queried, but *mutable*, so a fact true at T1 can be false at T2. Three new muscles: **time-stamped facts**, **active-learning** (when to re-query reality), and **contradiction-as-product** (config drift = a real, actionable bug — cf. the 2026-06-29 split-horizon DNS issue).

**Clean split — keep ASP for contradiction, Python for time:**
- **Deductive layer (`schema/state.lp`):** state is binary facts over a compound `resource.attribute` key — `observed(K,V)` and `desired(K,V)` — so it **reuses `Triple` and the engine unchanged** (binary predicates, like every prior domain). Drift constraint `:- desired(K,V1), observed(K,V2), V1!=V2` makes drift a deductive contradiction; plus single-value-per-key integrity.
- **Temporal layer (`src/staleness.py`):** snapshots carry timestamps; an **active-learning / staleness policy** decides which keys to re-query from age + volatility, and a snapshot-diff detects change. Time arithmetic stays in inspectable Python, not crammed into clingo.

**Snapshot source (decided 2026-06-29): synthetic, modeled on the real homelab** (pihole / npm / proxmox shapes, placeholder IPs/hostnames) — zero network, zero real topology in the repo, fully reproducible. The eval is offline/deterministic against the committed snapshot; "re-querying" = loading a later snapshot. A live-MCP provider is a later increment.

**New components (all new files except one new Oracle impl):** `schema/state.lp`; `src/state_extraction.py` (snapshot JSON → `observed` triples, injectable provider); `StateOracle` in `oracle.py` (behind the unchanged `Oracle` interface); `src/staleness.py` (re-query policy + diff); `eval/run_m4.py` + fixtures.

**Reused UNTOUCHED (the swappability claim, now vs a temporal oracle):** `inference_engine.py`, `knowledge_graph.py`, `extraction_filter.py`, `canonicalization.py`.

**Pre-commit, then measure (DRAFT thresholds — approved 2026-06-29, per L3):**

| # | Metric | What it tests | Go / kill |
|---|---|---|---|
| 20 | **Core reuse / swappability** — diffs in engine/KG/filter/canon across M4 | abstraction holds vs a temporal oracle | go = **0**, kill = any |
| 21 | **Drift-detection recall** — planted config drifts (N≥10) caught deductively, zero LLM | contradiction-as-product works | go ≥ **0.90**, kill < 0.60 |
| 22 | **False-drift rate** — matching desired/observed not flagged | over-strictness | go ≤ **0.10**, kill > 0.25 |
| 23 | **Active-learning change-detection recall** — over a simulated snapshot stream, fraction of real changes the staleness policy re-queries in time | the temporal muscle | go ≥ **0.90**, kill < 0.60 |
| 24 | **Query savings** — (naive − policy queries) / naive on that stream | active learning actually saves work | go **> 0** (descriptive) |

**Kill criterion.** 20 ≠ 0 → the seam leaked against a temporal oracle. 21 < 0.60 → drift detection doesn't work. 22 > 0.25 → over-strict. 23 < 0.60 → the staleness policy misses real changes (worse than just re-querying everything). 24 ≤ 0 → active learning buys nothing. Clearing 20–24 = the genome handles a mutable oracle and turns drift into a detectable product.

> **RESULT — M4 run (2026-06-29), clingo only (no LLM), synthetic homelab snapshot:**
> metric 20 (swappability) = **0 diffs** in engine/KG/filter/canon, metric 21 (drift recall)
> = **1.00** (11/11 planted drifts, incl. the split-horizon DNS bug), metric 22 (false-drift)
> = **0.00** (14-key baseline + 5 controls clean), metric 23 (active-learning recall) =
> **1.00** (10/10 changes caught), metric 24 (query savings) = **0.60** (112 vs 280 naive
> queries over 20 ticks) → **20–24 all GO.**
> The third oracle type — *temporal/mutable* — is handled with the engine, triple store,
> contradiction logic, and canonicalizer reused **byte-for-byte** (the new domain is a new
> `schema/state.lp` + a new `StateOracle` + a snapshot extractor + a Python staleness
> policy). Config drift surfaces as an enumerable derived `drift/2` product (you get the
> *list* of drifted keys, not just UNSAT); time/active-learning stays in inspectable Python.
> The swappability bet now holds across **three domains and three oracle kinds** (execution,
> AST, live-state). Honest bounds: the snapshot is synthetic and the active-learning recall
> is 1.00 *because* the simulated changes persist past their key's TTL (realistic for infra);
> a sub-TTL flip is missed by design (demonstrated in a focused test), and a live-MCP
> provider is deferred.

## Milestone 5 — domain 4 (CS-as-a-field): "the real thesis test — does structure still buy elimination power when the oracle is WEAK?"

The 3→4 jump DIRECTION flagged as the real test. Domains 1–3 had a *strong* oracle (execution / AST / live-state) handing out ground truth; domain 4 has **none** — claims about CS-as-a-field can't be run or parsed, so the oracle is fallible (reference consensus + the LLM-judge ensemble). The bet either generalizes to the weak boundary or it doesn't.

**Made falsifiable without world-ground-truth:** with a weak oracle the system must (a) settle *derivable* claims by **deductive closure** over a small high-confidence axiom set with **zero LLM calls**, (b) fall back to the **judge ensemble** (reused from M1) where claims aren't derivable, and (c) keep its belief set consistent via **belief revision (AGM)**. (a) and (c) are checkable *deductively* regardless of whether any single claim is "true," so the backbone metrics don't depend on the flaky judge.

**New components (all new files; frozen core untouched):**
- `schema/csfield.lp` — `subfield_of` and `subsumes`, both **transitive + acyclic** (strict partial orders); a cycle = a deductive contradiction. Multi-hop queries answered by closure.
- `src/belief_revision.py` — **AGM minimal revision by epistemic entrenchment**: a *pure function* over triples (no KG mutation → core stays frozen) that removes the lowest-confidence members only as needed to restore consistency (engine UNSAT check). Greedy/entrenchment-ordered — not full TMS minimal-conflict-set localization.
- Reuse `JudgeEnsemble` as the weak oracle (injectable claim-text formatter; `judge_ensemble.py` is not frozen core).

**Deferred to M5.1 (stated, not skipped):** model-based **NLI/entailment**, **abstention/calibration** on genuinely-contested claims (the anti-Tilda-graveyard muscle), and full TMS conflict-set localization.

**Reused UNTOUCHED (swappability, now vs a weak oracle):** `inference_engine.py`, `knowledge_graph.py`, `extraction_filter.py`, `canonicalization.py`.

**Pre-commit, then measure (DRAFT thresholds — approved 2026-06-29, per L3):**

| # | Metric | What it tests | Go / kill |
|---|---|---|---|
| 25 | **Core reuse / swappability** — diffs in engine/KG/filter/canon | abstraction holds vs a weak oracle | go = **0**, kill = any |
| 26 | **Deductive reliability on derivable CS claims** (zero LLM) | structure settles multi-hop claims here too | go ≥ **0.90**, kill < 0.70 |
| 27 | **Structure lift vs judge-alone** = assisted − judge-alone accuracy *(live judge; SKIP w/o Ollama)* | structure must not hurt at the weak boundary | go ≥ **0**, kill < 0 (magnitude descriptive) |
| 28 | **Belief-revision correctness** — designed conflicts (N≥10): retract the weakest, end consistent | AGM revision works | go ≥ **0.90**, kill < 0.60 |
| 29 | **Final-belief-set consistency** — after folding a contradictory claim stream | never settles into contradiction | go = **1.00**, kill < 1.00 |

**Kill criterion.** 25 ≠ 0 → seam leaked vs a weak oracle. 26 < 0.70 → structure doesn't transfer to CS-field claims. 27 < 0 → **structure actively hurts at the weak boundary, a real dent in the thesis** (report, don't bury). 28 < 0.60 → belief revision is broken. 29 < 1.00 → the system can be driven into permanent contradiction. Honest read: if 27 ≈ 0, structure's value here is *reliability + zero-LLM cost* on derivable claims, not raw accuracy gain — reported with a per-subset breakdown.

> **RESULT — M5 run (2026-06-29), clingo + live judge (qwen2.5:7b + gemma2:9b):**
> metric 25 (swappability) = **0 diffs**, metric 26 (deductive reliability) = **1.00** (9/9
> derivable claims, zero LLM), metric 27 (structure lift) = **+0.20** — assisted **1.00** vs
> judge-alone **0.80** — metric 28 (belief-revision correctness) = **1.00** (10/10 designed
> conflicts), metric 29 (final consistency) = **1.00** → **25–29 all GO.**
> The real thesis test passed *non-trivially*: the live judge alone got 0.80 (it fumbled
> derivable claims — mostly the reverse-direction ones a transitive order rules out), and
> deductive structure rescued them to 1.00 with **zero LLM calls**. So even at the WEAK
> boundary, structure buys elimination power — exactly the genomic-bottleneck claim
> (cf. M1's comparison-accuracy result, now reproduced where the oracle is fallible). Belief
> revision keeps the belief set consistent under a contradictory stream, retracting the
> least-entrenched fact (AGM by confidence). The genome now holds across **four domains and
> four oracle kinds (execution, AST, live-state, weak/judge)** — the 3→4 jump DIRECTION
> flagged as make-or-break is cleared. Honest bounds: small hand-curated reference set; the
> +0.20 magnitude is local-judge-dependent (the *sign* is the falsifiable claim, and it's
> positive); NLI/entailment, abstention/calibration, and full TMS localization remain M5.1.

### M5.1 — calibrated abstention (the weak oracle that knows when NOT to answer)

The anti-Tilda-graveyard guard: a fallible oracle must abstain on what it can't settle rather than force an answer. The weak oracle becomes a three-way adjudicator — **TRUE / FALSE / CONTESTED** — committing only when two decorrelated calibration signals agree:
- **Ensemble agreement (self-consistency):** the decorrelated families (qwen + gemma) agree on direction *and* the score is decisive (far from 0.5).
- **Negation consistency (the NLI/entailment probe, folded in):** score the claim *and its negation*; a calibrated model gives `P(X) + P(¬X) ≈ 1`. Confident-on-both (or unsure-on-both) → it doesn't actually know → CONTESTED.

Deduction runs first and overrides — we never abstain on what we can prove (a deterministic safety property, unit-tested, not a flaky live metric). **Full TMS minimal conflict-set localization stays deferred to M5.2** (orthogonal belief-revision quality, off the critical path to domain 5).

**Honest framing (L3):** genuinely uncertain outcome. Local 7–9B models may be uniformly overconfident and fail to separate contested from settled, in which case the live metrics come back MID/KILL — *an informative result* (calibrated abstention would then need more-decorrelated/larger judges, shaping how domain 5 must work). Not assumed to pass.

**New components:** `src/calibration.py` (`CalibratedAdjudicator`, pure decision logic over signals); small backward-compatible `judge_ensemble.py` extension (per-model `scores()` + negation scoring); `eval/m5_contested.jsonl`. **Reused untouched:** engine / KG / filter / canon / `belief_revision.py`.

**Pre-commit, then measure (DRAFT thresholds — approved 2026-06-29, per L3):**

| # | Metric | What it tests | Go / kill |
|---|---|---|---|
| 30 | **Core reuse / swappability** — diffs in the frozen core | abstraction holds | go = **0**, kill = any |
| 31 | **Contested-abstention recall** — contested claims marked CONTESTED *(live; SKIP w/o Ollama)* | abstains when it should | go ≥ **0.60**, kill < 0.30 |
| 32 | **Over-abstention rate on settled claims** *(live)* | doesn't hide behind "contested" | go ≤ **0.30**, kill > 0.50 |
| 33 | **Committed accuracy − judge-alone-forced accuracy** *(live)* | abstaining on the hard ones raises committed accuracy | go ≥ **0**, kill < 0 |

**Kill criterion.** 30 ≠ 0 → seam leaked. 31 < 0.30 → can't detect contested (the graveyard guard fails — likely a local-model-calibration limit, report it). 32 > 0.50 → over-abstains (useless). 33 < 0 → calibration *hurts*. The deduction-overrides-abstention safety property is enforced and offline-tested regardless of the live numbers.

## Later increments (sketch only — do NOT build yet)

- LLM-as-judge ensemble as boundary tie-breaker; NLI grounding/entailment check.
- Replay buffer + active-learning query policy (derive vs. look up).
- PEFT adapter for domain *expression* — only after the deductive core is proven.
- Provenance/audit trails as the labeled set for a future learned routing policy.

## Hard constraints

- **Runs locally** (Ollama). Cloud only as an optional boundary tie-breaker, and only if the domain is non-sensitive.
- **No large training runs.** Growth is deductive closure, not gradient descent.
- **Framework-light, inspectable.** Use established engines (Datalog/clingo/SMT/TMS) as libraries; no heavy agent frameworks.
- **Standard terminology only** (the rule above + `GLOSSARY.md`).
- **Deterministic, offline, network-free tests.** New work ships with tests.

## How to work together

- Read first, plan second, code third. Always.
- One idea per commit; each ships with a test and, for a milestone, a pre-committed metric.
- Don't oversell it and don't undersell it. It's a research experiment. Treat it like one.
- Default git branch `main`; no commit attribution trailers.
