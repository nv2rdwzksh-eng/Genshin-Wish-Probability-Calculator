"""Independent Monte Carlo verification using the same configured rules."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .model import ProbabilityModel, WishState, official_only_model


@dataclass(frozen=True, slots=True)
class SimulationResult:
    trials: int
    successes: int
    success_probability: float
    copy_distribution: dict[int, float]


def simulate(
    *,
    initial_state: WishState,
    wishes: int,
    target_copies: int,
    trials: int = 100_000,
    seed: int | None = None,
    model: ProbabilityModel | None = None,
) -> SimulationResult:
    if wishes < 0 or target_copies < 0:
        raise ValueError("wishes and target_copies cannot be negative")
    if trials <= 0:
        raise ValueError("trials must be positive")
    model = model or official_only_model()
    rng = random.Random(seed)
    counts: dict[int, int] = {}
    successes = 0

    for _ in range(trials):
        pity = initial_state.pity
        guaranteed = initial_state.guaranteed
        copies = initial_state.copies
        counter = initial_state.cr_counter
        for _ in range(wishes):
            if rng.random() < model.five_star_probability(pity):
                pity = 0
                if guaranteed:
                    copies += 1
                    guaranteed = False
                elif model.capturing_radiance is not None:
                    cr = model.capturing_radiance
                    if rng.random() < cr.probabilities[counter]:
                        copies += 1
                        counter = cr.reset_counter
                    elif rng.random() < model.featured_probability:
                        copies += 1
                        counter = cr.win_counters[counter]
                    else:
                        counter = cr.loss_counters[counter]
                        guaranteed = True
                elif rng.random() < model.featured_probability:
                    copies += 1
                else:
                    guaranteed = True
            else:
                pity += 1
        counts[copies] = counts.get(copies, 0) + 1
        successes += copies >= target_copies

    return SimulationResult(
        trials=trials,
        successes=successes,
        success_probability=successes / trials,
        copy_distribution={copies: count / trials for copies, count in sorted(counts.items())},
    )

