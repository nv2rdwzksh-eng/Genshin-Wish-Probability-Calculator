"""Single-process case runner for external peak-working-set measurement."""

from __future__ import annotations

import argparse

from genshin_wish import (
    WishState,
    calculate,
    calculate_target_plan,
    community_soft_pity_model,
)


CASES = {
    "A": (WishState(0, False), 320, 3),
    "B": (WishState(37, False), 240, 2),
    "C": (WishState(0, False), 800, 7),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=CASES)
    parser.add_argument("mode", choices=("full", "planning"))
    args = parser.parse_args()
    state, budget, target = CASES[args.case]
    function = calculate if args.mode == "full" else calculate_target_plan
    result = function(
        initial_state=state,
        wishes=budget,
        target_copies=target,
        model=community_soft_pity_model(),
    )
    print(result.success_probability)


if __name__ == "__main__":
    main()
