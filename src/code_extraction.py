"""Deterministic relation extraction from a Python codebase via the stdlib `ast` module
(domain 2's compiler/AST oracle path -- the mature syntactic tool, not reinvented).

text(source) -> typed `Triple`s, reusing the SAME `Triple` / `normalize` as domain 1:
- `defines(module, qualname)`    - a module defines a function/method/class
- `inherits(class, base)`        - by simple class name (so the inheritance graph chains)
- `calls(caller_qual, callee_qual)` - intra-repo call, resolved by UNIQUE simple name
                                   (ambiguous/external names are skipped -- conservative)
- `imports(module, target)`      - resolved (relative imports made absolute)
- `layer(module, layer)`         - core (src/) / harness (eval/) / first path segment

This is deterministic and offline. It feeds the unchanged inference engine and the
AstOracle; the LLM extraction path is unchanged from M2 and not used here (M3 first cut).
"""
from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path
from typing import Iterable, List

from src.knowledge_graph import Triple

_LAYER = {"src": "core", "eval": "harness"}


def module_name(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    return ".".join(rel.parts)


def layer_of(module: str) -> str:
    head = module.split(".", 1)[0]
    return _LAYER.get(head, head)


def python_files(root: Path, subdirs: Iterable[str]) -> List[Path]:
    files: List[Path] = []
    for sub in subdirs:
        files.extend(sorted((root / sub).rglob("*.py")))
    return files


def _callee_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _resolve_import(module: str, node: ast.ImportFrom) -> List[str]:
    """Resolve an `from ... import ...` to absolute target module string(s)."""
    if node.level:  # relative import: climb `level` packages from this module
        base = module.split(".")[: -node.level] if node.level <= module.count(".") + 1 else []
        prefix = ".".join(base)
    else:
        prefix = ""
    if node.module:
        target = ".".join(p for p in (prefix, node.module) if p)
        return [target]
    # `from . import x, y` -> prefix.x, prefix.y
    return [".".join(p for p in (prefix, a.name) if p) for a in node.names]


def extract_facts(paths: Iterable[Path], root: Path) -> List[Triple]:
    paths = list(paths)
    facts: List[Triple] = []
    func_index: dict[str, set[str]] = defaultdict(set)  # simple name -> {qualnames}
    callers: list[tuple[str, ast.AST]] = []             # (caller qual, def node)

    # ---- pass 1: definitions, inheritance, imports, layers ----
    for path in paths:
        module = module_name(path, root)
        facts.append(Triple(module, "layer", layer_of(module)))
        tree = ast.parse(path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for target in _resolve_import(module, node):
                    facts.append(Triple(module, "imports", target))
                    facts.append(Triple(target, "layer", layer_of(target)))
            elif isinstance(node, ast.Import):
                for a in node.names:
                    facts.append(Triple(module, "imports", a.name))
                    facts.append(Triple(a.name, "layer", layer_of(a.name)))

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = f"{module}.{node.name}"
                facts.append(Triple(module, "defines", qual))
                func_index[node.name].add(qual)
                callers.append((qual, node))
            elif isinstance(node, ast.ClassDef):
                facts.append(Triple(module, "defines", f"{module}.{node.name}"))
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        facts.append(Triple(node.name, "inherits", base.id))
                    elif isinstance(base, ast.Attribute):
                        facts.append(Triple(node.name, "inherits", base.attr))
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        qual = f"{module}.{node.name}.{item.name}"
                        facts.append(Triple(module, "defines", qual))
                        func_index[item.name].add(qual)
                        callers.append((qual, item))

    # ---- pass 2: calls, resolved by UNIQUE simple name ----
    for caller_qual, node in callers:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                name = _callee_name(sub)
                if name and len(func_index.get(name, ())) == 1:
                    (callee_qual,) = tuple(func_index[name])
                    if callee_qual != caller_qual:  # ignore direct self-recursion edges
                        facts.append(Triple(caller_qual, "calls", callee_qual))
    return facts
