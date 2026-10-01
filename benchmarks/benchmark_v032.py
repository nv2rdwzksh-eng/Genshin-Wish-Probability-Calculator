"""Target-aware v0.3.2 benchmark scenarios; no timing assertions."""

from __future__ import annotations

import argparse
from statistics import median
from time import perf_counter

from genshin_wish import WishState, calculate_target_plan, community_soft_pity_model


CASES = {
    "A": (WishState(0, False), 320, 3),
    "B": (WishState(37, False), 240, 2),
    "C": (WishState(0, False), 800, 7),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats <= 0:
        parser.error("--repeats must be positive")

    model = community_soft_pity_model()
    for name, (state, budget, target) in CASES.items():
        samples = []
        result = None
        for _ in range(args.repeats):
            start = perf_counter()
            result = calculate_target_plan(
                initial_state=state,
                wishes=budget,
                target_copies=target,
                model=model,
            )
            samples.append(perf_counter() - start)
        assert result is not None
        print(
            f"{name}\t{median(samples):.6f}s\t"
            f"max_active_states={max(result.active_state_count_by_wish)}\t"
            f"success={result.success_probability:.12%}"
        )


if __name__ == "__main__":
    main()
