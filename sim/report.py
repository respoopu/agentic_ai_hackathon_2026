"""One-command, denominator-carrying Hobbi metrics report."""

from __future__ import annotations

from typing import Any

from sim.counterfactual import run as counterfactual
from sim.harness import run_eligible_profiles


def _rate(metric: dict[str, Any], *, invert: bool = False) -> str:
    numerator, denominator = metric["numerator"], metric["denominator"]
    value = 0 if denominator == 0 else numerator / denominator * 100
    if invert:
        value = 100 - value
    return f"{numerator}/{denominator} ({value:.1f}%)"


def rows() -> list[tuple[str, str]]:
    harness = run_eligible_profiles()
    metrics = harness["metrics"]
    comparison = counterfactual()
    first = comparison["first_attendance"]
    long = comparison["longitudinal"]
    completion = metrics["task_completion"]
    denominator = completion["denominator"]
    return [
        ("B1 Schema validation", _rate(metrics["schema_validation"])),
        ("B2 Tool-call success", _rate(metrics["tool_call_success"])),
        (
            "B3 Task completion",
            (
                f"autonomous {completion['autonomous']}/{denominator}; checkpoint "
                f"{completion['checkpoint']}/{denominator}; failed "
                f"{completion['failed']}/{denominator}"
            ),
        ),
        (
            "B4 Token cost/run",
            "0 observed tokens / S$0.00 on deterministic offline path; Bedrock path not measured",
        ),
        (
            "B5 Loop discipline",
            (
                f"mean {metrics['loop_discipline']['mean_iterations']:.1f}; cap hits "
                f"{metrics['loop_discipline']['cap_hits']}/"
                f"{metrics['loop_discipline']['denominator']}"
            ),
        ),
        ("B6 Answer fidelity", "not measured — requires LLM judge plus 20% human double-score"),
        ("B7 S$0 viability", _rate(metrics["s0_viability"])),
        ("B8 Free-option share", _rate(metrics["free_option_share"])),
        ("B9 Long-tail coverage", _rate(metrics["long_tail_coverage"])),
        ("B10 Constraint violations", _rate(metrics["constraint_violations"])),
        ("B11 Adaptation latency", f"{long['adaptation_latency_cycles']} cycle"),
        ("B12 Hold rate", f"{long['holds']}/{long['hold_denominator']} ({long['holds']/long['hold_denominator']*100:.1f}%)"),
        ("B13 Dead-link rate", _rate(metrics["dead_links"])),
        (
            "B14 Adherence delta",
            (
                f"{long['hobbi']['attended']}/{long['hobbi']['bookings']} vs "
                f"{long['static']['attended']}/{long['static']['bookings']} "
                f"({long['adherence_delta_percentage_points']:+.1f} pp)"
            ),
        ),
        (
            "B15 First attendance ≤30d",
            (
                f"Hobbi {first['hobbi']['completed']}/{first['hobbi']['denominator']} "
                f"(median {first['hobbi']['median_days']}d, "
                f"{first['hobbi']['median_cycles']} cycles, "
                f"{first['hobbi']['median_teen_actions']} actions) vs static "
                f"{first['static']['completed']}/{first['static']['denominator']} "
                f"(median {first['static']['median_days']}d, "
                f"{first['static']['median_cycles']} cycles, "
                f"{first['static']['median_teen_actions']} actions)"
            ),
        ),
        ("A1 Unverified reached teen", _rate(metrics["unverified_reached_teen"])),
    ]


def main() -> int:
    print("Hobbi synthetic evaluation report")
    print("All results below are deterministic simulation outputs, not participant evidence.\n")
    for name, value in rows():
        print(f"{name:<30} {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
