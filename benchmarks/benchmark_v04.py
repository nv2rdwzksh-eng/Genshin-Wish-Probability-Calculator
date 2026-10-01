"""Reproducible v0.4 weapon target-planning benchmarks."""

from __future__ import annotations

import time
import tracemalloc

from genshin_wish.weapon_engine import calculate_weapon_target_plan
from genshin_wish.weapon_model import WeaponWishState, community_weapon_soft_pity_model
from genshin_wish.weapon_planning import weapon_threshold_table


MODEL = community_weapon_soft_pity_model()


def benchmark_plan(label: str, state: WeaponWishState, target: int, budget: int) -> None:
    tracemalloc.start()
    start = time.perf_counter()
    result = calculate_weapon_target_plan(
        initial_state=state, wishes=budget, target_copies=target, model=MODEL
    )
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(
        f"{label}: {elapsed:.6f}s, peak states={max(result.active_state_count_by_wish)}, "
        f"peak traced={peak / 1024:.1f} KiB, success={result.success_probability:.8%}"
    )


def main() -> None:
    benchmark_plan("A fresh, target 1, budget 120", WeaponWishState(), 1, 120)
    benchmark_plan(
        "B pity 50, promoted guarantee + Fate, target 1, budget 80",
        WeaponWishState(50, True, 1),
        1,
        80,
    )
    benchmark_plan("C fresh, target 5, budget 700", WeaponWishState(), 5, 700)

    tracemalloc.start()
    start = time.perf_counter()
    rows = weapon_threshold_table(
        initial_state=WeaponWishState(), target_copies=1, model=MODEL
    )
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    values = ", ".join(f"{row.probability:.0%}={row.wishes}" for row in rows)
    print(f"D inverse thresholds: {elapsed:.6f}s, peak traced={peak / 1024:.1f} KiB; {values}")


if __name__ == "__main__":
    main()
