"""Deterministic, offline tests for the oracle layer (no clingo, no network)."""
from src.knowledge_graph import Triple
from src.oracle import (
    Claim,
    ExecutionOracle,
    JudgeEntailmentOracle,
    OracleRouter,
    Verdict,
)

TOY_IMPLS = {"fast": lambda data: 1, "slow": lambda data: 999}


def _perf(s, o):
    return Claim(Triple(s, "faster_than", o), kind="performance")


def test_execution_oracle_settles_faster_than_by_measured_work():
    exo = ExecutionOracle(TOY_IMPLS, sample_size=8)
    assert exo.adjudicate(_perf("fast", "slow")).holds is True
    assert exo.adjudicate(_perf("slow", "fast")).holds is False


def test_execution_oracle_is_unknown_without_an_implementation():
    exo = ExecutionOracle(TOY_IMPLS, sample_size=8)
    assert exo.adjudicate(_perf("fast", "mystery")).holds is None


class _StubJudge:
    def __init__(self, score):
        self._score = score

    def score(self, triple):
        return self._score


def test_judge_entailment_oracle_thresholds_the_ensemble_score():
    conc = Claim(Triple("mergesort", "has_property", "stable"), kind="conceptual")
    assert JudgeEntailmentOracle(_StubJudge(0.9)).adjudicate(conc).holds is True
    assert JudgeEntailmentOracle(_StubJudge(0.1)).adjudicate(conc).holds is False
    assert JudgeEntailmentOracle(_StubJudge(None)).adjudicate(conc).holds is None


def test_router_dispatches_by_claim_kind():
    exo = ExecutionOracle(TOY_IMPLS, sample_size=8)
    judge_oracle = JudgeEntailmentOracle(_StubJudge(0.9))
    router = OracleRouter([exo, judge_oracle])

    assert router.adjudicate(_perf("fast", "slow")).source == "execution"
    conc = Claim(Triple("stack", "has_property", "lifo"), kind="conceptual")
    assert router.adjudicate(conc).source == "judge"


def test_router_returns_unknown_when_no_oracle_handles():
    router = OracleRouter([])
    v = router.adjudicate(_perf("fast", "slow"))
    assert isinstance(v, Verdict) and v.holds is None and v.source == "router"
