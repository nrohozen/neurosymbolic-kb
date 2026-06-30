"""Guards the run_all wiring (all milestone mains import + are callable). Offline; does not
execute the milestones (those have their own tests)."""
from eval.run_all import MILESTONES


def test_all_milestones_registered_and_callable():
    assert len(MILESTONES) == 9  # M1, M2, M2-filter, M3, M4, M5, M5.1, M5.2, M6
    titles = [t for t, _ in MILESTONES]
    assert titles == sorted(titles, key=titles.index)  # order preserved (no dedup surprise)
    for title, fn in MILESTONES:
        assert callable(fn), f"{title} main is not callable"
