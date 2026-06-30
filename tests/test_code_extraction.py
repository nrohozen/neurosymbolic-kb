"""Tests for the deterministic AST fact extractor against the M3 fixture. Offline, no
clingo, no network."""
from pathlib import Path

from src.code_extraction import extract_facts, layer_of, module_name, python_files

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "eval" / "m3_fixture"


def _triples():
    return {(t.s, t.r, t.o) for t in extract_facts(python_files(ROOT, ["eval/m3_fixture"]), ROOT)}


def test_module_name_and_layer():
    assert module_name(FIXTURE / "app.py", ROOT) == "eval.m3_fixture.app"
    assert layer_of("src.oracle") == "core"
    assert layer_of("eval.run_m3") == "harness"


def test_defines_and_inheritance():
    t = _triples()
    assert ("eval.m3_fixture.app", "defines", "eval.m3_fixture.app.main") in t
    assert ("eval.m3_fixture.app", "defines", "eval.m3_fixture.app.Base") in t
    # inheritance by simple class name, so the graph chains leaf -> mid -> base
    assert ("Mid", "inherits", "Base") in t
    assert ("Leaf", "inherits", "Mid") in t


def test_calls_resolved_by_unique_name():
    t = _triples()
    assert ("eval.m3_fixture.app.main", "calls", "eval.m3_fixture.app.handle") in t
    assert ("eval.m3_fixture.app.handle", "calls", "eval.m3_fixture.app.validate") in t
    assert ("eval.m3_fixture.app.validate", "calls", "eval.m3_fixture.util.normalize") in t
    assert ("eval.m3_fixture.app.save", "calls", "eval.m3_fixture.util.write") in t
    # no spurious reverse edge
    assert ("eval.m3_fixture.app.handle", "calls", "eval.m3_fixture.app.main") not in t


def test_imports_and_layer_facts():
    t = _triples()
    assert ("eval.m3_fixture.app", "imports", "eval.m3_fixture.util") in t
    assert ("eval.m3_fixture.app", "layer", "harness") in t
