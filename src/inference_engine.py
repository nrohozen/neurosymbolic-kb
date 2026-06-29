"""Forward-chaining / deductive-closure engine over the ASP schema, backed by clingo.

- SAT  -> `atoms` is the deductive closure (the shown predicates of the first answer set).
- UNSAT -> a contradiction: an integrity constraint in the schema fired.

clingo is imported lazily inside `run()` so the rest of the package (and any test that
injects a stub engine) does not require clingo to import.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class InferenceResult:
    satisfiable: bool
    atoms: frozenset  # shown atoms of the first answer set (empty if UNSAT)


class InferenceEngine:
    def __init__(self, schema_text: str) -> None:
        self.schema_text = schema_text

    @classmethod
    def from_schema_file(cls, path: str | Path) -> "InferenceEngine":
        return cls(Path(path).read_text(encoding="utf-8"))

    def run(self, facts: Iterable[str]) -> InferenceResult:
        import clingo  # lazy: only needed when actually solving

        program = self.schema_text + "\n" + "".join(f"{f}.\n" for f in facts)
        ctl = clingo.Control(["--warn=none"])
        ctl.add("base", [], program)
        ctl.ground([("base", [])])

        shown: set[str] = set()
        with ctl.solve(yield_=True) as handle:
            for model in handle:
                shown = {str(sym) for sym in model.symbols(shown=True)}
                break
            result = handle.get()
        return InferenceResult(satisfiable=bool(result.satisfiable), atoms=frozenset(shown))

    def is_consistent(self, facts: Iterable[str]) -> bool:
        return self.run(facts).satisfiable

    def entails(self, facts: Iterable[str], query_atom: str) -> bool:
        """True iff `facts` are consistent AND `query_atom` is in the deductive closure."""
        r = self.run(facts)
        return r.satisfiable and query_atom in r.atoms
