"""Repeatable v0.3.1 wall-clock benchmarks; no timing assertions."""

from __future__ import annotations

import argparse
from statistics import median
from time import perf_counter

from genshin_wish import (
    WishState,
    calculate_plan,
    community_soft_pity_model,
    minimum_wishes_for_probability,
    threshold_table,
)


def measure(operation, repeats: int) -> float:
    samples = []
    for _ in range(repeats):
        start = perf_counter()
        operation()
        samples.append(perf_counter() - start)
    return median(samples)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    if args.repeats <= 0:
        parser.error("--repeats must be positive")

    model = community_soft_pity_model()
    cases = (
        (
            "A: full report, pity 0, target 3, budget 320",
            lambda: calculate_plan(
                initial_state=WishState(0, False),
                wishes=320,
                target_copies=3,
                model=model,
            ),
        ),
        (
            "B: 50/75/90/95/99% thresholds, pity 0, target 3",
            lambda: threshold_table(
                initial_state=WishState(0, False),
                target_copies=3,
                probabilities=(0.50, 0.75, 0.90, 0.95, 0.99),
                model=model,
            ),
        ),
        (
            "B99: one 99% inverse query, pity 0, target 3",
            lambda: minimum_wishes_for_probability(
                initial_state=WishState(0, False),
                target_copies=3,
                desired_probability=0.99,
                model=model,
            ),
        ),
        (
            "C: full report, pity 37, target 2, budget 240",
            lambda: calculate_plan(
                initial_state=WishState(37, False),
                wishes=240,
                target_copies=2,
                model=model,
            ),
        ),
    )
    for name, operation in cases:
        print(f"{name}\t{measure(operation, args.repeats):.6f}s")


if __name__ == "__main__":
    main()
