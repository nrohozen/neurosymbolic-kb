"""Source reconciliation for the open / contested-knowledge domain (domain 5).

The system no longer emits a single TRUE/FALSE. It ingests claims from multiple SOURCES
(each a `Triple` carrying `Provenance(method="source", detail=<source id>)`, reusing L5) and
partitions them into AGREED (jointly consistent) and CONTESTED (jointly inconsistent). For
each contested cluster it KEEPS every conflicting position with its source -- it represents
the disagreement rather than resolving it (the anti-Tilda-graveyard).

The neurosymbolic part: `reconcile` finds **latent** conflicts -- a set of claims that is
jointly UNSAT though no two of them conflict (e.g. a 3-source cycle) -- which the pairwise
`surface_conflicts` baseline misses. Localization is a deletion-based **MUS** (minimal
unsatisfiable subset), reusing only `engine.is_consistent` (the frozen core is untouched).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence, Tuple, TYPE_CHECKING

from src.knowledge_graph import Provenance, Triple

if TYPE_CHECKING:
    from src.inference_engine import InferenceEngine


def sourced(s: str, r: str, o: str, source: str) -> Triple:
    """A claim tagged with the source that asserted it (provenance, L5)."""
    return Triple(s, r, o, provenance=Provenance("source", source))


def _source_of(t: Triple) -> str:
    return t.provenance.detail if t.provenance else ""


@dataclass
class ContestedCluster:
    positions: List[Triple]   # the conflicting claims, each with its source (kept, not resolved)
    kind: str                 # "surface" (a pair already conflicts) | "latent" (only jointly)

    @property
    def sources(self) -> set:
        return {_source_of(t) for t in self.positions}


@dataclass
class Reconciliation:
    agreed: List[Triple] = field(default_factory=list)
    contested: List[ContestedCluster] = field(default_factory=list)


def _consistent(engine: "InferenceEngine", claims: Sequence[Triple]) -> bool:
    return engine.is_consistent([t.as_atom() for t in claims])


def _has_pairwise_conflict(engine: "InferenceEngine", claims: Sequence[Triple]) -> bool:
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            if not _consistent(engine, [claims[i], claims[j]]):
                return True
    return False


def mus(engine: "InferenceEngine", claims: Sequence[Triple]) -> List[Triple]:
    """Deletion-based minimal unsatisfiable subset of `claims` (which must be UNSAT): drop any
    claim whose removal leaves the set still inconsistent; what remains is minimal."""
    sub = list(claims)
    for c in list(sub):
        trial = [x for x in sub if x is not c]
        if not _consistent(engine, trial):
            sub = trial
    return sub


def all_conflicts(engine: "InferenceEngine", claims: Sequence[Triple]) -> List[List[Triple]]:
    """Localize every conflict as a MUS. After finding one, drop a single member to break it
    and continue, so independent conflicts are all surfaced (order-dependent which member)."""
    conflicts: List[List[Triple]] = []
    remaining = list(claims)
    while not _consistent(engine, remaining):
        m = mus(engine, remaining)
        conflicts.append(m)
        remaining = [x for x in remaining if x is not m[0]]
    return conflicts


def surface_conflicts(engine: "InferenceEngine", claims: Sequence[Triple]) -> List[Tuple[Triple, Triple]]:
    """The naive pairwise baseline: conflicting PAIRS only. Misses latent (3+) conflicts."""
    claims = list(claims)
    pairs = []
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            if not _consistent(engine, [claims[i], claims[j]]):
                pairs.append((claims[i], claims[j]))
    return pairs


def reconcile(engine: "InferenceEngine", claims: Sequence[Triple]) -> Reconciliation:
    """Partition sourced claims into AGREED + CONTESTED clusters (positions kept, not resolved)."""
    claims = list(claims)
    if _consistent(engine, claims):
        return Reconciliation(agreed=claims, contested=[])

    clusters: List[ContestedCluster] = []
    contested_ids: set = set()
    for m in all_conflicts(engine, claims):
        kind = "surface" if _has_pairwise_conflict(engine, m) else "latent"
        clusters.append(ContestedCluster(positions=list(m), kind=kind))
        contested_ids.update(id(c) for c in m)

    agreed = [c for c in claims if id(c) not in contested_ids]
    return Reconciliation(agreed=agreed, contested=clusters)
