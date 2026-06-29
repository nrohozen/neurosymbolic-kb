"""Loader for the M2 extraction corpus (eval/m2_corpus.jsonl).

Each line is a source text plus its hand-labeled GOLD triples — what a correct
extractor should produce from that text, restricted to the M1 schema. Shared by the
corpus test and the M2 scorecard so there is one parser, not two.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from src.knowledge_graph import Triple

CORPUS = Path(__file__).resolve().parent / "m2_corpus.jsonl"

# the M1 schema's vocabulary — the corpus may not range outside it.
ALLOWED_RELATIONS = {"is_a", "has_complexity", "has_property"}
COMPLEXITY_ENUM = {"o_1", "o_logn", "o_n", "o_nlogn", "o_n2", "o_2n"}


@dataclass(frozen=True)
class CorpusEntry:
    id: str
    text: str
    gold: Tuple[Triple, ...]


def load_corpus(path: str | Path = CORPUS) -> List[CorpusEntry]:
    entries: List[CorpusEntry] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        d = json.loads(line)
        gold = tuple(Triple(s, r, o) for s, r, o in d["gold"])
        entries.append(CorpusEntry(id=d["id"], text=d["text"], gold=gold))
    return entries
