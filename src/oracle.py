"""The swappable ground-truth source.

The `Oracle` interface is the seam that makes moving to a new domain a *re-registration*,
not a rewrite: the inference engine, property library, and contradiction logic never name
a concrete oracle. Domain 1 registers two implementations:

- `ExecutionOracle`     - the STRONG oracle: runs reference implementations and compares
                          measured work to settle performance claims (`faster_than`).
- `JudgeEntailmentOracle` - the WEAK oracle: an LLM-as-judge ensemble for conceptual /
                          definitional claims (`has_property`) that execution cannot settle.

`OracleRouter` dispatches a `Claim` to the first oracle that `handles` it.
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


class OracleRouter:
    def __init__(self, oracles: Sequence[Oracle]) -> None:
        self._oracles = list(oracles)

    def adjudicate(self, claim: Claim) -> Verdict:
        for oracle in self._oracles:
            if oracle.handles(claim):
                return oracle.adjudicate(claim)
        return Verdict(None, "router", "no oracle handles this claim")
