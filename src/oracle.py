"""The swappable ground-truth source.

The `Oracle` interface is the seam that makes moving to a new domain a *re-registration*,
not a rewrite: the inference engine, property library, and contradiction logic never name
a concrete oracle. Domain 1 registers two implementations:

- `ExecutionOracle`     - domain 1 STRONG oracle: runs reference implementations and
                          compares measured work to settle performance claims (`faster_than`).
- `JudgeEntailmentOracle` - domain 1 WEAK oracle: an LLM-as-judge ensemble for conceptual /
                          definitional claims (`has_property`) that execution cannot settle.
- `AstOracle`           - domain 2 STRONG oracle: settles `reaches(A, B)` by independent BFS
                          over the AST call graph (cross-checks the engine's closure).

`OracleRouter` dispatches a `Claim` to the first oracle that `handles` it. Adding a new
oracle here is the intended way to bring up a new domain (the engine stays untouched).
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Mapping, Sequence

if TYPE_CHECKING:
    from .knowledge_graph import Triple


@dataclass
class Claim:
    triple: "Triple"
    kind: str  # "performance" | "conceptual"


@dataclass
class Verdict:
    holds: bool | None  # True / False / None (unknown)
    source: str
    detail: str = ""


class Oracle(ABC):
    @abstractmethod
    def handles(self, claim: Claim) -> bool: ...

    @abstractmethod
    def adjudicate(self, claim: Claim) -> Verdict: ...


class ExecutionOracle(Oracle):
    """Settles `faster_than(A, B)` by running A and B and comparing measured work."""

    def __init__(
        self,
        implementations: Mapping[str, Callable[[Sequence[int]], int]],
        sample_size: int = 512,
        seed: int = 0,
    ) -> None:
        self._impl = dict(implementations)
        self._n = sample_size
        self._seed = seed

    def handles(self, claim: Claim) -> bool:
        return claim.kind == "performance" and claim.triple.r == "faster_than"

    def adjudicate(self, claim: Claim) -> Verdict:
        a, b = claim.triple.s, claim.triple.o
        if a not in self._impl or b not in self._impl:
            return Verdict(None, "execution", f"no reference implementation for {a!r} or {b!r}")
        rnd = random.Random(self._seed)
        data = [rnd.randint(0, 1_000_000) for _ in range(self._n)]
        ops_a = self._impl[a](list(data))
        ops_b = self._impl[b](list(data))
        return Verdict(ops_a < ops_b, "execution", f"{a}={ops_a} ops vs {b}={ops_b} ops @ n={self._n}")


class JudgeEntailmentOracle(Oracle):
    """Settles conceptual claims via an injected judge with a `.score(triple) -> float|None`."""

    def __init__(self, judge, threshold: float = 0.5) -> None:
        self._judge = judge
        self._threshold = threshold

    def handles(self, claim: Claim) -> bool:
        return claim.kind == "conceptual"

    def adjudicate(self, claim: Claim) -> Verdict:
        score = self._judge.score(claim.triple)
        if score is None:
            return Verdict(None, "judge", "judge unavailable")
        return Verdict(score >= self._threshold, "judge", f"ensemble score {score:.2f}")


class AstOracle(Oracle):
    """Settles `reaches(A, B)` by independent breadth-first search over the AST call graph.
    Deterministic and decoupled from the engine's transitive-closure rule, so agreement
    between the two is a genuine cross-check (as execution cross-checked deduction in
    domain 1)."""

    def __init__(self, call_edges: Mapping[str, Sequence[str]]) -> None:
        self._edges: dict[str, set[str]] = {k: set(v) for k, v in call_edges.items()}

    @classmethod
    def from_call_triples(cls, triples) -> "AstOracle":
        edges: dict[str, set[str]] = {}
        for t in triples:
            if t.r == "calls":
                edges.setdefault(t.s, set()).add(t.o)
        return cls(edges)

    def handles(self, claim: Claim) -> bool:
        return claim.kind == "reachability" and claim.triple.r == "reaches"

    def adjudicate(self, claim: Claim) -> Verdict:
        start, target = claim.triple.s, claim.triple.o
        seen: set[str] = set()
        stack = [start]
        while stack:
            node = stack.pop()
            for nxt in self._edges.get(node, ()):  # strict reachability: >= 1 edge
                if nxt == target:
                    return Verdict(True, "ast", f"{start} reaches {target}")
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return Verdict(False, "ast", f"{start} does not reach {target}")


class OracleRouter:
    def __init__(self, oracles: Sequence[Oracle]) -> None:
        self._oracles = list(oracles)

    def adjudicate(self, claim: Claim) -> Verdict:
        for oracle in self._oracles:
            if oracle.handles(claim):
                return oracle.adjudicate(claim)
        return Verdict(None, "router", "no oracle handles this claim")
