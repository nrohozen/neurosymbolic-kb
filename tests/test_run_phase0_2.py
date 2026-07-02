"""Offline tests for the Phase 0.2 extraction pilot: nominal-edge gold, the name parser,
scoring, verdict rules, and the runner's persist/resume — all with stub transports."""
import pytest

from experiments.class_graph import class_graph
from experiments.run_phase0_2 import (
    RECALL_FLOOR, TRUTH_PRECISION_FLOOR, alias_map, eligible_classes, extract_names,
    run, stats_by_model, verdict_extraction,
)


# ---------- nominal edges (the extraction gold) ----------

def test_nominal_edges_exclude_virtual_completion():
    g = class_graph()
    assert g.nominal_edges["bool"] == frozenset({"int"})
    assert g.nominal_edges["int"] == frozenset({"object"})
    assert "numbers.Integral" in g.edges["int"]           # virtual edge present in the graph
    assert "numbers.Integral" not in g.nominal_edges["int"]  # but not in __bases__ gold


def test_eligible_classes_have_unambiguous_gold():
    g = class_graph()
    pool = eligible_classes()
    assert "object" not in pool                 # no bases at all
    assert "io.BytesIO" not in pool             # real bases are private _io classes
    assert all(g.nominal_edges[n] for n in pool)
    assert len(pool) > 100                      # still a large sample pool


# ---------- alias map + parser ----------

def test_alias_map_bare_names_resolve_unambiguously():
    amap = alias_map()
    assert amap["Integral"] == "numbers.Integral"
    assert amap["set"] == "set"                        # builtin, case-sensitive...
    assert amap["Set"] == "collections.abc.Set"        # ...distinct from the ABC


def test_extract_names_qualified_not_double_counted():
    assert extract_names("collections.abc.Sequence", exclude="x") == ["collections.abc.Sequence"]


def test_extract_names_mixed_list_and_exclusion():
    text = "The bases are int and numbers.Rational (see bool.__bases__)."
    assert extract_names(text, exclude="bool") == ["int", "numbers.Rational"]


def test_extract_names_ignores_unknown_and_substrings():
    assert extract_names("MyCustomClass, printer, integer", exclude="x") == []


def test_extract_names_strips_builtins_prefix():
    # the Phase 0.2 killer: correct answers spelled 'builtins.X' must score
    assert extract_names("builtins.OSError", exclude="x") == ["OSError"]
    assert extract_names("builtins. BaseException, Builtins.object", exclude="x") == [
        "BaseException", "object"]


def test_extract_names_maps_private_impl_modules():
    assert extract_names("_io.IOBase", exclude="x") == ["io.IOBase"]
    assert extract_names("_collections_abc.Iterable", exclude="x") == ["collections.abc.Iterable"]


def test_extract_names_accepts_module_ish_prefixes_not_identifiers():
    # a garbage module prefix still names the class...
    assert extract_names("unicodedata_errors.UnicodeError", exclude="x") == ["UnicodeError"]
    assert extract_names("abc.Iterable", exclude="x") == ["collections.abc.Iterable"]
    # ...but partial identifiers stay unmatched
    assert extract_names("_OSError, Iterableprotocols", exclude="x") == []


# ---------- runner (stub transport; offline) ----------

def _stub(content):
    def transport(url, payload):
        return {"message": {"content": content}}
    return transport


def test_run_persists_and_resumes(tmp_path):
    out = tmp_path / "answers.jsonl"
    classes = ["bool", "int", "float"]
    rows = run(classes, ["m1"], transport=_stub("object"), out_path=out)
    assert len(rows) == 3
    calls = []

    def counting(url, payload):
        calls.append(1)
        return {"message": {"content": "object"}}

    rows2 = run(classes, ["m1"], transport=counting, out_path=out)
    assert calls == []          # fully cached
    assert len(rows2) == 3


# ---------- scoring ----------

def test_stats_truth_precision_forgives_true_ancestors(tmp_path):
    # for bool: gold direct base = {int}. Answer "int, object": object is an ancestor
    # (entailed-true, harmless) so truth precision 1.0 while strict precision is 0.5.
    rows = run(["bool"], ["m1"], transport=_stub("int, object"), out_path=tmp_path / "a.jsonl")
    s = stats_by_model(rows)["m1"]
    assert s["direct_recall"] == 1.0
    assert s["truth_precision"] == 1.0
    assert s["strict_precision"] == pytest.approx(0.5)


def test_stats_false_edge_hurts_truth_precision(tmp_path):
    # "str" is NOT an ancestor of bool -> a genuinely corrupting edge
    rows = run(["bool"], ["m1"], transport=_stub("int, str"), out_path=tmp_path / "a.jsonl")
    s = stats_by_model(rows)["m1"]
    assert s["truth_precision"] == pytest.approx(0.5)


# ---------- pre-registered verdict ----------

def _stats(**by_model):
    return {
        m: {"direct_recall": r, "truth_precision": p, "strict_precision": p, "n_matched": 10}
        for m, (r, p) in by_model.items()
    }


LADDER5 = ("s0", "s1", "s3", "s7", "s14")


def test_verdict_go_full_when_sub7b_extracts():
    stats = _stats(s0=(0.2, 0.5), s1=(0.5, 0.7), s3=(0.75, 0.85), s7=(0.9, 0.95), s14=(0.95, 0.97))
    v, notes = verdict_extraction(stats, LADDER5)
    assert v == "GO_FULL"
    assert any("s3" in n and "anchor" in n for n in notes)


def test_verdict_h1_only_when_only_big_extracts():
    stats = _stats(s0=(0.2, 0.5), s1=(0.4, 0.6), s3=(0.6, 0.75), s7=(0.85, 0.9), s14=(0.9, 0.95))
    assert verdict_extraction(stats, LADDER5)[0] == "GO_H1_ONLY"


def test_verdict_dead_when_nothing_extracts():
    stats = _stats(s0=(0.1, 0.3), s1=(0.2, 0.4), s3=(0.3, 0.5), s7=(0.5, 0.6), s14=(0.65, 0.75))
    assert verdict_extraction(stats, LADDER5)[0] == "DEAD"


def test_verdict_requires_both_floors():
    # high recall but corrupting edges (low truth precision) must NOT count as competent
    stats = _stats(s0=(0.9, 0.5), s1=(0.9, 0.5), s3=(0.9, 0.5), s7=(0.9, 0.9), s14=(0.95, 0.95))
    assert verdict_extraction(stats, LADDER5)[0] == "GO_H1_ONLY"
    assert RECALL_FLOOR == 0.70 and TRUTH_PRECISION_FLOOR == 0.80  # doc/code mirror


def test_verdict_incomplete():
    assert verdict_extraction(_stats(s14=(0.9, 0.9)), LADDER5)[0] == "INCOMPLETE"
