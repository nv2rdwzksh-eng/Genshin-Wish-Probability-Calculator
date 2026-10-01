"""Independent Monte Carlo cross-check for Weapon Event Wish calculations."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .weapon_model import (
    WeaponProbabilityModel,
    WeaponWishState,
    official_only_weapon_model,
)


@dataclass(frozen=True, slots=True)
class WeaponSimulationResult:
    trials: int
    successes: int
    success_probability: float
    copy_distribution: dict[int, float]


def simulate_weapon(
    *,
    initial_state: WeaponWishState,
    wishes: int,
    target_copies: int,
    trials: int = 100_000,
    seed: int | None = None,
    model: WeaponProbabilityModel | None = None,
) -> WeaponSimulationResult:
    if wishes < 0 or target_copies < 0:
        raise ValueError("wishes and target_copies cannot be negative")
    if trials <= 0:
        raise ValueError("trials must be positive")
    model = model or official_only_weapon_model()
    rng = random.Random(seed)
    counts: dict[int, int] = {}
    successes = 0

    for _ in range(trials):
        pity = initial_state.pity
        promoted_guaranteed = initial_state.promoted_guaranteed
        fate_point = initial_state.fate_point
        copies = initial_state.copies
        for _ in range(wishes):
            if rng.random() >= model.five_star_probability(pity):
                pity += 1
                continue
            pity = 0
            if fate_point:
                copies += 1
                fate_point = 0
                promoted_guaranteed = False
                continue
            promoted = promoted_guaranteed or rng.random() < model.promoted_probability
            if promoted:
                desired = rng.random() < model.desired_given_promoted_probability
                if desired:
                    copies += 1
                    fate_point = 0
                else:
                    fate_point = 1
                promoted_guaranteed = False
            else:
                fate_point = 1
                promoted_guaranteed = True
        counts[copies] = counts.get(copies, 0) + 1
        successes += copies >= target_copies

    return WeaponSimulationResult(
        trials=trials,
        successes=successes,
        success_probability=successes / trials,
        copy_distribution={key: value / trials for key, value in sorted(counts.items())},
    )
