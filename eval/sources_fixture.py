"""Loader for the M6 multi-source scenarios (eval/m6_sources.jsonl)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from src.knowledge_graph import Triple
from src.source_reconciliation import sourced

SOURCES = Path(__file__).resolve().parent / "m6_sources.jsonl"
TYPES = {"agreed", "surface", "latent"}


@dataclass
class Scenario:
    id: str
    type: str
    triples: List[Triple]  # built with sourced(), so each carries its source provenance


def load_scenarios(path: str | Path = SOURCES) -> List[Scenario]:
    out: List[Scenario] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        d = json.loads(line)
        if d["type"] not in TYPES:
            raise ValueError(f"bad type {d['type']!r}")
        triples = [sourced(s, r, o, src) for s, r, o, src in d["claims"]]
        out.append(Scenario(id=d["id"], type=d["type"], triples=triples))
    return out
