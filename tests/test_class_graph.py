"""Offline tests for the Phase 0 ground-truth graph, question generator, and runner logic.
No network: the runner is exercised through an injected stub transport."""
import json

import pytest

from experiments.class_graph import class_graph, generate_questions
from experiments.run_phase0 import (
    BUCKETS, FLAT_CEILING, accuracy_table, build_prompt, parse_prediction, run, verdict,
    verdict_v2,
)


# ---------- ground truth (computed, and internally asserted against issubclass) ----------

def test_graph_builds_and_closure_matches_issubclass():
    g = class_graph()  # raises if closure != issubclass or antisymmetry is violated
    assert len(g.names) > 100
    assert len(g.true_pairs) > 400


def test_known_depths():
    g = class_graph()
    assert g.true_pairs[("bool", "int")] == 1
    assert g.true_pairs[("bool", "numbers.Integral")] == 2      # bool -> int -> Integral (virtual)
    assert g.true_pairs[("ModuleNotFoundError", "Exception")] == 2
    assert g.true_pairs[("TabError", "BaseException")] == 4
    assert ("Exception", "ModuleNotFoundError") not in g.true_pairs  # direction matters


def test_virtual_registration_edges_are_completed_not_dropped():
    g = class_graph()
    assert g.n_virtual_edges > 0
    assert ("int", "numbers.Integral") in g.true_pairs  # virtual-only link is representable


def test_depth_range_supports_all_buckets():
    g = class_graph()
    depths = set(g.true_pairs.values())
    assert {1, 2, 3, 4}.issubset(depths)


# ---------- question generation ----------

def test_questions_balanced_and_deterministic():
    qs1 = generate_questions(n_per_bucket=12, seed=0)
    qs2 = generate_questions(n_per_bucket=12, seed=0)
    assert qs1 == qs2
    assert len(qs1) == 96
    for bucket in BUCKETS:
        in_bucket = [q for q in qs1 if q.bucket == bucket]
        assert sum(q.label for q in in_bucket) == 12
        assert sum(not q.label for q in in_bucket) == 12


def test_question_labels_match_ground_truth():
    g = class_graph()
    for q in generate_questions(n_per_bucket=12, seed=0):
        assert q.label == ((q.a, q.b) in g.true_pairs)
        if q.kind == "reversed":
            assert (q.b, q.a) in g.true_pairs      # true in the other direction
        if q.kind == "unrelated":
            assert (q.b, q.a) not in g.true_pairs  # unrelated both ways


def test_no_duplicate_questions():
    qs = generate_questions(n_per_bucket=12, seed=0)
    assert len({(q.a, q.b) for q in qs}) == len(qs)


# ---------- elicitation ----------

def test_prompt_letter_randomization_is_deterministic_and_mixed():
    qs = generate_questions(n_per_bucket=12, seed=0)
    letters = []
    for q in qs:
        p1, l1 = build_prompt(q, "code", seed=0)
        p2, l2 = build_prompt(q, "code", seed=0)
        assert (p1, l1) == (p2, l2)
        assert f"{l1}) True" in p1
        letters.append(l1)
    assert {"A", "B"} == set(letters)  # both assignments actually occur


def test_parse_prediction():
    assert parse_prediction("A", "A") is True
    assert parse_prediction("The answer is B.", "A") is False
    assert parse_prediction("no idea", "A") is None


# ---------- runner (stub transport; offline) ----------

def _stub_transport_factory(answer_letter="A"):
    calls = []

    def transport(url, payload):
        calls.append(payload)
        return {"message": {"content": answer_letter}}

    return transport, calls


def test_run_persists_and_resumes(tmp_path):
    out = tmp_path / "answers.jsonl"
    qs = generate_questions(n_per_bucket=2, seed=0)
    transport, calls = _stub_transport_factory()
    rows = run(qs, ["m1"], ["code"], transport=transport, out_path=out)
    assert len(rows) == len(qs) == len(calls)
    assert len(out.read_text(encoding="utf-8").splitlines()) == len(qs)

    transport2, calls2 = _stub_transport_factory()
    rows2 = run(qs, ["m1"], ["code"], transport=transport2, out_path=out)
    assert calls2 == []                # everything cached -> zero live calls
    assert len(rows2) == len(qs)


def test_accuracy_table_scores_against_letter_assignment(tmp_path):
    # a stub that always answers the TRUE letter -> should be 100% on true, 0% on false
    qs = generate_questions(n_per_bucket=2, seed=0)

    def oracle_transport(url, payload):
        prompt = payload["messages"][0]["content"]
        letter_true = "A" if "A) True" in prompt else "B"
        return {"message": {"content": letter_true}}

    rows = run(qs, ["m1"], ["code"], transport=oracle_transport,
               out_path=tmp_path / "a.jsonl")
    acc = accuracy_table(rows, "code")
    for bucket in BUCKETS:  # 2 true + 2 false per bucket, trues right, falses wrong
        assert acc[("m1", bucket)] == pytest.approx(0.5)


# ---------- pre-registered verdict logic ----------

def _acc(small_by_bucket, large_by_bucket):
    table = {}
    for b, v in zip(BUCKETS, small_by_bucket):
        table[("s", b)] = v
    for b, v in zip(BUCKETS, large_by_bucket):
        table[("l", b)] = v
    return table


def test_verdict_go():
    v, _ = verdict(_acc([0.80, 0.60, 0.55, 0.50], [0.95, 0.90, 0.85, 0.80]), "s", "l")
    assert v == "GO"


def test_verdict_flat():
    v, _ = verdict(_acc([0.95, 0.95, 0.92, 0.95], [0.98, 0.95, 0.95, 0.96]), "s", "l")
    assert v == "FLAT"
    assert all(x >= FLAT_CEILING for x in [0.92, 0.95, 0.96, 0.98])


def test_verdict_dead_when_large_fails_atoms():
    v, _ = verdict(_acc([0.50, 0.50, 0.50, 0.50], [0.70, 0.60, 0.55, 0.50]), "s", "l")
    assert v == "DEAD"


def test_verdict_mixed_when_no_decay():
    # gap exists but the small model does not decay with depth
    v, _ = verdict(_acc([0.60, 0.60, 0.60, 0.60], [0.95, 0.90, 0.85, 0.85]), "s", "l")
    assert v == "MIXED"


def test_verdict_incomplete_on_missing_cells():
    v, notes = verdict({("s", 1): 0.5}, "s", "l")
    assert v == "INCOMPLETE"


# ---------- Phase 0.1 verdict (anchor on the smallest atomically-competent candidate) ----------

def _acc_multi(**by_model):
    return {(m, b): v for m, vals in by_model.items() for b, v in zip(BUCKETS, vals)}


def test_verdict_v2_skips_degenerate_smallest_and_goes():
    acc = _acc_multi(
        tiny=[0.52, 0.50, 0.55, 0.50],   # below the 0.70 atomic floor -> not the anchor
        mid=[0.80, 0.65, 0.60, 0.55],    # anchor: atomically competent, decays 0.25
        large=[0.95, 0.90, 0.88, 0.85],
    )
    v, notes = verdict_v2(acc, ["tiny", "mid"], "large")
    assert v == "GO"
    assert any("anchor" in n and "mid" in n for n in notes)


def test_verdict_v2_no_floor_when_no_candidate_competent():
    acc = _acc_multi(
        tiny=[0.50, 0.50, 0.50, 0.50],
        mid=[0.60, 0.55, 0.50, 0.52],    # best candidate still under 0.70 at d=1
        large=[0.90, 0.85, 0.85, 0.80],
    )
    assert verdict_v2(acc, ["tiny", "mid"], "large")[0] == "NO_FLOOR"


def test_verdict_v2_mixed_when_anchor_does_not_decay():
    acc = _acc_multi(
        mid=[0.75, 0.72, 0.74, 0.70],    # competent but decay only 0.05
        large=[0.95, 0.92, 0.90, 0.88],
    )
    assert verdict_v2(acc, ["mid"], "large")[0] == "MIXED"


def test_verdict_v2_dead_and_flat_take_precedence():
    dead = _acc_multi(mid=[0.75, 0.60, 0.55, 0.50], large=[0.70, 0.65, 0.60, 0.55])
    assert verdict_v2(dead, ["mid"], "large")[0] == "DEAD"
    flat = _acc_multi(mid=[0.95, 0.93, 0.92, 0.91], large=[0.98, 0.97, 0.96, 0.95])
    assert verdict_v2(flat, ["mid"], "large")[0] == "FLAT"


def test_verdict_v2_incomplete_on_missing_ladder_cells():
    acc = _acc_multi(large=[0.9, 0.9, 0.9, 0.9])
    assert verdict_v2(acc, ["mid"], "large")[0] == "INCOMPLETE"
