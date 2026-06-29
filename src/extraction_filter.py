"""Deductive consistency filter: the solver backend vetting the LLM frontend.

A candidate triple extracted from text is *dropped* if adding it to the trusted seed
graph (plus the candidates already kept) makes the program UNSAT — i.e. it fires a
schema integrity constraint. This recovers extraction precision with ZERO LLM calls:
the same deductive immune system that catches planted contradictions in M1 also catches
the contradiction-shaped extraction errors here.

It catches only the SUBSET of errors that conflict with the schema or the trusted seeds;
a wrong-but-consistent triple (e.g. a false property on an entity the seeds never
constrain) survives. That ceiling is honest and measured by M2 metric 8.

Order dependence: candidates are vetted in arrival order against the accumulating kept
set, so when two candidates are each seed-consistent but jointly violate a constraint,
the one seen first survives. Minimal-conflict-set localization (TMS/ATMS) is later work.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from .inference_engine import InferenceEngine
    from .knowledge_graph import Triple


@dataclass
class FilterResult:
    kept: List["Triple"] = field(default_factory=list)
    dropped: List["Triple"] = field(default_factory=list)


def consistency_filter(
    engine: "InferenceEngine",
    trusted_atoms: Sequence[str],
    candidates: Iterable["Triple"],
) -> FilterResult:
    """Partition `candidates` into the ones that leave the graph satisfiable (`kept`) and
    the ones that fire an integrity constraint (`dropped`). A candidate equal to a trusted
    fact is consistent, hence kept; a within-batch exact duplicate is collapsed (judged
    once). This is an *admissibility* test, not a novelty test — deduping against an
    existing graph is `KnowledgeGraph.add`'s job, not the filter's."""
    result = FilterResult()
    kept_atoms: List[str] = []
    judged: set[str] = set()
    for triple in candidates:
        atom = triple.as_atom()
        if atom in judged:
            continue  # same extracted atom seen earlier in this batch
        judged.add(atom)
        if engine.is_consistent(list(trusted_atoms) + kept_atoms + [atom]):
            result.kept.append(triple)
            kept_atoms.append(atom)
        else:
            result.dropped.append(triple)
    return result
