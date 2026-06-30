"""End-to-end test of the M6 scorecard over the real fixture. Offline (clingo local);
skipped if clingo absent."""
from pathlib import Path

import pytest

pytest.importorskip("clingo")

from eval.run_m6 import evaluate  # noqa: E402
from eval.sources_fixture import load_scenarios  # noqa: E402
from src.inference_engine import InferenceEngine  # noqa: E402
from src.source_reconciliation import reconcile, surface_conflicts  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "open.lp"


def test_reconciliation_metrics_on_the_fixture():
    engine = InferenceEngine.from_schema_file(SCHEMA)
    scenarios = load_scenarios()
    claims = [t for s in scenarios for t in s.triples]
    recon = reconcile(engine, claims)
    s = evaluate(scenarios, recon, surface_conflicts(engine, claims))

    assert s.detection_recall == pytest.approx(1.0)     # all planted conflicts found
    assert s.latent_recall == pytest.approx(1.0)        # incl. the latent ones
    assert s.surface_latent_recall == pytest.approx(0.0)  # pairwise baseline misses latent
    assert s.faithful_rate == pytest.approx(1.0)        # every position kept, none resolved
    assert s.false_contestation == pytest.approx(0.0)   # agreement not over-flagged
