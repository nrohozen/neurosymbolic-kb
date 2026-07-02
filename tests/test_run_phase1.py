"""Offline tests for the Phase 1 harness: fact blocks, the deduce condition (real clingo,
no network), prompts, Wilson intervals, verdict rules, and persist/resume."""
import pytest

from experiments.class_graph import class_graph, generate_questions
from experiments.run_phase1 import (
    BUCKETS, DEDUCE_CEILING, FACTS_PER_QUESTION, accuracy_table, cost_table, deduce_answer,
    fact_set, rag_prompt, relevant_edges, run, verdict_h1, wilson,
)


def _sample_questions(n_per_bucket=3, seed=1):
    return generate_questions(n_per_bucket=n_per_bucket, seed=seed, buckets=BUCKETS)


# ---------- fact blocks ----------

def test_fact_set_contains_full_chain_for_true_questions():
    g = class_graph()
    for q in _sample_questions():
        facts = set(fact_set(q))
        if q.label:  # walk any shortest chain; every hop must be present
            assert (q.a, q.b) in g.true_pairs
            rel = set(relevant_edges(q))
            assert rel <= facts


def test_fact_set_is_padded_true_and_deterministic():
    g = class_graph()
    for q in _sample_questions(n_per_bucket=2):
        f1, f2 = fact_set(q), fact_set(q)
        assert f1 == f2                                   # deterministic per question
        assert len(f1) >= min(FACTS_PER_QUESTION, len(f1))
        for x, y in f1:                                   # distractors are TRUE edges only
            assert y in g.edges[x]


# ---------- the deduce condition (the ceiling) ----------

def test_deduce_is_perfect_on_the_sample():
    # true chains entailed; reversed and unrelated not entailed — deduce == ground truth
    for q in _sample_questions():
        assert deduce_answer(q, fact_set(q)) == q.label


# ---------- prompts ----------

def test_rag_prompt_contains_facts_and_randomized_letter():
    qs = _sample_questions()
    letters = set()
    for q in qs:
        prompt, letter_true = rag_prompt(q, fact_set(q))
        assert f"{letter_true}) True" in prompt
        assert "ONLY these facts" in prompt
        assert "->" in prompt
        letters.add(letter_true)
    assert letters == {"A", "B"}


# ---------- scoring ----------

def test_wilson_interval_sanity():
    lo, hi = wilson(0.5, 100)
    assert 0.39 < lo < 0.41 and 0.59 < hi < 0.61
    assert wilson(1.0, 0) == (0.0, 1.0)


def test_run_persists_resumes_and_records_cost(tmp_path):
    out = tmp_path / "answers.jsonl"
    qs = _sample_questions(n_per_bucket=2)

    def stub(url, payload):
        return {"message": {"content": "A"}, "prompt_eval_count": 40,
                "eval_count": 2, "total_duration": 5_000_000}

    rows = run(qs, ["m1"], ["deduce", "monolith"], transport=stub, out_path=out)
    n_expected = 2 * len(qs)                    # deduce + monolith
    assert len(rows) == n_expected

    calls = []

    def counting(url, payload):
        calls.append(1)
        return stub(url, payload)

    rows2 = run(qs, ["m1"], ["deduce", "monolith"], transport=counting, out_path=out)
    assert calls == []                          # fully cached
    assert len(rows2) == n_expected
    costs = cost_table(rows2)
    assert costs[("m1", "monolith")]["mean_prompt_tokens"] == 40
    assert costs[("deduce", "deduce")]["total_seconds"] == 0


# ---------- pre-registered verdict ----------

def _acc(ded, mono, rag=None, primary="p"):
    table = {}
    for b, v in zip(BUCKETS, ded):
        table[("deduce", "deduce", b)] = (v, 100)
    for b, v in zip(BUCKETS, mono):
        table[(primary, "monolith", b)] = (v, 100)
    if rag:
        for b, v in zip(BUCKETS, rag):
            table[(primary, "rag", b)] = (v, 100)
    return table


def test_verdict_supported():
    v, _ = verdict_h1(_acc([1.0, 1.0, 1.0, 0.99], [0.88, 0.80, 0.75, 0.70]), primary="p")
    assert v == "H1_SUPPORTED"


def test_verdict_falsified_when_monolith_is_flat():
    v, _ = verdict_h1(_acc([1.0, 1.0, 1.0, 1.0], [0.90, 0.90, 0.89, 0.89]), primary="p")
    assert v == "H1_FALSIFIED"


def test_verdict_invalid_when_deduce_misses_chains():
    v, _ = verdict_h1(_acc([1.0, 0.9, 0.8, 0.7], [0.9, 0.8, 0.7, 0.6]), primary="p")
    assert v == "INVALID"
    assert DEDUCE_CEILING == 0.95


def test_verdict_flags_rag_tracking_deduce():
    v, notes = verdict_h1(
        _acc([1.0, 1.0, 1.0, 1.0], [0.88, 0.80, 0.75, 0.70], rag=[0.98, 0.97, 0.97, 0.97]),
        primary="p")
    assert v == "H1_SUPPORTED"
    assert any("tracks deduce" in n for n in notes)


def test_verdict_incomplete():
    assert verdict_h1({}, primary="p")[0] == "INCOMPLETE"
