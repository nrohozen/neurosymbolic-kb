"""Relation extraction at the boundary: text -> candidate typed triples, via the base
model on Ollama. Deliberately THIN for M1 (the M1 metrics test the inference + oracle
core, not extraction quality; extraction precision/recall becomes its own metric in M2).
The transport is injectable so tests run offline.
"""
from __future__ import annotations

import json
import re
import urllib.request
from typing import Callable, List

from .knowledge_graph import Provenance, Triple

Transport = Callable[[str, dict], dict]

_ALLOWED_RELATIONS = {"is_a", "has_complexity", "has_property"}
# tolerant of ```json fences and surrounding prose
_OBJ = re.compile(r"\{[^{}]*\}")


def _urllib_transport(url: str, payload: dict, timeout: float = 120.0) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


_PROMPT = (
    "Extract facts from the text as JSON objects, one per line, each "
    '{{"s": subject, "r": relation, "o": object}}. '
    "Use ONLY these relations: is_a, has_complexity, has_property. "
    "For has_complexity use one of: o_1, o_logn, o_n, o_nlogn, o_n2, o_2n. "
    "Output nothing but the JSON objects.\n\nText:\n{text}"
)


class RelationExtractor:
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        host: str = "http://localhost:11434",
        transport: Transport | None = None,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self._transport = transport or _urllib_transport

    def extract(self, text: str, source: str = "") -> List[Triple]:
        """Extract candidate triples from `text`. Each is stamped with `extracted`
        provenance recording `source` (the corpus id / document the text came from), per L5."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": _PROMPT.format(text=text)}],
            "stream": False,
            "options": {"temperature": 0.0},
        }
        try:
            resp = self._transport(f"{self.host}/api/chat", payload)
            content = resp["message"]["content"]
        except Exception:
            return []
        return self._parse(content, source)

    @staticmethod
    def _parse(content: str, source: str = "") -> List[Triple]:
        prov = Provenance("extracted", source)
        triples: List[Triple] = []
        for blob in _OBJ.findall(content):
            try:
                d = json.loads(blob)
            except json.JSONDecodeError:
                continue
            if not all(k in d for k in ("s", "r", "o")):
                continue
            if d["r"] not in _ALLOWED_RELATIONS:
                continue
            triples.append(Triple(str(d["s"]), str(d["r"]), str(d["o"]), provenance=prov))
        return triples
