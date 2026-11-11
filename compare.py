"""Compare retrieval reports and return 0 for pass, 1 for regression, 2 for invalid input."""

import argparse
import math
import sys

from common import read

METRICS = (
    "empty_load_p50_ms",
    "restart_load_p50_ms",
    "empty_first_query_p50_ms",
    "restart_first_query_p50_ms",
    "warm_query_p95_ms",
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("baseline")
    p.add_argument("candidate")
    p.add_argument("--max-slowdown-pct", type=float, required=True)
    p.add_argument("--warm-p95-budget-ms", type=float)
    args = p.parse_args()
    if not math.isfinite(args.max_slowdown_pct) or args.max_slowdown_pct < 0:
        p.error("Supply a finite non-negative slowdown allowance.")
    if args.warm_p95_budget_ms is not None and (
        not math.isfinite(args.warm_p95_budget_ms) or args.warm_p95_budget_ms <= 0
    ):
        p.error("Supply a positive finite warm query budget.")
    base, cand = read(args.baseline), read(args.candidate)
    if base["schema"] != 1 or cand["schema"] != 1 or base["config"] != cand["config"]:
        p.error(
            "Use the same report schema, index, cases, host label and benchmark settings."
        )
    if base["versions"]["python"] != cand["versions"]["python"]:
        p.error("Use the same Python runtime for both runs.")
    if not base["case_pass"] or set(base["case_pass"]) != set(cand["case_pass"]):
        p.error("The reports must cover the same nonempty case set.")
    if not all(base["case_pass"].values()):
        p.error("Choose a baseline that passes every required case.")
    failures = [
        case + " missed its expected document"
        for case, ok in cand["case_pass"].items()
        if not ok
    ]
    print("SDK versions", base["versions"], "->", cand["versions"])
    for name in METRICS:
        before, after = base["metrics"][name], cand["metrics"][name]
        if any(not math.isfinite(value) or value <= 0 for value in [before, after]):
            p.error("Missing or invalid timing: " + name)
        change = 100 * (after / before - 1)
        print(f"{name}: {before:.2f} -> {after:.2f} ms ({change:+.1f}%)")
        if change > args.max_slowdown_pct + 1e-9:
            failures.append(name + " exceeded allowed slowdown")
    if (
        args.warm_p95_budget_ms is not None
        and cand["metrics"]["warm_query_p95_ms"] > args.warm_p95_budget_ms
    ):
        failures.append("warm p95 exceeded the absolute budget")
    print("FAIL: " + "; ".join(failures) if failures else "PASS")
    return int(bool(failures))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, KeyError, TypeError, ValueError) as e:
        print("Unusable report:", e, file=sys.stderr)
        sys.exit(2)
