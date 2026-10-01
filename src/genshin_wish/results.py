"""Planning result types shared by character and weapon engines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Mapping, TypeVar


StateT = TypeVar("StateT")


@dataclass(frozen=True, slots=True)
class TargetPlanningResult(Generic[StateT]):
    """Exact finite-budget result under a stop-immediately-at-target policy.

    ``completion_time_distribution[t]`` is P(T=t). The remaining-wish tuples
    are indexed by remaining wishes. The unconditional form is joint with
    success; the conditional form divides by total success probability.
    ``final_states`` contains unfinished states only.

    Keeping this result independent of either banner's internal state lets a
    future composition layer consume character and weapon plans uniformly.
    """

    wishes: int
    target_copies: int
    success_probability: float
    unfinished_probability: float
    copy_distribution: Mapping[int, float]
    expected_copies: float
    expected_wishes_if_success_within_budget: float | None
    expected_wishes_consumed: float
    expected_remaining_wishes_if_success: float | None
    completion_time_distribution: tuple[float, ...]
    remaining_wishes_distribution: tuple[float, ...]
    conditional_remaining_wishes_distribution: tuple[float, ...]
    probability_mass_by_wish: tuple[float, ...]
    active_state_count_by_wish: tuple[int, ...]
    final_states: Mapping[StateT, float]
