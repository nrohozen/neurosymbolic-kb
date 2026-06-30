"""Belief revision (AGM) by epistemic entrenchment, for the weak-oracle domain.

When a new candidate fact contradicts the accepted belief set, something must give. This is
the standard **AGM belief revision** problem; we resolve it by **epistemic entrenchment** =
confidence: keep the more-entrenched facts, retract the least-entrenched only as far as
needed to restore consistency.

It is a PURE FUNCTION over triples (no KnowledgeGraph mutation), so the frozen core stays
untouched -- it just calls the engine's UNSAT check. The engine is passed in already loaded
with whatever schema, so this module is domain-agnostic.

Two deliberate choices (both inspectable, both noted limitations):
- **Greedy, entrenchment-ordered** removal, not full TMS minimal-conflict-set localization:
  it removes lowest-confidence facts one at a time until consistent. Order-dependent in the
  same spirit as the M2-filter.
- **Incumbents win ties:** among equal-confidence facts the candidate is dropped first, so a
  new claim must strictly EXCEED an incumbent's entrenchment to displace it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Mapping, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from .inference_engine import InferenceEngine
    from .knowledge_graph import Triple

DEFAULT_CONFIDENCE = 0.5


@dataclass
class RevisionResult:
    accepted: List["Triple"] = field(default_factory=list)   # the new consistent belief set
    retracted: List["Triple"] = field(default_factory=list)  # removed (may include candidate)
    candidate_accepted: bool = False


def revise(
    engine: "InferenceEngine",
    accepted: Sequence["Triple"],
    candidate: "Triple",
    confidence: Mapping[str, float],
) -> RevisionResult:
    """Revise the consistent `accepted` set with `candidate`. Returns the new consistent set,
    what was retracted, and whether the candidate survived."""
    def conf(t: "Triple") -> float:
        return confidence.get(t.as_atom(), DEFAULT_CONFIDENCE)

    def atoms(ts: Sequence["Triple"]) -> List[str]:
        return [t.as_atom() for t in ts]

    pool = list(accepted) + [candidate]
    if engine.is_consistent(atoms(pool)):
        return RevisionResult(accepted=pool, retracted=[], candidate_accepted=True)

    # least-entrenched first; on a tie the candidate (0) sorts before incumbents (1)
    order = sorted(pool, key=lambda t: (conf(t), 0 if t is candidate else 1))
    kept = list(pool)
    retracted: List["Triple"] = []
    for t in order:
        if engine.is_consistent(atoms(kept)):
            break
        kept = [x for x in kept if x is not t]
        retracted.append(t)

    return RevisionResult(
        accepted=kept,
        retracted=retracted,
        candidate_accepted=any(x is candidate for x in kept),
    )
