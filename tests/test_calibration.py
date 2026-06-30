"""Truth-table tests for the calibrated adjudicator. Pure, deterministic — no clingo, no
network (signals are supplied directly)."""
from src.calibration import Signals, adjudicate


def test_deduction_overrides_and_is_never_abstained():
    # the safety property: a deductively-decidable claim is committed, ignoring signals
    assert adjudicate(True, None).status == "deduced"
    assert adjudicate(True, None).verdict is True
    assert adjudicate(False, Signals([0.9], 0.9)).verdict is False  # signals would say contested


def test_confident_agreeing_consistent_signals_commit():
    sig = Signals(model_scores=[0.9, 0.85], neg_score=0.1)  # agree, decisive, neg-consistent
    a = adjudicate(None, sig)
    assert a.status == "committed" and a.verdict is True

    sig_false = Signals(model_scores=[0.1, 0.15], neg_score=0.9)
    a2 = adjudicate(None, sig_false)
    assert a2.status == "committed" and a2.verdict is False


def test_scores_near_half_are_contested():
    a = adjudicate(None, Signals(model_scores=[0.55, 0.45], neg_score=0.5))
    assert a.status == "contested" and a.verdict is None


def test_ensemble_disagreement_is_contested():
    # one model says true, the other false -> no direction agreement
    a = adjudicate(None, Signals(model_scores=[0.85, 0.2], neg_score=0.2))
    assert a.status == "contested"


def test_negation_inconsistency_is_contested():
    # confident the claim is true AND confident its negation is true -> doesn't really know
    a = adjudicate(None, Signals(model_scores=[0.9, 0.88], neg_score=0.9))
    assert a.status == "contested"


def test_no_signal_is_unknown():
    assert adjudicate(None, None).status == "unknown"
    assert adjudicate(None, Signals(model_scores=[])).status == "unknown"
