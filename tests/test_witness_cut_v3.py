"""Offline tests for v3 ground truth (the obscure-but-real edges) + elicitation. No network."""
from experiments.witness_cut_v3 import elicit_stable, ground_truth


def test_ground_truth_has_the_obscure_true_edges():
    t = ground_truth()
    # the surprising-but-true ones a 7B should waver on:
    assert ("int", "rational") in t       # int IS a numbers.Rational (registration)
    assert ("real", "complex") in t       # numbers.Real IS a subclass of numbers.Complex
    assert ("bool", "number") in t        # bool < int < ... < Number
    assert ("list", "iterable") in t      # list registered under Iterable
    # ...and the false ones:
    assert ("float", "rational") not in t  # float is Real, NOT Rational
    assert ("int", "iterable") not in t    # int is not iterable
    assert ("number", "int") not in t      # direction


def test_elicit_unanimous_assigns_full_stability():
    def t(url, payload):
        return {"message": {"content": "A"}}
    elicited = elicit_stable(t, k=3)
    assert elicited and all(stab == 1.0 for _, stab in elicited)
