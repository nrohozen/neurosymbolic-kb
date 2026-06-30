"""Active-learning / staleness policy for the temporal (domain-3) oracle.

The deductive layer catches drift in a snapshot it already has; the question this module
answers is *when to spend a query to refresh a fact* — standard term: **active learning /
uncertainty sampling**, here driven by staleness. Each key has a volatility class; a key is
due for re-query once it is older than the TTL for its volatility. Volatile keys are polled
often (catch changes), stable keys rarely (save queries) — instead of re-querying everything
every tick.

Pure and deterministic (no clock, no network): `now`/`last_queried` are caller-supplied tick
counts, so the simulation in eval/run_m4.py is reproducible.
"""
from __future__ import annotations

from typing import Dict

from src.state_extraction import observed_from_snapshot

# volatility class -> time-to-live in ticks (refresh interval)
TTL: Dict[str, int] = {"high": 1, "medium": 4, "low": 16}


def ttl_for(volatility: str) -> int:
    return TTL.get(volatility, TTL["medium"])


def should_requery(now: int, last_queried: int, ttl: int) -> bool:
    """Due for re-query once at least `ttl` ticks have passed since the last query."""
    return (now - last_queried) >= ttl


def changed_keys(old_snapshot: dict, new_snapshot: dict) -> set[str]:
    """Keys whose observed value differs between two snapshots (added/removed count too)."""
    a = {t.s: t.o for t in observed_from_snapshot(old_snapshot)}
    b = {t.s: t.o for t in observed_from_snapshot(new_snapshot)}
    return {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
