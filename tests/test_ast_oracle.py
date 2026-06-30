"""Tests for the domain-2 AstOracle (BFS reachability). Offline, no clingo, no network."""
from src.knowledge_graph import Triple
from src.oracle import AstOracle, Claim, OracleRouter

# chain a -> b -> c ; plus d -> b (so d reaches c, but c reaches nothing)
CALLS = [
    Triple("a", "calls", "b"),
    Triple("b", "calls", "c"),
    Triple("d", "calls", "b"),
    Triple("x", "defines", "y"),  # non-call triple must be ignored
]


def _reach(s, o):
    return Claim(Triple(s, "reaches", o), kind="reachability")


def test_reaches_transitively():
    o = AstOracle.from_call_triples(CALLS)
    assert o.adjudicate(_reach("a", "c")).holds is True
    assert o.adjudicate(_reach("d", "c")).holds is True
    assert o.adjudicate(_reach("a", "b")).holds is True


def test_does_not_reach():
    o = AstOracle.from_call_triples(CALLS)
    assert o.adjudicate(_reach("c", "a")).holds is False
    assert o.adjudicate(_reach("a", "d")).holds is False
    assert o.adjudicate(_reach("a", "a")).holds is False  # strict (no self-reach)


def test_router_dispatches_reachability_to_ast_oracle():
    router = OracleRouter([AstOracle.from_call_triples(CALLS)])
    v = router.adjudicate(_reach("a", "c"))
    assert v.holds is True and v.source == "ast"
