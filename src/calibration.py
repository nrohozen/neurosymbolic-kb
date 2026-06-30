"""Calibrated abstention for the weak oracle (domain 4): TRUE / FALSE / CONTESTED.

The anti-Tilda-graveyard guard. Deduction runs first and OVERRIDES -- we never abstain on
what we can prove. Otherwise the weak oracle commits only when two decorrelated calibration
signals agree, and abstains (CONTESTED) otherwise:

- **ensemble agreement (self-consistency):** the decorrelated judge families agree on
  direction AND the mean score is decisive (far from 0.5).
- **negation consistency (the NLI/entailment probe):** a calibrated model gives
  P(claim) + P(not claim) ~= 1; confident-on-both or unsure-on-both means it doesn't know.

`adjudicate` is a PURE function of (deductive verdict, signals) -- no LLM call, no network,
fully unit-testable -- so the decision logic is deterministic and the live judge only
supplies the numbers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass
class Signals:
    model_scores: Sequence[float]      # per-model P(claim is true) from the judge ensemble
    neg_score: Optional[float] = None  # ensemble P(the negation is true)


@dataclass
class Adjudication:
    verdict: Optional[bool]   # True / False / None (contested or unknown)
    status: str               # "deduced" | "committed" | "contested" | "unknown"
    detail: str = ""


def adjudicate(
    deductive: Optional[bool],
    signals: Optional[Signals],
    *,
    decisive: float = 0.30,
    neg_tol: float = 0.40,
) -> Adjudication:
    """Combine a deductive verdict (or None) with weak-oracle signals into a calibrated
    three-way verdict. `decisive`: required |score - 0.5| to commit. `neg_tol`: tolerance on
    |P(claim) + P(neg) - 1| for negation consistency."""
    if deductive is not None:
        return Adjudication(deductive, "deduced", "deductive closure")
    if signals is None or not signals.model_scores:
        return Adjudication(None, "unknown", "no oracle signal")

    scores = list(signals.model_scores)
    mean = sum(scores) / len(scores)
    direction_agree = all(x >= 0.5 for x in scores) or all(x < 0.5 for x in scores)
    decisive_ok = abs(mean - 0.5) >= decisive
    neg_ok = signals.neg_score is None or abs(mean + signals.neg_score - 1.0) <= neg_tol

    if direction_agree and decisive_ok and neg_ok:
        return Adjudication(mean >= 0.5, "committed", f"score={mean:.2f}")
    return Adjudication(
        None, "contested",
        f"score={mean:.2f} agree={direction_agree} decisive={decisive_ok} neg_ok={neg_ok}",
    )
