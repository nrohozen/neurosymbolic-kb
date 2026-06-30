"""Tests for the M5.1 contested fixture + signal builder. Offline, no clingo, no network."""
from eval.contested import build_signals, load_contested, negation_claim_text
from src.knowledge_graph import Triple


def test_fixture_is_balanced_and_well_formed():
    cases = load_contested()
    by = {}
    for c in cases:
        by[c["status"]] = by.get(c["status"], 0) + 1
    assert by.get("contested", 0) >= 5
    assert by.get("settled_true", 0) >= 3
    assert by.get("settled_false", 0) >= 3


def test_negation_claim_text_negates():
    t = Triple("data_science", "subfield_of", "statistics")
    assert "NOT" in negation_claim_text(t)


class _StubJudge:
    def __init__(self, per_model, mean):
        self._per_model = per_model
        self._mean = mean

    def scores(self, triple):
        return list(self._per_model)

    def score(self, triple):
        return self._mean


def test_build_signals_pulls_from_both_judges():
    t = Triple("x", "subfield_of", "y")
    sig = build_signals(t, _StubJudge([0.9, 0.8], 0.85), _StubJudge([0.1, 0.2], 0.15))
    assert sig.model_scores == [0.9, 0.8]
    assert sig.neg_score == 0.15
