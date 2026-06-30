"""Judge claim-text extension + M5 fixture well-formedness. Offline, no clingo, no network."""
import json
from pathlib import Path

from src.judge_ensemble import JudgeEnsemble
from src.knowledge_graph import Triple

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ROOT / "eval" / "m5_claims.jsonl"
REVISION = ROOT / "eval" / "m5_revision.jsonl"


def _load(path):
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


def test_judge_uses_injected_claim_text():
    captured = {}

    def stub(url, payload):
        captured["content"] = payload["messages"][0]["content"]
        return {"message": {"content": "0.9"}}

    je = JudgeEnsemble(models=["m"], transport=stub,
                       claim_text=lambda t: f"Is {t.s} a subfield of {t.o}?")
    assert je.score(Triple("ml", "subfield_of", "ai")) == 0.9
    assert "subfield of" in captured["content"]


def test_claims_are_well_formed():
    claims = _load(CLAIMS)
    assert sum(c["kind"] == "derivable" for c in claims) >= 5
    assert sum(c["kind"] == "nonderivable" for c in claims) >= 5
    for c in claims:
        assert c["kind"] in {"derivable", "nonderivable"}
        assert isinstance(c["gold"], bool)


def test_revision_scenarios_are_well_formed():
    scenarios = _load(REVISION)
    assert len(scenarios) >= 10
    for s in scenarios:
        assert s["accepted"] and s["candidate"] and s["gold_remain"]
        assert len(s["candidate"]) == 4  # [s, r, o, confidence]
