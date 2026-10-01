"""v0.5 composition timings and a reproducible worked example."""

import argparse
from statistics import median
from time import perf_counter

from genshin_wish import (
    CharacterGoal, WeaponGoal, WishState, WeaponWishState,
    community_soft_pity_model, community_weapon_soft_pity_model,
    with_capturing_radiance, calculate_combined_plan,
    deterministic_combined_wishes_to_target, prepare_combined_distribution,
)


def measure(operation, repeats):
    times = []
    for _ in range(repeats):
        start = perf_counter()
        result = operation()
        times.append(perf_counter() - start)
    return median(times), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    character_model = with_capturing_radiance(community_soft_pity_model())
    weapon_model = community_weapon_soft_pity_model()
    cases = (
        ('A fresh C1 + W1, budget 240', CharacterGoal(model=character_model), WeaponGoal(model=weapon_model), 240),
        ('B character pity37 K2 + fresh W1, budget 320', CharacterGoal(WishState(37), 2, character_model), WeaponGoal(model=weapon_model), 320),
        ('C guaranteed character pity60 K2 + weapon pity50/guarantee/Fate K1, budget240', CharacterGoal(WishState(60, True, 0, 2), 2, character_model), WeaponGoal(WeaponWishState(50, True, 1), 1, weapon_model), 240),
        ('D fresh C7 + W5, budget1200', CharacterGoal(target_copies=7, model=character_model), WeaponGoal(target_copies=5, model=weapon_model), 1200),
    )
    for name, character, weapon, budget in cases:
        elapsed, result = measure(lambda: calculate_combined_plan(
            character_goal=character, weapon_goal=weapon, total_wishes=budget,
        ), args.repeats)
        print(f'{name}: {elapsed:.6f}s; both={result.success_probability:.10%}; character-only={result.character_success_weapon_failure_probability:.10%}; character-fail={result.character_failure_probability:.10%}')

    _, character, weapon, budget = cases[1]
    bound = deterministic_combined_wishes_to_target(character_goal=character, weapon_goal=weapon)
    elapsed, prepared = measure(lambda: prepare_combined_distribution(
        character_goal=character, weapon_goal=weapon, max_wishes=bound,
    ), args.repeats)
    print(f'B complete curve + inverse preparation: {elapsed:.6f}s; bound={bound}; peak phase states C={max(prepared.character_result.active_state_count_by_wish)}, W={max(prepared.weapon_result.active_state_count_by_wish)}')
    elapsed, rows = measure(lambda: prepared.threshold_table((.5, .75, .9, .95, .99, 1)), args.repeats)
    print(f'B inverse lookup on reused curve: {elapsed:.6f}s; ' + ', '.join(f'{r.probability:.0%}={r.wishes}' for r in rows))
    result = prepared.report(budget)
    print(f'B expected remaining (failure=0): {result.expected_remaining_wishes_after_character:.12f}; remaining|C success: {result.expected_remaining_wishes_given_character_success:.12f}; completion|both: {result.expected_total_completion_wish_given_success:.12f}')


if __name__ == '__main__':
    main()
