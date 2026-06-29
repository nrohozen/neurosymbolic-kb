"""Canonicalization: entity linking + normalization to the schema's controlled vocabulary.

A competent base model extracts the right *meaning* in the wrong *surface form*
(`bubble_sort`!=`bubblesort`, `last_in_first_out_ordering`!=`lifo`, `sorts_in_place`!=
`in_place`). This pure, deterministic post-processor (no LLM call, no training -- L2) maps
extracted triples onto the canonical constants the schema and seeds use:

- **entity linking** (open set): exact match on a canonical key (lowercase, alphanumerics
  only) against the known entity set -- conservative, so it never falsely merges two
  distinct entities; unknown mentions fall back to the lexical-normal form.
- **controlled-vocabulary mapping** (closed sets): negation-aware keyword rules encoding
  what each property enum value *means*, plus an asymptotic-notation normalizer. A value
  that maps to nothing in the vocabulary is dropped (the triple is rejected).

It is intentionally derived from the schema's vocabulary, NOT from the eval corpus's
specific mistakes -- memorizing observed error strings would be cheating (L3). It fixes
surface forms only: structure drift (a property folded into an `is_a` object) and
hallucinated facts are out of scope and survive as errors.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from .knowledge_graph import Triple, normalize

_ALLOWED_RELATIONS = {"is_a", "has_complexity", "has_property"}
_ALNUM = re.compile(r"[^a-z0-9]")


def canonical_key(term: str) -> str:
    """Entity-linking blocking key: lowercase, alphanumerics only. Collapses separator
    and spacing variants (`bubble_sort`, `bubble sort`, `Bubblesort` -> `bubblesort`)."""
    return _ALNUM.sub("", term.lower())


# asymptotic-notation key -> canonical complexity class. Keyed by canonical_key, so it
# matches both the enum form (`o_nlogn` -> `onlogn`) and math/word forms.
_COMPLEXITY = {
    "o1": "o_1", "constant": "o_1",
    "ologn": "o_logn", "logarithmic": "o_logn",
    "on": "o_n", "linear": "o_n",
    "onlogn": "o_nlogn", "nlogn": "o_nlogn",
    "linearithmic": "o_nlogn", "loglinear": "o_nlogn", "quasilinear": "o_nlogn",
    "on2": "o_n2", "n2": "o_n2", "quadratic": "o_n2",
    "o2n": "o_2n", "2n": "o_2n", "exponential": "o_2n",
}


def map_complexity(value: str) -> Optional[str]:
    cleaned = value.replace("²", "2").replace("³", "3")  # n², n³
    return _COMPLEXITY.get(canonical_key(cleaned))


def map_property(value: str) -> Optional[str]:
    """Map a free-form property value to the schema enum, negation-aware. Returns None for
    anything outside the vocabulary -- including negations the schema can't represent
    (there is no `not_comparison_based` / `not_lifo`)."""
    v = value.strip().lower()
    k = canonical_key(v)
    neg = ("not" in v) or v.startswith("un") or ("out of" in v)
    if "place" in k:
        return "not_in_place" if neg else "in_place"
    if "stable" in k:
        return "not_stable" if neg else "stable"
    if "comparison" in k:
        return None if neg else "comparison_based"
    if "lifo" in k or "lastinfirstout" in k:
        return None if neg else "lifo"
    if "fifo" in k or "firstinfirstout" in k:
        return None if neg else "fifo"
    return None


class Canonicalizer:
    def __init__(self, known_entities: Iterable[str]) -> None:
        # canonical key -> canonical surface (the normalized known form)
        self._entities: dict[str, str] = {}
        for e in known_entities:
            self._entities[canonical_key(e)] = normalize(e)

    @classmethod
    def from_seed_triples(cls, triples: Iterable[Triple]) -> "Canonicalizer":
        """Known entities = every subject, plus the object of every `is_a` (the types).
        Complexity/property objects are values, not entities, so they are excluded."""
        known: set[str] = set()
        for t in triples:
            known.add(t.s)
            if t.r == "is_a":
                known.add(t.o)
        return cls(known)

    def link_entity(self, mention: str) -> str:
        return self._entities.get(canonical_key(mention), normalize(mention))

    def canonicalize(self, triple: Triple) -> Optional[Triple]:
        """Return the canonicalized triple, or None if it cannot be mapped onto the schema
        (unknown relation, or an unmappable closed-vocabulary value)."""
        r = normalize(triple.r)
        if r not in _ALLOWED_RELATIONS:
            return None
        s = self.link_entity(triple.s)
        if r == "is_a":
            o: Optional[str] = self.link_entity(triple.o)
        elif r == "has_complexity":
            o = map_complexity(triple.o)
        else:  # has_property
            o = map_property(triple.o)
        if o is None:
            return None
        return Triple(s, r, o, provenance=triple.provenance)
