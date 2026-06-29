"""LLM-as-judge ensemble over a local Ollama, for the weak (conceptual) oracle.

Each seated model scores whether a conceptual claim is true in [0, 1]; the ensemble
averages decorrelated families. The HTTP transport is injectable so tests run offline
with a stub and never touch the network. Any transport/parse failure yields `None`
(unknown) rather than a guess.
"""
from __future__ import annotations

import json
import re
import urllib.request
from typing import Callable, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from .knowledge_graph import Triple

_FLOAT = re.compile(r"[01](?:\.\d+)?|0?\.\d+")

# A transport takes (url, json_payload) and returns the parsed JSON response dict.
Transport = Callable[[str, dict], dict]


def _urllib_transport(url: str, payload: dict, timeout: float = 60.0) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _claim_text(triple: "Triple") -> str:
    return (
        f"In computer science, is the following statement true: "
        f"'{triple.s.replace('_', ' ')}' has the property "
        f"'{triple.o.replace('_', ' ')}'?"
    )


class JudgeEnsemble:
    def __init__(
        self,
        models: Sequence[str] = ("qwen2.5:7b", "gemma2:9b"),
        host: str = "http://localhost:11434",
        transport: Transport | None = None,
    ) -> None:
        self.models = list(models)
        self.host = host.rstrip("/")
        self._transport = transport or _urllib_transport

    def _score_one(self, model: str, triple: "Triple") -> float | None:
        prompt = (
            _claim_text(triple)
            + " Reply with ONLY a probability between 0 and 1 that it is true."
        )
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.0},
        }
        try:
            resp = self._transport(f"{self.host}/api/chat", payload)
            content = resp["message"]["content"]
        except Exception:
            return None
        match = _FLOAT.search(content)
        if not match:
            return None
        try:
            return max(0.0, min(1.0, float(match.group())))
        except ValueError:
            return None

    def score(self, triple: "Triple") -> float | None:
        """Average the seated models' scores; None if no model produced a usable score."""
        scores = [s for s in (self._score_one(m, triple) for m in self.models) if s is not None]
        if not scores:
            return None
        return sum(scores) / len(scores)
