"""Offline tests for v2 elicitation logic (forced-choice tally + abstention). Stub transport,
no network. The scoring math is covered by test_witness_cut."""
from experiments.witness_cut_v2 import elicit_stable, forced_choice_vote


def _transport_returning(letter):
    def t(url, payload):
        return {"message": {"content": f"{letter}"}}
    return t


def test_vote_parses_the_letter():
    assert forced_choice_vote(_transport_returning("A"), "m", "bool", "int") == "A"
    assert forced_choice_vote(_transport_returning("answer: B."), "m", "x", "y") == "B"


def test_unanimous_votes_assert_with_full_stability():
    # every sample says "A) X subclass of Y" -> assert (x, y) at stability 1.0
    elicited = elicit_stable(_transport_returning("A"), models=["m"], k=3)
    edges = dict(elicited)
    # for the pair (object, baseexception) the prompt's A is "object subclass of baseexception"
    assert all(stab == 1.0 for stab in edges.values())
    # every pair produced exactly one directed edge (its A direction)
    assert len(elicited) > 0


def test_no_majority_abstains():
    # alternate A/C so no direction reaches >50% -> nothing asserted
    flip = {"n": 0}

    def t(url, payload):
        flip["n"] += 1
        return {"message": {"content": "A" if flip["n"] % 2 else "C"}}

    elicited = elicit_stable(t, models=["m"], k=4)
    assert elicited == []
