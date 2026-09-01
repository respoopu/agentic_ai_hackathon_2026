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
    schema = metrics["schema_validation"]
    tools = metrics["tool_call_success"]
    long_tail = metrics["long_tail_coverage"]
    constraints = metrics["constraint_violations"]
    return [
        (
            "B1 Schema validation",
            (
                f"not measured — {schema['note']}; diagnostic gate runs "
                f"{schema['observed_successful_continuations']}/"
                f"{schema['observed_continuation_denominator']} approval continuations"
            ),
        ),
        (
            "B2 Tool-call success",
            f"not fully measured — {_rate(tools)} booking commits; {tools['note']}",
        ),
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
        (
            "B9 Long-tail coverage",
            (
                f"illustrative only: {long_tail['illustrative_numerator']}/"
                f"{long_tail['illustrative_denominator']}; {long_tail['note']}"
            ),
        ),
        (
            "B10 Constraint violations",
            f"not fully measured — {_rate(constraints)} eligible-run diagnostic; {constraints['note']}",
        ),
        ("B11 Adaptation latency", f"not measured — {long['reason']}"),
        (
            "B12 Hold rate",
            (
                f"illustrative input only: {long['scripted_holds']}/"
                f"{long['scripted_hold_denominator']}; not a measured product result"
            ),
        ),
        ("B13 Dead-link rate", f"not measured — {metrics['dead_links']['note']}"),
        ("B14 Adherence delta", f"not measured — {long['reason']}"),
        ("B15 First attendance ≤30d", f"not measured — {first['reason']}"),
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
