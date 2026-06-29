"""The typed triple store (non-parametric memory).

A `Triple` is `(subject, relation, object)`. `as_atom()` renders it in the canonical,
space-free form the inference engine (clingo) both consumes and prints, so input facts
and derived atoms compare as plain strings.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

_UNSAFE = re.compile(r"[^a-z0-9_]")


def normalize(term: str) -> str:
    """Map an arbitrary string to a valid ASP constant (lowercase, [a-z0-9_], leading
    letter/underscore). ASP constants must not start with a digit or uppercase letter."""
    t = term.strip().lower().replace("-", "_").replace(" ", "_")
    t = _UNSAFE.sub("_", t)
    if not t:
        return "x_empty"
    if not (t[0].isalpha() or t[0] == "_"):
        t = "x_" + t
    return t


@dataclass(frozen=True)
class Provenance:
    """L5: how a fact entered the graph. `method` is the standard data-provenance kind
    (`seed` / `extracted` / `derived`); `detail` records what admitted it — a source id
    for extraction, the rule or vote for derivation."""

    method: str  # "seed" | "extracted" | "derived"
    detail: str = ""


@dataclass(frozen=True)
class Triple:
    s: str
    r: str
    o: str
    # Provenance rides along but is NOT part of identity: a fact is the same fact
    # regardless of how it was admitted, so eq/hash (and thus dedup, set membership,
    # and the M1 atom comparisons) ignore it.
    provenance: "Provenance | None" = field(default=None, compare=False)

    def as_atom(self) -> str:
        return f"{normalize(self.r)}({normalize(self.s)},{normalize(self.o)})"

    @classmethod
    def from_seq(cls, seq) -> "Triple":
        s, r, o = seq
        return cls(s, r, o)


class KnowledgeGraph:
    """An ordered, de-duplicated set of triples."""

    def __init__(self, triples: Iterable[Triple] | None = None) -> None:
        self._triples: list[Triple] = []
        for t in triples or ():
            self.add(t)

    @classmethod
    def from_seeds(cls, path: str | Path) -> "KnowledgeGraph":
        kg = cls()
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            d = json.loads(line)
            kg.add(Triple(d["s"], d["r"], d["o"], provenance=Provenance("seed", str(path))))
        return kg

    def add(self, triple: Triple) -> bool:
        """Add a triple; return True if it was new."""
        if triple in self._triples:
            return False
        self._triples.append(triple)
        return True

    def atoms(self) -> list[str]:
        return [t.as_atom() for t in self._triples]

    @property
    def triples(self) -> list[Triple]:
        return list(self._triples)

    def __len__(self) -> int:
        return len(self._triples)

    def __iter__(self) -> Iterator[Triple]:
        return iter(self._triples)
