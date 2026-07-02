# Findings — the hypothesis test, and what it split apart

*2026-07-01. Written for a skeptical outside reader. Every number below comes from a
pre-registered run whose thresholds were committed before execution; the pre-registration
documents (with RESULT blocks) are in `experiments/`. Everything is reproducible offline
against local models except where noted.*

## Abstract

We tested the "genomic bottleneck" thesis for language models: that knowledge should live
in a non-parametric store and composition in a deductive solver, so that a **small frozen
model plus structure can match a much larger model alone**. The thesis, as stated, is
**falsified** in our test regime — but the falsification is unusually informative, because
the experiments decomposed the thesis into its two constituent claims and they came apart
cleanly:

1. **Knowledge outside the weights is load-bearing.** A 7b model with the relevant atomic
   facts retrieved into context beat a 14b model answering from parameters at every
   composition depth (0.91–0.97 vs 0.85–0.89, N=100/cell), at half the inference cost.
2. **The solver as composer is mostly redundant at this scale.** Given the same facts,
   in-context reasoning tracked deductive closure (0.95 vs 1.00 at depth 4+). Deduction's
   measured edge is a *constant* +0.11–0.15 plus zero marginal cost and determinism — not
   the depth-compounding advantage the thesis predicted.
3. **The model cannot supply the solver's facts.** Generative extraction of exact
   structure failed at every size tested (best: 0.60 recall at 14b): models hold
   hierarchies as a *soft partial order* — semantically true, structurally imprecise —
   naming ancestors when asked for parents.

Four pre-registered kill bars fired across the project's lifetime and all four stayed on
the record. The surviving value of the deductive layer is not accuracy at depth; it is
cost, determinism, and the operations in-context reasoning structurally cannot perform
(latent multi-source conflict detection, drift-as-contradiction, consistency guarantees).

## 1. The claim under test

Frontier models store world knowledge in their parameters. Biology does not: the genome
is information-poor and encodes priors and learning rules, not the connectome (Zador
2019). The bet: split the substrates the same way —

- **knowledge** = a typed knowledge graph (non-parametric),
- **composition** = a forward-chaining inference engine (clingo / ASP),
- **the model** = a small frozen base used only at the boundary (extract atomic facts;
  tie-break what deduction cannot settle).

Made falsifiable as two hypotheses (`experiments/HYPOTHESIS_TEST.md`):

- **H1 (composition gap).** On multi-hop questions, a plain model declines with hop depth
  while deduction over atomic facts stays high; the gap **grows with depth**.
- **H2 (parameter floor).** A small base that only extracts depth-1 facts, plus the
  solver, matches a much larger monolith at hard depths.

## 2. Method

**Domain.** Python `issubclass` over a fixed 127-class stdlib inventory (exceptions, core
types, `numbers`, `collections.abc`, `io`) — chosen because ground truth is **computed,
not authored** (the project's earlier milestone suite, M1–M6, was retro-diagnosed as
near-tautological precisely because its gold sets were self-authored; see §8 and the
banner in `RESULTS.md`). Direct edges come from `__bases__` plus a minimal completion for
ABC virtual registration, and the transitive closure of the edge graph is asserted equal
to `issubclass` over all ~16k ordered pairs, so truth and hop-depth cannot disagree.
502 true pairs, depths 1–6.

**Questions.** Balanced forced-choice ("is A a subclass of Z?"): per depth bucket
{1, 2, 3, 4+}, equal true chains and false controls (reversed pairs + unrelated pairs).
The True/False **letter assignment is randomized per question**, which matters (§4.1).

**Conditions (Phase 1).**
- `monolith-direct` — the bare question; knowledge and composition both in weights.
- `rag-model` — the true atomic edges for the question's neighborhood presented in
  context (padded with true-but-irrelevant distractor edges to 30 facts), model composes.
- `deduce` — the *same* fact block, composed by the inference engine; zero LLM calls.

**Power and discipline.** Pilots at N=24/cell; the main run at **N=100/cell** with Wilson
95% intervals. Every phase pre-committed thresholds and kill criteria in writing before
running (`experiments/PHASE0.md`, `PHASE0_1.md`, `PHASE0_2.md`, `PHASE1.md`); per-row
token and latency costs recorded. Models: qwen2.5 at 0.5b/1.5b/3b/7b/14b, local, frozen,
temperature 0.

## 3. Results

### 3.1 Verification across sizes is a cliff, not a gradient (Phases 0, 0.1)

| model | overall acc by depth (d=1/2/3/4+) | failure mode |
|---|---|---|
| 0.5b | 0.58 / 0.58 / 0.33 / 0.58 | answered the letter "A" 96/96 times — format-degenerate |
| 1.5b | 0.58 / 0.71 / 0.54 / 0.54 | follows format; denies most positive claims (true chains: 0.21) |
| 3b | 0.50 / 0.54 / 0.54 / 0.50 | **universal denial** — true chains 0.04; denied `tuple → object` |
| 7b | 0.88 / 0.92 / 0.92 / 0.71 | competent |
| 14b | 0.88 / 0.88 / 0.92 / 0.79 | competent; ≈ 7b (mean gap +0.01) |

Two methodological notes that generalize. First, **randomized letter assignment exposed
degenerate strategies instead of rewarding them** — a fixed mapping would have scored the
0.5b's all-"A" policy near 75% on an unbalanced set. Second, sub-7b failure is a
**truth-value bias** (systematic denial of positive claims, worse than chance on true
statements), not ignorance — a behavior that would silently poison any pipeline using
small models as verifiers.

### 3.2 Models cannot emit exact structure (Phase 0.2 — pre-registered DEAD)

Generative extraction — "list the direct base classes of X, exactly `X.__bases__`" —
scored against computed gold, micro-averaged over a 60-class sample:

| model | direct recall | truth precision | strict precision |
|---|---|---|---|
| 0.5b | 0.16 | 0.36 | 0.10 |
| 1.5b | 0.31 | 0.41 | 0.25 |
| 3b | 0.12 | 0.20 | 0.15 |
| 7b | 0.29 | 0.79 | 0.33 |
| 14b | 0.60 | 0.76 | 0.49 |

No size clears the pre-registered floors (0.70 recall / 0.80 truth precision). The
instructive comparison: 14b *verifies* depth-1 pairs at 0.88 but *reconstructs* exact
direct edges at 0.60, and half of what it emits is true-but-indirect (truth precision
0.76 vs strict 0.49) — it answers "ancestor" when asked for "parent" (`IndexError →
Exception`, skipping `LookupError`), plus occasional direction flips (`numbers.Real` as a
base of `numbers.Complex`). **Models hold hierarchies as a soft partial order, not as
exact hops.** This killed H2's extraction leg: the small model cannot build the solver's
fact store. (A scoring-parser bug was found and fixed during this phase; the DEAD verdict
survived re-scoring of the same raw transcripts — both numbers are on the record.)

### 3.3 The composition test: H1 falsified (Phase 1)

400 questions, 100 per depth cell, all three conditions, both competent sizes:

| condition | d=1 | d=2 | d=3 | d=4+ |
|---|---|---|---|---|
| deduce | 1.00 | 1.00 | 1.00 | 1.00 |
| 14b monolith | 0.85 | 0.85 | 0.87 | **0.89** |
| 14b rag | 0.99 | 0.87 | 0.88 | 0.95 |
| 7b monolith | 0.90 | 0.88 | 0.83 | 0.79 |
| 7b rag | **0.97** | **0.94** | **0.91** | **0.96** |

(Wilson half-widths ≈ ±0.05–0.07 per cell.)

- **H1's premise failed at the primary model:** 14b is flat in depth — slightly
  *improving* (chains-only slice: 0.72 → 0.78). The decay our pilot showed at N=24
  (0.88 → 0.79) did not replicate at N=100; it was sampling noise. Pre-registered
  verdict: **H1_FALSIFIED** (monolith decay −0.04 against a ≥0.10 bar; gap growth −0.04).
- **The pre-registered flag fired:** rag tracks deduce at depth (0.95 vs 1.00). Given
  true atoms, in-context composition suffices; deduction's edge over the best monolith is
  a constant +0.11–0.15, not depth-scaling.
- **Exploratory:** 7b *does* decay (chains 0.88 → 0.60), so H1's shape exists one size
  below the primary — and 7b+rag beats the 14b monolith everywhere.
- **Cost** (per question / total over 400): monolith ~75 tokens; rag ~345 tokens (14b rag
  455s total, 7b rag 90s, 14b monolith 196s); deduce 0 tokens, ~0s.

## 4. The reframe — what the falsification isolated

The thesis bundled two claims that had never been separated:

**(a) knowledge belongs outside the weights** and **(b) composition belongs in a solver.**

Phase 1's design — monolith vs rag vs deduce on identical questions and identical fact
blocks — separates them, and they came apart:

| claim | verdict | evidence |
|---|---|---|
| the store is load-bearing | **supported** | 7b+facts > 14b-alone at every depth, at half the cost |
| the solver as composer | **redundant at this scale** | rag ≈ deduce at depth; gap constant, not growing |
| the model as extractor | **unreliable** | 0.60 recall at best; hierarchy flattening at 5/5 sizes |

What survives for the deductive layer is exactly what the project's earlier
infrastructure milestones (M1–M6) demonstrated but could not honestly weigh, because
their evals were self-authored: **zero marginal cost** (0 tokens vs ~345/question for the
same answers), **determinism and guarantees** (a closure is correct or the harness is
broken — no 0.95), and the operations in-context reasoning structurally cannot do:
**latent multi-source conflict detection** (three pairwise-consistent claims forming a
cycle — M6 measured 1.00 deductive recall vs 0.00 for pairwise comparison),
**drift-as-contradiction** over live state (M4), and belief-set consistency under
contradictory streams (M5). The solver is not a better reasoner than a 14b at this scale;
it is a *free, exact* one with a different failure surface.

The corrected architecture this implies is mundane and useful rather than novel and
grand: **deterministic extractors** (AST, snapshots, databases — never generative recall)
feeding a **non-parametric store**, retrieved into a **small model** for composition,
with the **solver as auditor** (consistency, conflicts, drift) rather than as the
reasoning engine.

## 5. A convergent secondary finding

Three independent measurements now say the same thing:

- M2 (LLM extraction, 2026-06-29): correct *meaning*, wrong *structure* — properties
  folded into `is_a` objects ("structure drift").
- The witness-cut experiments: elicitation dominates; self-reported confidence and
  sampling stability carry no truth signal; errors are consistent-shaped.
- Phase 0.2 (five sizes): hierarchy flattening — ancestors for parents, 0.88
  verification vs 0.60 exact generation at 14b.

**LLMs emit semantically-true but structurally-imprecise facts.** Any system that needs
exact structure (a type hierarchy, a dependency graph, a schema) should obtain it from a
deterministic source and use the model only where meaning, not structure, is the payload.

## 6. Relation to prior art

The store-is-load-bearing half is consistent with, and anticipated by, the
retrieval-augmentation literature: RETRO (Borgeaud et al. 2021) matched models ~25× its
size using retrieval; Atlas (Izacard et al. 2022) did similar for knowledge-intensive
tasks; PAL (Gao et al. 2022) showed offloading *computation* to an interpreter beats
in-weights execution. We do not claim novelty there. What this adds, modestly: a
**controlled decomposition** on one domain — identical questions, identical fact blocks —
that separates store-value from composer-value with computed ground truth and powered
cells; a five-size measurement of the **generation ≪ verification** gap for exact
structure; and a documented case of pilot-scale depth-decay (N=24) evaporating at N=100,
which we suspect is a common unexamined failure in small-scale LLM evaluation.

## 7. Threats to validity

- **One domain, heavily memorized.** `issubclass` over the stdlib is training-set
  material; the 14b's depth-flatness may reflect memorized *composed* facts rather than
  composition ability. A rare-knowledge domain (WordNet hypernymy) might show real decay —
  but the rag-tracks-deduce result would likely persist, and it, not the decay, carries
  the reframe. Any successor domain must first demonstrate powered depth-decay at the
  primary model (the requirement this domain failed, discoverable only at N=100).
- **One model family.** The sub-7b truth-value bias and the cliff may be qwen2.5-specific.
- **Oracle retrieval.** The rag condition presents exactly the relevant edges plus
  distractors; real retrievers miss links, and a missed edge breaks a chain. Phase 1
  bounds what composition costs, not what retrieval costs.
- **Forced-choice elicitation.** Answer-format effects are real (0.26 → 0.96 across the
  witness-cut probes); we mitigated with randomized letters and a pre-registered primary
  phrasing, but did not exhaust the elicitation space, particularly for extraction.
- **Validity-checklist item 5 (≥3 sizes) was waived in writing for Phase 1** — it guards
  H2, which extraction already blocked; no third competent in-family size exists.

## 8. Discipline record (why the negatives are trustworthy)

Every phase pre-committed metrics and kill bars before running. Four kill bars fired and
stayed: M5.1 (self-signal calibration over-abstains, 0.62), M5.2 (contested-detection
collapses on held-out data, 0.17 — conclusion: contestedness requires external source
disagreement, not introspection), Phase 0.2 (extraction DEAD, surviving an instrument
fix), Phase 1 (H1 falsified). Two MIXED verdicts stopped runs that would otherwise have
crept forward. The predecessor project (Tilda) died of unfalsifiable accumulation; this
one killed its own core hypothesis with a pre-registered bar at proper power — which is
the outcome the discipline was built for. The earlier M1–M6 milestone suite is retained
in the history as infrastructure validation, with an explicit retraction of its
"thesis validated" claim (`RESULTS.md`): its gold sets were self-authored and it ran no
parametric baseline.

## 9. What would change our mind

- A domain with **demonstrated powered depth-decay at 14b+** where deduce's gap over the
  monolith *grows* — H1 would revive there (the shape exists at 7b even here).
- A retrieval stack whose miss rate at depth makes rag decay while deduce (over the same
  imperfect store) does not — that would restore a composer role the oracle-retrieval
  design excluded.
- An extraction elicitation that clears 0.70/0.80 on exact edges at any small size —
  that would reopen H2 as originally stated.
