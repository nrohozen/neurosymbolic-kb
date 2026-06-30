"""Offline tests for the witness-cut scoring + ground truth. No clingo, no network."""
from experiments.witness_cut import CutScores, evaluate, ground_truth


def test_ground_truth_is_real_issubclass():
    t = ground_truth()
    assert ("bool", "int") in t          # bool IS a subclass of int
    assert ("int", "bool") not in t      # ...but not the reverse
    assert ("int", "object") in t        # everything <= object
    assert ("int", "float") not in t     # the classic misconception: int is NOT a float
    assert ("zerodivisionerror", "exception") in t  # transitive up the chain


def test_evaluate_rewards_dropping_false_cyclic_edges():
    truth = {("bool", "int"), ("int", "object"), ("bool", "object")}
    asserted = {("bool", "int"), ("int", "object"), ("object", "int")}  # last false + cyclic
    survivors = {("bool", "int"), ("int", "object")}                     # examiner dropped it
    s = evaluate(asserted, survivors, truth)
    assert s.raw_precision == 2 / 3
    assert s.filt_precision == 1.0
    assert s.lift > 0
    assert s.good_drops == 1 and s.bad_drops == 0


def test_evaluate_penalizes_dropping_a_true_edge():
    truth = {("bool", "int"), ("int", "object")}
    asserted = {("bool", "int"), ("int", "object")}
    survivors = {("bool", "int")}  # examiner wrongly dropped a true edge
    s = evaluate(asserted, survivors, truth)
    assert s.bad_drops == 1 and s.good_drops == 0
    assert s.filt_precision == 1.0 and s.raw_precision == 1.0  # precision same, but recall fell
    assert s.filt_recall < s.raw_recall
