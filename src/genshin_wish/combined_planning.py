"""Exact character-then-weapon composition through public target results.

No banner state is propagated here. The weapon phase always uses the supplied
initial weapon state. Conditional on character completion at t, it receives
N-t wishes and its usual standalone completion distribution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import accumulate
from math import fsum
from typing import Iterable, Protocol, Sequence

from .engine import calculate_target_plan
from .model import ProbabilityModel, WishState, official_only_model
from .planning import ThresholdRequirement, deterministic_wishes_to_target
from .results import TargetPlanningResult
from .weapon_engine import calculate_weapon_target_plan
from .weapon_model import (
    WeaponProbabilityModel, WeaponWishState, official_only_weapon_model,
)
from .weapon_planning import deterministic_weapon_wishes_to_target


def _validate_count(value: int, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")


def _validate_probability(value: float) -> None:
    if not 0 <= value <= 1:
        raise ValueError("desired probability must be between 0 and 1")


class TargetGoal(Protocol):
    """Small adapter contract for obtaining a banner's completion law.

    A future sequence can consume the same result interface without knowing
    the internal pity/guarantee state. v0.5 exposes only character -> weapon.
    """

    def calculate(self, wishes: int) -> TargetPlanningResult: ...

    def certain_wishes(self) -> int: ...


@dataclass(frozen=True, slots=True)
class CharacterGoal:
    initial_state: WishState = field(default_factory=WishState)
    target_copies: int = 1
    model: ProbabilityModel = field(default_factory=official_only_model)

    def __post_init__(self) -> None:
        _validate_count(self.target_copies, "character target copies")

    def calculate(self, wishes: int) -> TargetPlanningResult[WishState]:
        return calculate_target_plan(
            initial_state=self.initial_state, wishes=wishes,
            target_copies=self.target_copies, model=self.model,
        )

    def certain_wishes(self) -> int:
        return deterministic_wishes_to_target(
            initial_state=self.initial_state, target_copies=self.target_copies,
            model=self.model,
        )


@dataclass(frozen=True, slots=True)
class WeaponGoal:
    initial_state: WeaponWishState = field(default_factory=WeaponWishState)
    target_copies: int = 1
    model: WeaponProbabilityModel = field(default_factory=official_only_weapon_model)

    def __post_init__(self) -> None:
        _validate_count(self.target_copies, "weapon target copies")

    def calculate(self, wishes: int) -> TargetPlanningResult[WeaponWishState]:
        return calculate_weapon_target_plan(
            initial_state=self.initial_state, wishes=wishes,
            target_copies=self.target_copies, model=self.model,
        )

    def certain_wishes(self) -> int:
        return deterministic_weapon_wishes_to_target(
            initial_state=self.initial_state, target_copies=self.target_copies,
            model=self.model,
        )


def convolve_completion_pmfs(
    first: Sequence[float], second: Sequence[float], max_wishes: int,
) -> tuple[float, ...]:
    """P(T1+T2=s), truncated at the requested horizon, including t=0 mass.

    Zero entries are skipped, but no positive probability is pruned. The
    straightforward finite convolution uses O(H1*H2) time and O(H1+H2) space.
    """

    _validate_count(max_wishes, "maximum wishes")
    horizon = min(max_wishes, len(first) + len(second) - 2)
    result = [0.0] * (horizon + 1)
    second_support = [(t, p) for t, p in enumerate(second) if p > 0]
    for t, first_probability in enumerate(first):
        if not first_probability or t > horizon:
            continue
        for u, second_probability in second_support:
            if t + u > horizon:
                break
            result[t + u] += first_probability * second_probability
    return tuple(result)


def _cdf(pmf: Sequence[float]) -> tuple[float, ...]:
    # Clamp only floating-point overshoot; 100% inverse planning uses the
    # structural bound rather than this rounded CDF.
    return tuple(min(1.0, max(0.0, value)) for value in accumulate(pmf))


@dataclass(frozen=True, slots=True)
class CombinedPlanningResult:
    total_wishes: int
    success_probability: float
    character_success_weapon_failure_probability: float
    character_failure_probability: float
    character_success_probability: float
    character_completion_time_distribution: tuple[float, ...]
    character_remaining_wishes_distribution: tuple[float, ...]
    conditional_character_remaining_wishes_distribution: tuple[float, ...]
    expected_remaining_wishes_after_character: float
    expected_remaining_wishes_given_character_success: float | None
    total_completion_time_distribution: tuple[float, ...]
    expected_total_completion_wish_given_success: float | None


@dataclass(frozen=True, slots=True)
class CombinedCompletionDistribution:
    """Reusable phase laws, combined PMF/CDF, and exact structural bound.

    Phase results are standalone target-aware laws, not a claim that both
    phases receive the full budget in the sequential plan. The second law is
    evaluated at N-t in the composition. Reports can reuse these calculations
    for any budget <= max_wishes (and beyond it if certainty was reached).
    """

    max_wishes: int
    certain_wishes: int
    character_result: TargetPlanningResult
    weapon_result: TargetPlanningResult
    weapon_success_probability_by_wish: tuple[float, ...]
    completion_time_distribution: tuple[float, ...]
    success_probability_by_budget: tuple[float, ...]

    def report(self, total_wishes: int) -> CombinedPlanningResult:
        _validate_count(total_wishes, "total wishes")
        if total_wishes > self.max_wishes and self.max_wishes < self.certain_wishes:
            raise ValueError("total wishes exceed the prepared horizon")

        def through_budget(pmf: tuple[float, ...]) -> tuple[float, ...]:
            truncated = pmf[:total_wishes + 1]
            return truncated + (0.0,) * (total_wishes + 1 - len(truncated))

        character_completion = through_budget(
            self.character_result.completion_time_distribution
        )
        character_success = min(1.0, fsum(character_completion))
        total_completion = through_budget(self.completion_time_distribution)
        # Evaluate the requested conditioning identity using the one cached
        # weapon CDF. If r exceeds its finite support, the final CDF applies.
        weapon_cdf = self.weapon_success_probability_by_wish
        both = min(character_success, fsum(
            p * weapon_cdf[min(total_wishes - t, len(weapon_cdf) - 1)]
            for t, p in enumerate(character_completion) if p
        ))
        if total_wishes >= self.certain_wishes:
            both = character_success = 1.0
        remaining = tuple(reversed(character_completion))
        remaining_moment = fsum(r * p for r, p in enumerate(remaining))
        conditional_remaining = (
            tuple(p / character_success for p in remaining)
            if character_success else (0.0,) * (total_wishes + 1)
        )
        completion_moment = fsum(t * p for t, p in enumerate(total_completion))
        return CombinedPlanningResult(
            total_wishes=total_wishes, success_probability=both,
            character_success_weapon_failure_probability=max(0.0, character_success - both),
            character_failure_probability=max(0.0, 1.0 - character_success),
            character_success_probability=character_success,
            character_completion_time_distribution=character_completion,
            character_remaining_wishes_distribution=remaining,
            conditional_character_remaining_wishes_distribution=conditional_remaining,
            # Remaining budget is defined as zero on character-failure paths.
            expected_remaining_wishes_after_character=remaining_moment,
            expected_remaining_wishes_given_character_success=(
                remaining_moment / character_success if character_success else None
            ),
            total_completion_time_distribution=total_completion,
            expected_total_completion_wish_given_success=(
                completion_moment / both if both else None
            ),
        )

    def minimum_wishes(self, desired_probability: float) -> int:
        _validate_probability(desired_probability)
        if desired_probability == 0:
            return 0
        if desired_probability == 1:
            return self.certain_wishes
        # First qualifying N is minimal even if the CDF contains plateaus.
        for wishes, probability in enumerate(self.success_probability_by_budget):
            if probability >= desired_probability:
                return wishes
        raise ValueError("confidence is not reached within the prepared horizon")

    def threshold_table(
        self, probabilities: Iterable[float] = (.50, .75, .90, .95, .99),
    ) -> tuple[ThresholdRequirement, ...]:
        return tuple(
            ThresholdRequirement(p, self.minimum_wishes(p)) for p in probabilities
        )


def deterministic_combined_wishes_to_target(
    *, character_goal: CharacterGoal, weapon_goal: WeaponGoal,
) -> int:
    """The longest positive-probability phase durations add sequentially."""

    return character_goal.certain_wishes() + weapon_goal.certain_wishes()


def _prepare_phase(
    goal: TargetGoal, max_wishes: int,
) -> tuple[int, TargetPlanningResult]:
    """Consume only the common goal/result contract, never a DP state layout."""

    bound = goal.certain_wishes()
    return bound, goal.calculate(min(max_wishes, bound))


def prepare_combined_distribution(
    *, character_goal: CharacterGoal, weapon_goal: WeaponGoal, max_wishes: int,
) -> CombinedCompletionDistribution:
    """Call each target-aware engine once, then compose their public PMFs."""

    _validate_count(max_wishes, "maximum wishes")
    # Beyond the phase's finite guarantee its PMF is zero: avoid generating
    # unnecessarily long banner trajectories for reports/inverse tables.
    character_bound, character = _prepare_phase(character_goal, max_wishes)
    weapon_bound, weapon = _prepare_phase(weapon_goal, max_wishes)
    pmf = convolve_completion_pmfs(
        character.completion_time_distribution,
        weapon.completion_time_distribution, max_wishes,
    )
    cdf = list(_cdf(pmf))
    bound = character_bound + weapon_bound
    if max_wishes >= bound:
        cdf[bound] = 1.0
    return CombinedCompletionDistribution(
        max_wishes, bound, character, weapon,
        _cdf(weapon.completion_time_distribution), pmf, tuple(cdf),
    )


def calculate_combined_plan(
    *, character_goal: CharacterGoal, weapon_goal: WeaponGoal, total_wishes: int,
) -> CombinedPlanningResult:
    return prepare_combined_distribution(
        character_goal=character_goal, weapon_goal=weapon_goal,
        max_wishes=total_wishes,
    ).report(total_wishes)


def minimum_combined_wishes_for_probability(
    *, character_goal: CharacterGoal, weapon_goal: WeaponGoal,
    desired_probability: float,
) -> int:
    _validate_probability(desired_probability)
    if desired_probability == 0:
        return 0
    bound = deterministic_combined_wishes_to_target(
        character_goal=character_goal, weapon_goal=weapon_goal,
    )
    if desired_probability == 1 or bound == 0:
        return bound
    return prepare_combined_distribution(
        character_goal=character_goal, weapon_goal=weapon_goal, max_wishes=bound,
    ).minimum_wishes(desired_probability)


def combined_threshold_table(
    *, character_goal: CharacterGoal, weapon_goal: WeaponGoal,
    probabilities: Iterable[float] = (.50, .75, .90, .95, .99),
) -> tuple[ThresholdRequirement, ...]:
    requested = tuple(probabilities)
    for probability in requested:
        _validate_probability(probability)
    bound = deterministic_combined_wishes_to_target(
        character_goal=character_goal, weapon_goal=weapon_goal,
    )
    if all(p in (0, 1) for p in requested):
        return tuple(ThresholdRequirement(p, bound if p else 0) for p in requested)
    return prepare_combined_distribution(
        character_goal=character_goal, weapon_goal=weapon_goal, max_wishes=bound,
    ).threshold_table(requested)
