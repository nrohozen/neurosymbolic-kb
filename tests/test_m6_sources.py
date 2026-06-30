"""Validation of the M6 multi-source fixture. Offline, no clingo, no network."""
from eval.sources_fixture import load_scenarios


def test_fixture_is_balanced_and_well_formed():
    scs = load_scenarios()
    by = {}
    for s in scs:
        by[s.type] = by.get(s.type, 0) + 1
    assert by.get("agreed", 0) >= 4
    assert by.get("surface", 0) + by.get("latent", 0) >= 10  # >=10 planted conflicts
    assert by.get("latent", 0) >= 5
    assert all(s.triples for s in scs)


def test_scenario_ids_unique_and_sources_tagged():
    scs = load_scenarios()
    assert len({s.id for s in scs}) == len(scs)
    for s in scs:
        for t in s.triples:
            assert t.provenance and t.provenance.method == "source" and t.provenance.detail
