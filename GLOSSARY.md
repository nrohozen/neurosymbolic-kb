# Glossary

The point of this file: **use the established term.** When tempted to coin a name, look here
first; if it isn't here, search the literature and add the real term — don't invent one.
A metaphor may appear in prose as a flagged one-line intuition pump, never in code or as the
canonical name.

## Canonical terms (use these)

| Concept | Use this term | Field / source to search |
|---|---|---|
| Several models scoring a candidate, agreement-gated | **LLM-as-a-judge ensemble**; **self-consistency** | LLM evaluation; Wang et al. |
| A high-confidence starting fact / anchor | **seed fact / axiom / ground-truth assertion** | knowledge representation; weak supervision |
| Propagating one fact into many via relation structure | **forward chaining**; **transitive / deductive closure** | logic programming; relational algebra |
| Declaring a relation transitive/symmetric/inverse/functional | **OWL property characteristics** | ontologies; description logic |
| Detect contradiction, localize cause, retract | **truth maintenance system (TMS/ATMS)** | classical AI; de Kleer, Doyle |
| Update beliefs consistently under new, conflicting info | **belief revision (AGM)** | formal epistemology |
| LLM turning text into structured facts | **relation extraction / OpenIE / LLM-based KG construction** | NLP; knowledge graphs |
| External, editable fact store | **non-parametric memory / knowledge graph / RAG** | retrieval; KR |
| Revisiting uncertain items offline | **replay buffer + offline re-evaluation** | continual learning; RL |
| Cheap, reversible, environment-shaped weight tweak | **PEFT / LoRA adapter** | parameter-efficient fine-tuning |
| Resolving a surface mention to a canonical KB entry | **entity linking / entity normalization** | NLP; knowledge graphs |
| Mapping varied surface strings to one canonical form / closed enum | **lexical normalization**; **controlled vocabulary** | NLP; ontologies |
| "Is the answer about the entity/type actually asked?" | **NLI / entailment**; faithfulness check | NLP |
| Update only on novel/surprising input | **active learning / uncertainty sampling / novelty detection** | active learning |
| Losing old skills when learning new ones | **catastrophic forgetting** | continual learning |
| Frozen base providing built-in structure | **inductive bias / prior**; frozen pretrained base | — |
| Conditional, context-dependent activation | **conditional computation / mixture-of-experts / in-context conditioning** | — |

## Established named ideas (keep using exactly — these are literature, not metaphors)

- **Genomic bottleneck** — Zador, "A Critique of Pure Learning," 2019.
- **Core knowledge** — Spelke (objects, agents, number, geometry).
- **Lottery Ticket Hypothesis** — Frankle & Carbin, 2018.
- **Knowledge distillation** — Hinton et al.
- **Skill-acquisition efficiency / ARC** — Chollet, "On the Measure of Intelligence," 2019.

## Retired Tilda jargon → replacement

`council` → judge ensemble · `senses` → tools · `cribs` → seed facts · `diagonal board` →
forward chaining / deductive closure · `the dragon` → catastrophic forgetting · `cortex`/
`hippocampus`/`genome` → PEFT adapter / non-parametric memory / frozen base · `sleep`/
`consolidation` → replay buffer + offline re-evaluation · `bone fact` → anchor/seed ·
`grounding gate` → NLI/entailment check · `faculties`/`characters`/`bands`/`elders` → name
the specific standard mechanism instead.
