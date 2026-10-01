"""Paired v0.4.1 CR comparisons; wall time medians, no timing assertions."""

import argparse
from statistics import median
from time import perf_counter

from genshin_wish import (
    WishState, calculate, calculate_plan, calculate_target_plan,
    community_soft_pity_model, threshold_table, with_capturing_radiance,
)


def measure(operation, repeats):
    samples = []
    for _ in range(repeats):
        start = perf_counter()
        result = operation()
        samples.append(perf_counter() - start)
    return median(samples), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    legacy = community_soft_pity_model()
    for name, state, budget, target in (
        ('A', WishState(), 320, 3),
        ('B', WishState(37), 240, 2),
        ('C', WishState(), 800, 7),
    ):
        for enabled in (False, True):
            model = with_capturing_radiance(legacy) if enabled else legacy
            elapsed, result = measure(lambda: calculate_target_plan(
                initial_state=state, wishes=budget, target_copies=target, model=model
            ), args.repeats)
            print(f'{name} CR={enabled}: {elapsed:.6f}s; peak states={max(result.active_state_count_by_wish)}; success={result.success_probability:.12%}')
    for enabled in (False, True):
        model = with_capturing_radiance(legacy) if enabled else legacy
        elapsed, full = measure(lambda: calculate(
            initial_state=WishState(37), wishes=240, target_copies=2, model=model
        ), args.repeats)
        plan = calculate_plan(initial_state=WishState(37), wishes=240, target_copies=2, model=model)
        print(f'Full CR={enabled}: {elapsed:.6f}s; success={full.success_probability:.12%}; E[copies]={full.expected_copies:.12f}; E[T]={plan.unconditional_expected_wishes:.12f}; conditional={plan.calculation.expected_wishes_if_success_within_budget:.12f}')
        elapsed, rows = measure(lambda: threshold_table(
            initial_state=WishState(37), target_copies=2,
            probabilities=(.5, .75, .9, .95, .99, 1.0), model=model
        ), args.repeats)
        print(f'Inverse CR={enabled}: {elapsed:.6f}s; ' + ', '.join(f'{r.probability:.0%}={r.wishes}' for r in rows))


if __name__ == '__main__':
    main()
