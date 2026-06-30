"""Tests for the M5.2 fixed negation phrasing. Offline, no network."""
from eval.contested import negation_claim_text, negation_statement_text
from src.knowledge_graph import Triple


def test_statement_form_is_a_clean_negated_statement():
    t = Triple("data_science", "subfield_of", "statistics")
    txt = negation_statement_text(t)
    assert txt.startswith("Consider the statement:")
    assert "is not a subfield of" in txt
    assert "data science" in txt and "statistics" in txt
    # the broken double-negative QUESTION form is gone from the fix
    assert "is it true that" not in txt.lower()


def test_subsumes_negation_statement():
    t = Triple("transformer", "subsumes", "rnn")
    assert "does not generalize" in negation_statement_text(t)


def test_m51_function_unchanged_for_reproducibility():
    # M5.1's phrasing must still be the old double-negative question
    t = Triple("data_science", "subfield_of", "statistics")
    assert "is it true that" in negation_claim_text(t).lower()
