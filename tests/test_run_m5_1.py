"""Tests for the M5.1 scoring (`evaluate`). Pure — no clingo, no network (synthetic rows)."""
from eval.run_m5_1 import evaluate


def _row(status, gold, adj_status, adj_verdict, judge_mean):
    return {"status": status, "gold": gold, "adj_status": adj_status,
            "adj_verdict": adj_verdict, "judge_mean": judge_mean}


def test_skip_when_no_judge_signal():
    rows = [_row("contested", None, "unknown", None, None),
            _row("settled_true", True, "unknown", None, None)]
    assert evaluate(rows).available is False


def test_ideal_calibration_scores_perfectly():
    rows = [
        _row("contested", None, "contested", None, 0.55),
        _row("contested", None, "contested", None, 0.50),
        _row("settled_true", True, "committed", True, 0.9),
        _row("settled_false", False, "committed", False, 0.1),
    ]
    s = evaluate(rows)
    assert s.available
    assert s.contested_recall == 1.0          # both contested abstained
    assert s.settled_over_abstention == 0.0   # neither settled abstained
    assert s.committed_acc == 1.0
    assert s.judge_alone_acc == 1.0
    assert s.lift == 0.0


def test_abstaining_on_a_hard_settled_claim_lifts_committed_accuracy():
    # judge gets the second settled claim wrong; calibration abstains on it -> committed acc up
    rows = [
        _row("settled_true", True, "committed", True, 0.9),      # judge right, committed
        _row("settled_false", False, "contested", None, 0.7),    # judge WRONG (0.7->True), abstained
    ]
    s = evaluate(rows)
    assert s.judge_alone_acc == 0.5     # judge forced: 1 right of 2
    assert s.committed_acc == 1.0       # only the one it committed to, correct
    assert s.lift == 0.5
    assert s.settled_over_abstention == 0.5
