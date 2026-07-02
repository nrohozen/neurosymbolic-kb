"""Ground-truth class graph + question generator for the hypothesis test (Phase 0+).

The domain (HYPOTHESIS_TEST.md section 4): Python `issubclass` over a fixed stdlib
inventory (builtin exceptions + core value/container types + `numbers` + `collections.abc`
+ `io`). Ground truth is COMPUTED, not authored (Validity Checklist item 6): direct edges
are read from `__bases__`, plus a minimal completion for ABC virtual registrations derived
from `issubclass` itself. The transitive closure of the direct-edge graph is asserted equal
to `issubclass` over every ordered pair, so truth and hop-depth can never disagree — this
resolves section-9 open decision 6 (virtual-subclass handling): virtual covering edges are
completed into the graph, and any pair where closure and `issubclass` still disagreed would
raise, not silently mislabel.

Depth of a true pair = shortest path in the direct-edge graph — the number of hops the
monolith must compose in-head and the solver composes for free. False questions are
reversed true pairs (bucketed at the depth of their true direction — the lexical-association
control) and unrelated pairs (no relation in either direction).
"""
from __future__ import annotations

import builtins
import collections.abc
import io
import numbers
import random
import warnings
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, FrozenSet, List, Tuple

# ByteString is deprecated (3.12: issubclass against it warns, removal planned) — a hygiene
# exclusion, not a difficulty exclusion. Hashable's __subclasshook__ (duck-typing on
# __hash__) makes `object` a VIRTUAL subclass of it while Hashable nominally inherits
# object — mutual subclassing, so issubclass stops being a partial order and depth is
# undefined; excluded for well-definedness (caught by the antisymmetry assertion below).
_EXCLUDE = {"ByteString", "Hashable"}

_CORE_TYPES = (
    object, type, int, bool, float, complex, str, bytes, bytearray,
    list, tuple, dict, set, frozenset, range, memoryview,
)


def _issub(a: type, b: type) -> bool:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return issubclass(a, b)


def _display_name(cls: type) -> str:
    mod = cls.__module__
    if mod in ("builtins", None):
        return cls.__qualname__
    if mod == "_io":  # CPython implementation detail; the public module is `io`
        mod = "io"
    if mod == "_collections_abc":
        mod = "collections.abc"
    return f"{mod}.{cls.__qualname__}"


def _inventory() -> Dict[str, type]:
    """The fixed class set, enumerated programmatically (not hand-picked one by one)."""
    out: Dict[str, type] = {}
    seen_ids: set = set()

    def add(cls: type) -> None:
        if id(cls) in seen_ids:  # alias dedup: IOError is OSError
            return
        if cls.__qualname__ in _EXCLUDE:
            return
        seen_ids.add(id(cls))
        out[_display_name(cls)] = cls

    for obj in vars(builtins).values():
        if isinstance(obj, type) and _issub(obj, BaseException):
            add(obj)
    for cls in _CORE_TYPES:
        add(cls)
    for mod in (numbers, collections.abc, io):
        for name, obj in vars(mod).items():
            if name.startswith("_") or not isinstance(obj, type):
                continue
            add(obj)
    return out


@dataclass(frozen=True)
class ClassGraph:
    names: Tuple[str, ...]
    edges: Dict[str, FrozenSet[str]]              # direct edges: subclass -> base (incl. virtual)
    nominal_edges: Dict[str, FrozenSet[str]]      # __bases__ only — the unambiguous extraction gold
    true_pairs: Dict[Tuple[str, str], int]        # (sub, super) -> shortest-path depth
    n_virtual_edges: int                          # completion edges added for ABC registration


def _bfs_depths(edges: Dict[str, FrozenSet[str]], start: str) -> Dict[str, int]:
    depths = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in edges[node]:
            if nxt not in depths:
                depths[nxt] = depths[node] + 1
                queue.append(nxt)
    return depths


@lru_cache(maxsize=1)
def class_graph() -> ClassGraph:
    inv = _inventory()
    names = sorted(inv)
    by_id = {id(cls): name for name, cls in inv.items()}

    # antisymmetry sanity: distinct entries must never be mutual subclasses
    truth = {(a, b) for a in names for b in names if a != b and _issub(inv[a], inv[b])}
    for a, b in truth:
        if (b, a) in truth:
            raise AssertionError(f"mutual subclass between distinct classes: {a} / {b}")

    nominal: Dict[str, set] = {n: set() for n in names}
    for name, cls in inv.items():
        for base in cls.__bases__:
            bname = by_id.get(id(base))
            if bname is not None:
                nominal[name].add(bname)
    edges: Dict[str, set] = {n: set(e) for n, e in nominal.items()}

    # minimal completion: a virtual (ABC-registered) covering pair gets a direct edge iff
    # no inventory class sits strictly between it — computed from issubclass, not authored.
    n_virtual = 0
    for a, b in truth:
        if b in edges[a]:
            continue
        covered = any(
            c != a and c != b and _issub(inv[a], inv[c]) and _issub(inv[c], inv[b])
            for c in names
        )
        if not covered:
            edges[a].add(b)
            n_virtual += 1

    frozen = {n: frozenset(e) for n, e in edges.items()}
    true_pairs: Dict[Tuple[str, str], int] = {}
    for a in names:
        for b, d in _bfs_depths(frozen, a).items():
            if d > 0:
                true_pairs[(a, b)] = d

    # the load-bearing assertion: closure == issubclass, so depth and truth cannot diverge
    if set(true_pairs) != truth:
        missing = truth - set(true_pairs)
        extra = set(true_pairs) - truth
        raise AssertionError(
            f"closure/issubclass mismatch: missing={sorted(missing)[:5]} extra={sorted(extra)[:5]}"
        )

    return ClassGraph(
        names=tuple(names),
        edges=frozen,
        nominal_edges={n: frozenset(e) for n, e in nominal.items()},
        true_pairs=true_pairs,
        n_virtual_edges=n_virtual,
    )


@dataclass(frozen=True)
class Question:
    a: str        # subject (display name)
    b: str        # object
    label: bool   # ground truth of "a is a subclass of b"
    bucket: int   # depth bucket (the last bucket pools deeper chains, e.g. 4 = "4+")
    kind: str     # "chain" (true) | "reversed" (false control) | "unrelated" (false)


def generate_questions(
    n_per_bucket: int = 12, seed: int = 0, buckets: Tuple[int, ...] = (1, 2, 3, 4)
) -> List[Question]:
    """A balanced, deterministic question set: per depth bucket, `n_per_bucket` true pairs
    and `n_per_bucket` false ones (half reversed true pairs, half unrelated)."""
    g = class_graph()
    rnd = random.Random(seed)
    max_bucket = buckets[-1]

    pools: Dict[int, List[Tuple[str, str]]] = {b: [] for b in buckets}
    for (a, b), d in sorted(g.true_pairs.items()):
        bucket = min(d, max_bucket)
        if bucket in pools:
            pools[bucket].append((a, b))

    related = set(g.true_pairs) | {(b, a) for (a, b) in g.true_pairs}
    unrelated_pool = sorted(
        (a, b) for a in g.names for b in g.names if a != b and (a, b) not in related
    )

    questions: List[Question] = []
    n_rev = n_per_bucket - n_per_bucket // 2
    n_unrel = n_per_bucket // 2
    for bucket in buckets:
        pool = pools[bucket]
        if len(pool) < n_per_bucket:
            raise ValueError(f"bucket {bucket}: only {len(pool)} true pairs, need {n_per_bucket}")
        chosen = rnd.sample(pool, n_per_bucket)
        for a, b in chosen:
            questions.append(Question(a, b, True, bucket, "chain"))
        for a, b in rnd.sample(chosen, n_rev):
            questions.append(Question(b, a, False, bucket, "reversed"))
        for a, b in rnd.sample(unrelated_pool, n_unrel):
            questions.append(Question(a, b, False, bucket, "unrelated"))
    return questions
