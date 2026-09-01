"""Honest boundary for counterfactual metrics not yet backed by observations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def run() -> dict[str, Any]:
    payload = json.loads(
        (ROOT / "data" / "synthetic_teen.json").read_text(encoding="utf-8")
    )
    cycles = payload["cycles"]
    holds = sum(1 for cycle in cycles if cycle["hobbi_action"] == "hold_this_week")
    reason = (
        "requires an executable static recommender, runtime-generated plans, "
        "Observer transitions, and attendance observations"
    )
    return {
        "label": "illustrative scripted scenario; not measured effectiveness evidence",
        "first_attendance": {"measured": False, "reason": reason},
        "longitudinal": {
            "measured": False,
            "reason": reason,
            "scripted_cycles": len(cycles),
            "scripted_holds": holds,
            "scripted_hold_denominator": len(cycles),
        },
    }


def main() -> int:
    print(json.dumps(run(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
