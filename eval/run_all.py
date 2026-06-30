"""Top-level evaluation: run every milestone scorecard (M1-M6) in chronological order.

Deductive scorecards need only clingo; the live-judge metrics (M1#4, M2, M5#27, M5.1/5.2)
SKIP gracefully without a local Ollama. See RESULTS.md for the consolidated synthesis and
DIRECTION.md for the per-milestone RESULT blocks.

Run:  python -m eval.run_all
"""
from __future__ import annotations

from eval import (
    run_m1,
    run_m2,
    run_m2_filter,
    run_m3,
    run_m4,
    run_m5,
    run_m5_1,
    run_m5_2,
    run_m6,
)

# (title, main) in chronological order
MILESTONES = [
    ("M1   domain 1: algorithms & data structures", run_m1.main),
    ("M2   extraction path", run_m2.main),
    ("M2-filter   consistency filter in isolation", run_m2_filter.main),
    ("M3   domain 2: a codebase", run_m3.main),
    ("M4   domain 3: homelab / temporal oracle", run_m4.main),
    ("M5   domain 4: CS-as-a-field / weak oracle", run_m5.main),
    ("M5.1 calibrated abstention", run_m5_1.main),
    ("M5.2 calibrated abstention (probe fix, held-out)", run_m5_2.main),
    ("M6   domain 5: open / contested knowledge", run_m6.main),
]


def main() -> int:
    rc = 0
    for title, fn in MILESTONES:
        print("\n" + "#" * 72)
        print(f"#  {title}")
        print("#" * 72)
        try:
            rc |= fn()
        except Exception as exc:  # keep going so one failure doesn't hide the rest
            print(f"  ERROR running {title}: {exc}")
            rc = 1
    print("\n" + "=" * 72)
    print("  run_all complete.  See RESULTS.md for the consolidated synthesis.")
    print("=" * 72)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
