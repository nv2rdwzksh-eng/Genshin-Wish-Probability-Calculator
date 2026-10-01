"""Reusable wish-planning operations built on the exact probability engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .engine import (
    TargetPlanningResult,
    calculate_target_plan,
    expected_wishes_to_target,
    iter_target_success_probabilities,
)
from .model import ProbabilityModel, WishState, official_only_model


@dataclass(frozen=True, slots=True)
class WishPlan:
    calculation: TargetPlanningResult
    unconditional_expected_wishes: float


@dataclass(frozen=True, slots=True)
class ThresholdRequirement:
    probability: float
    wishes: int


def _validate_probability(probability: float) -> None:
    if not 0.0 <= probability <= 1.0:
        raise ValueError("desired probability must be between 0 and 1")


def deterministic_wishes_to_target(
    *, initial_state: WishState, target_copies: int, model: ProbabilityModel | None = None
) -> int:
    """Return the finite worst-case wish count that guarantees the target.

    The first configured pity position with q=1 is the model's structural
    5-star deadline. If a non-guaranteed featured result is not certain, the
    worst case includes an off-banner result followed by a guaranteed cycle.
    """

    if target_copies < 0:
        raise ValueError("target_copies cannot be negative")
    remaining = target_copies - initial_state.copies
    if remaining <= 0:
        return 0
    model = model or official_only_model()

    def certain_five_star_wait(starting_pity: int) -> int:
        for pity in range(starting_pity, 90):
            if model.five_star_probability(pity) == 1.0:
                return pity - starting_pity + 1
        raise ValueError("model has no finite 5-star guarantee")

    if model.capturing_radiance is not None:
        from .cr_engine import completion_value
        return completion_value(initial_state=initial_state, target_copies=target_copies, model=model, worst_case=True)

    reset_wait = certain_five_star_wait(0)
    first_wait = certain_five_star_wait(initial_state.pity)
    can_lose_featured = model.featured_probability < 1.0
    if not initial_state.guaranteed and can_lose_featured:
        first_wait += reset_wait
    later_copy_wait = reset_wait * (2 if can_lose_featured else 1)
    return first_wait + (remaining - 1) * later_copy_wait


def calculate_plan(
    *,
    initial_state: WishState,
    wishes: int,
    target_copies: int,
    model: ProbabilityModel | None = None,
) -> WishPlan:
    """Calculate the finite-budget report and unconditional target expectation."""

    model = model or official_only_model()
    calculation = calculate_target_plan(
        initial_state=initial_state,
        wishes=wishes,
        target_copies=target_copies,
        model=model,
    )
    return WishPlan(
        calculation=calculation,
        unconditional_expected_wishes=expected_wishes_to_target(
            initial_state=initial_state,
            target_copies=target_copies,
            model=model,
        ),
    )


def minimum_wishes_for_probability(
    *,
    initial_state: WishState,
    target_copies: int,
    desired_probability: float,
    model: ProbabilityModel | None = None,
) -> int:
    """Return the least N with P(target reached within N) >= the threshold."""

    if target_copies < 0:
        raise ValueError("target_copies cannot be negative")
    _validate_probability(desired_probability)
    if initial_state.copies >= target_copies or desired_probability == 0.0:
        return 0
    model = model or official_only_model()
    certainty_bound = deterministic_wishes_to_target(
        initial_state=initial_state, target_copies=target_copies, model=model
    )
    if desired_probability == 1.0:
        return certainty_bound

    for wishes, probability in iter_target_success_probabilities(
        initial_state=initial_state,
        target_copies=target_copies,
        model=model,
        max_wishes=certainty_bound,
    ):
        if probability >= desired_probability:
            return wishes
    raise RuntimeError("finite guarantee was not reached; probability model is inconsistent")


def threshold_table(
    *,
    initial_state: WishState,
    target_copies: int,
    probabilities: Iterable[float] = (0.50, 0.75, 0.90, 0.95, 0.99),
    model: ProbabilityModel | None = None,
) -> tuple[ThresholdRequirement, ...]:
    """Calculate multiple inverse thresholds with one incremental DP pass."""

    requested = tuple(float(value) for value in probabilities)
    for probability in requested:
        _validate_probability(probability)
    if target_copies < 0:
        raise ValueError("target_copies cannot be negative")
    model = model or official_only_model()
    if initial_state.copies >= target_copies:
        return tuple(ThresholdRequirement(value, 0) for value in requested)

    certainty_bound = deterministic_wishes_to_target(
        initial_state=initial_state, target_copies=target_copies, model=model
    )
    resolved: dict[float, int] = {0.0: 0, 1.0: certainty_bound}
    pending = sorted({value for value in requested if 0.0 < value < 1.0})

    if pending:
        for wishes, success_probability in iter_target_success_probabilities(
            initial_state=initial_state,
            target_copies=target_copies,
            model=model,
            max_wishes=certainty_bound,
        ):
            while pending and success_probability >= pending[0]:
                resolved[pending.pop(0)] = wishes
            if not pending:
                break

    return tuple(ThresholdRequirement(value, resolved[value]) for value in requested)
