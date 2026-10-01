"""Reusable target planning and inverse planning for Weapon Event Wishes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .planning import ThresholdRequirement
from .results import TargetPlanningResult
from .weapon_engine import (
    calculate_weapon_target_plan,
    iter_weapon_target_success_probabilities,
)
from .weapon_model import (
    WeaponProbabilityModel,
    WeaponWishState,
    official_only_weapon_model,
)


@dataclass(frozen=True, slots=True)
class WeaponWishPlan:
    calculation: TargetPlanningResult[WeaponWishState]
    unconditional_expected_wishes: float


def _validate_probability(probability: float) -> None:
    if not 0.0 <= probability <= 1.0:
        raise ValueError("desired probability must be between 0 and 1")


def _certain_five_star_wait(
    pity: int, model: WeaponProbabilityModel
) -> int:
    for position in range(pity, 80):
        if model.five_star_probability(position) == 1.0:
            return position - pity + 1
    raise ValueError("weapon model has no finite 5-star guarantee")


def deterministic_weapon_wishes_to_target(
    *,
    initial_state: WeaponWishState,
    target_copies: int,
    model: WeaponProbabilityModel | None = None,
) -> int:
    """Finite worst-case count under one-Fate-Point Epitomized Path."""

    if target_copies < 0:
        raise ValueError("target_copies cannot be negative")
    remaining = target_copies - initial_state.copies
    if remaining <= 0:
        return 0
    model = model or official_only_weapon_model()
    first_wait = _certain_five_star_wait(initial_state.pity, model)
    reset_wait = _certain_five_star_wait(0, model)

    if initial_state.fate_point:
        first_copy = first_wait
    else:
        current_desired_probability = (
            model.desired_given_promoted_probability
            if initial_state.promoted_guaranteed
            else model.promoted_probability
            * model.desired_given_promoted_probability
        )
        first_copy = first_wait + (reset_wait if current_desired_probability < 1.0 else 0)

    reset_desired_probability = (
        model.promoted_probability * model.desired_given_promoted_probability
    )
    later_copy = reset_wait * (2 if reset_desired_probability < 1.0 else 1)
    return first_copy + (remaining - 1) * later_copy


def expected_weapon_wishes_to_target(
    *,
    initial_state: WeaponWishState,
    target_copies: int,
    model: WeaponProbabilityModel | None = None,
) -> float:
    """Return E[T] by exact backward recurrence over weapon rule states."""

    if target_copies < 0:
        raise ValueError("target_copies cannot be negative")
    if initial_state.copies >= target_copies:
        return 0.0
    model = model or official_only_weapon_model()
    fate_values: dict[int, list[float]] = {}
    guarantee_values: dict[int, list[float]] = {}
    normal_values: dict[int, list[float]] = {}
    selection = model.desired_given_promoted_probability
    fresh_desired = model.promoted_probability * selection

    for copies in range(target_copies - 1, initial_state.copies - 1, -1):
        after_desired = (
            0.0 if copies + 1 >= target_copies else normal_values[copies + 1][0]
        )
        fate = [0.0] * 80
        for pity in range(79, -1, -1):
            q = model.five_star_probabilities[pity]
            continuation = 0.0 if pity == 79 else (1.0 - q) * fate[pity + 1]
            fate[pity] = 1.0 + continuation + q * after_desired
        fate_values[copies] = fate

        guaranteed = [0.0] * 80
        for pity in range(79, -1, -1):
            q = model.five_star_probabilities[pity]
            continuation = (
                0.0 if pity == 79 else (1.0 - q) * guaranteed[pity + 1]
            )
            guaranteed[pity] = 1.0 + continuation + q * (
                selection * after_desired + (1.0 - selection) * fate[0]
            )
        guarantee_values[copies] = guaranteed

        normal = [0.0] * 80
        for pity in range(79, -1, -1):
            q = model.five_star_probabilities[pity]
            continuation = 0.0 if pity == 79 else (1.0 - q) * normal[pity + 1]
            normal[pity] = 1.0 + continuation + q * (
                fresh_desired * after_desired + (1.0 - fresh_desired) * fate[0]
            )
        normal_values[copies] = normal

    if initial_state.fate_point:
        values = fate_values
    elif initial_state.promoted_guaranteed:
        values = guarantee_values
    else:
        values = normal_values
    return values[initial_state.copies][initial_state.pity]


def calculate_weapon_plan(
    *,
    initial_state: WeaponWishState,
    wishes: int,
    target_copies: int,
    model: WeaponProbabilityModel | None = None,
) -> WeaponWishPlan:
    model = model or official_only_weapon_model()
    return WeaponWishPlan(
        calculation=calculate_weapon_target_plan(
            initial_state=initial_state,
            wishes=wishes,
            target_copies=target_copies,
            model=model,
        ),
        unconditional_expected_wishes=expected_weapon_wishes_to_target(
            initial_state=initial_state,
            target_copies=target_copies,
            model=model,
        ),
    )


def minimum_weapon_wishes_for_probability(
    *,
    initial_state: WeaponWishState,
    target_copies: int,
    desired_probability: float,
    model: WeaponProbabilityModel | None = None,
) -> int:
    if target_copies < 0:
        raise ValueError("target_copies cannot be negative")
    _validate_probability(desired_probability)
    if initial_state.copies >= target_copies or desired_probability == 0.0:
        return 0
    model = model or official_only_weapon_model()
    bound = deterministic_weapon_wishes_to_target(
        initial_state=initial_state, target_copies=target_copies, model=model
    )
    if desired_probability == 1.0:
        return bound
    for wishes, probability in iter_weapon_target_success_probabilities(
        initial_state=initial_state,
        target_copies=target_copies,
        max_wishes=bound,
        model=model,
    ):
        if probability >= desired_probability:
            return wishes
    raise RuntimeError("finite weapon guarantee was not reached")


def weapon_threshold_table(
    *,
    initial_state: WeaponWishState,
    target_copies: int,
    probabilities: Iterable[float] = (0.50, 0.75, 0.90, 0.95, 0.99),
    model: WeaponProbabilityModel | None = None,
) -> tuple[ThresholdRequirement, ...]:
    requested = tuple(float(value) for value in probabilities)
    for probability in requested:
        _validate_probability(probability)
    if target_copies < 0:
        raise ValueError("target_copies cannot be negative")
    if initial_state.copies >= target_copies:
        return tuple(ThresholdRequirement(value, 0) for value in requested)
    model = model or official_only_weapon_model()
    bound = deterministic_weapon_wishes_to_target(
        initial_state=initial_state, target_copies=target_copies, model=model
    )
    resolved = {0.0: 0, 1.0: bound}
    pending = sorted({value for value in requested if 0.0 < value < 1.0})
    if pending:
        for wishes, success in iter_weapon_target_success_probabilities(
            initial_state=initial_state,
            target_copies=target_copies,
            max_wishes=bound,
            model=model,
        ):
            while pending and success >= pending[0]:
                resolved[pending.pop(0)] = wishes
            if not pending:
                break
    return tuple(ThresholdRequirement(value, resolved[value]) for value in requested)
