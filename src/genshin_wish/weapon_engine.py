"""Exact dynamic programming for the post-Version 5.0 Weapon Event Wish."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from .results import TargetPlanningResult
from .weapon_model import (
    WeaponProbabilityModel,
    WeaponWishState,
    official_only_weapon_model,
)


_PITIES = 80
_STATES_PER_FATE = 160
_STATES_PER_COPY = 320


def _encode_state(pity: int, promoted_guaranteed: bool, fate_point: int, copies: int) -> int:
    return (
        copies * _STATES_PER_COPY
        + fate_point * _STATES_PER_FATE
        + (80 if promoted_guaranteed else 0)
        + pity
    )


def _decode_state(encoded: int) -> tuple[int, bool, int, int]:
    copies = encoded // _STATES_PER_COPY
    remainder = encoded - copies * _STATES_PER_COPY
    fate_point = remainder // _STATES_PER_FATE
    remainder -= fate_point * _STATES_PER_FATE
    promoted_guaranteed = remainder >= _PITIES
    pity = remainder - _PITIES if promoted_guaranteed else remainder
    return pity, promoted_guaranteed, fate_point, copies


@dataclass(frozen=True, slots=True)
class WeaponCalculationResult:
    """Full-distribution result when all supplied wishes are spent."""

    wishes: int
    target_copies: int
    success_probability: float
    copy_distribution: Mapping[int, float]
    expected_copies: float
    expected_wishes_if_success_within_budget: float | None
    probability_mass_by_wish: tuple[float, ...]
    final_states: Mapping[WeaponWishState, float]


def _validate_inputs(wishes: int, target_copies: int) -> None:
    if wishes < 0:
        raise ValueError("wishes cannot be negative")
    if target_copies < 0:
        raise ValueError("target_copies cannot be negative")


def next_weapon_state_probabilities(
    state: WeaponWishState, model: WeaponProbabilityModel
) -> tuple[tuple[WeaponWishState, float], ...]:
    """Enumerate every nonzero one-wish branch from ``state``."""

    q = model.five_star_probability(state.pity)
    branches: list[tuple[WeaponWishState, float]] = []
    if q < 1.0:
        branches.append(
            (
                WeaponWishState(
                    state.pity + 1,
                    state.promoted_guaranteed,
                    state.fate_point,
                    state.copies,
                ),
                1.0 - q,
            )
        )

    if not q:
        return tuple(branches)

    if state.fate_point == model.fate_points_required:
        desired_probability = q
        other_promoted_probability = 0.0
        non_promoted_probability = 0.0
    elif state.promoted_guaranteed:
        desired_probability = q * model.desired_given_promoted_probability
        other_promoted_probability = q * (
            1.0 - model.desired_given_promoted_probability
        )
        non_promoted_probability = 0.0
    else:
        promoted = q * model.promoted_probability
        desired_probability = promoted * model.desired_given_promoted_probability
        other_promoted_probability = promoted * (
            1.0 - model.desired_given_promoted_probability
        )
        non_promoted_probability = q * (1.0 - model.promoted_probability)

    if desired_probability:
        branches.append(
            (WeaponWishState(0, False, 0, state.copies + 1), desired_probability)
        )
    if other_promoted_probability:
        branches.append(
            (WeaponWishState(0, False, 1, state.copies), other_promoted_probability)
        )
    if non_promoted_probability:
        branches.append(
            (WeaponWishState(0, True, 1, state.copies), non_promoted_probability)
        )
    return tuple(branches)


def _advance_target_states(
    active_states: Mapping[int, float],
    *,
    target_copies: int,
    model: WeaponProbabilityModel,
) -> tuple[dict[int, float], float]:
    next_active: dict[int, float] = {}
    next_get = next_active.get
    completed = 0.0
    for encoded, mass in active_states.items():
        pity, promoted_guaranteed, fate_point, copies = _decode_state(encoded)
        q = model.five_star_probabilities[pity]
        if q < 1.0:
            key = encoded + 1
            next_active[key] = next_get(key, 0.0) + mass * (1.0 - q)

        if fate_point:
            desired = mass * q
            other = non_promoted = 0.0
        elif promoted_guaranteed:
            desired = mass * q * model.desired_given_promoted_probability
            other = mass * q * (1.0 - model.desired_given_promoted_probability)
            non_promoted = 0.0
        else:
            promoted = mass * q * model.promoted_probability
            desired = promoted * model.desired_given_promoted_probability
            other = promoted * (1.0 - model.desired_given_promoted_probability)
            non_promoted = mass * q * (1.0 - model.promoted_probability)

        if copies + 1 >= target_copies:
            completed += desired
        elif desired:
            key = (copies + 1) * _STATES_PER_COPY
            next_active[key] = next_get(key, 0.0) + desired
        if other:
            key = copies * _STATES_PER_COPY + _STATES_PER_FATE
            next_active[key] = next_get(key, 0.0) + other
        if non_promoted:
            key = copies * _STATES_PER_COPY + _STATES_PER_FATE + _PITIES
            next_active[key] = next_get(key, 0.0) + non_promoted
    return next_active, completed


def calculate_weapon_target_plan(
    *,
    initial_state: WeaponWishState,
    wishes: int,
    target_copies: int,
    model: WeaponProbabilityModel | None = None,
) -> TargetPlanningResult[WeaponWishState]:
    """Calculate exact outcomes when weapon wishes stop at the target."""

    _validate_inputs(wishes, target_copies)
    model = model or official_only_weapon_model()
    completion = [0.0] * (wishes + 1)
    mass_history = [1.0]

    if initial_state.copies >= target_copies:
        completion[0] = 1.0
        active: dict[int, float] = {}
        active_counts = [0] * (wishes + 1)
        mass_history.extend([1.0] * wishes)
    else:
        active = {
            _encode_state(
                initial_state.pity,
                initial_state.promoted_guaranteed,
                initial_state.fate_point,
                initial_state.copies,
            ): 1.0
        }
        active_counts = [1]
        success_mass = 0.0
        for wish_number in range(1, wishes + 1):
            if active:
                active, newly_completed = _advance_target_states(
                    active, target_copies=target_copies, model=model
                )
                if not active:
                    newly_completed = 1.0 - success_mass
                completion[wish_number] = newly_completed
                success_mass += newly_completed
            mass_history.append(success_mass + sum(active.values()))
            active_counts.append(len(active))

    success_probability = sum(completion)
    unfinished_probability = sum(active.values())
    distribution = {copies: 0.0 for copies in range(target_copies + 1)}
    final_states: dict[WeaponWishState, float] = {}
    for encoded, probability in active.items():
        decoded = _decode_state(encoded)
        state = WeaponWishState(*decoded)
        distribution[state.copies] += probability
        final_states[state] = probability
    distribution[target_copies] += success_probability

    remaining = [0.0] * (wishes + 1)
    for completion_wish, probability in enumerate(completion):
        remaining[wishes - completion_wish] = probability
    if success_probability:
        conditional_remaining = [value / success_probability for value in remaining]
        conditional_completion = sum(
            wish * probability for wish, probability in enumerate(completion)
        ) / success_probability
        conditional_expected_remaining = sum(
            remaining_wishes * probability
            for remaining_wishes, probability in enumerate(conditional_remaining)
        )
    else:
        conditional_remaining = [0.0] * (wishes + 1)
        conditional_completion = None
        conditional_expected_remaining = None

    return TargetPlanningResult(
        wishes=wishes,
        target_copies=target_copies,
        success_probability=success_probability,
        unfinished_probability=unfinished_probability,
        copy_distribution=distribution,
        expected_copies=sum(c * p for c, p in distribution.items()),
        expected_wishes_if_success_within_budget=conditional_completion,
        expected_wishes_consumed=(
            sum(w * p for w, p in enumerate(completion))
            + wishes * unfinished_probability
        ),
        expected_remaining_wishes_if_success=conditional_expected_remaining,
        completion_time_distribution=tuple(completion),
        remaining_wishes_distribution=tuple(remaining),
        conditional_remaining_wishes_distribution=tuple(conditional_remaining),
        probability_mass_by_wish=tuple(mass_history),
        active_state_count_by_wish=tuple(active_counts),
        final_states=final_states,
    )


def calculate_weapon(
    *,
    initial_state: WeaponWishState,
    wishes: int,
    target_copies: int,
    model: WeaponProbabilityModel | None = None,
) -> WeaponCalculationResult:
    """Propagate the full distribution while spending exactly ``wishes``."""

    _validate_inputs(wishes, target_copies)
    model = model or official_only_weapon_model()
    states: dict[int, float] = {
        _encode_state(
            initial_state.pity,
            initial_state.promoted_guaranteed,
            initial_state.fate_point,
            initial_state.copies,
        ): 1.0
    }
    mass_history = [1.0]
    first_hit = [0.0] * (wishes + 1)
    if initial_state.copies >= target_copies:
        first_hit[0] = 1.0

    for wish_number in range(1, wishes + 1):
        next_states: dict[int, float] = {}
        next_get = next_states.get
        for encoded, mass in states.items():
            pity, promoted_guaranteed, fate_point, copies = _decode_state(encoded)
            q = model.five_star_probabilities[pity]
            if q < 1.0:
                key = encoded + 1
                next_states[key] = next_get(key, 0.0) + mass * (1.0 - q)
            if fate_point:
                desired = mass * q
                other = non_promoted = 0.0
            elif promoted_guaranteed:
                desired = mass * q * model.desired_given_promoted_probability
                other = mass * q * (1.0 - model.desired_given_promoted_probability)
                non_promoted = 0.0
            else:
                promoted = mass * q * model.promoted_probability
                desired = promoted * model.desired_given_promoted_probability
                other = promoted * (1.0 - model.desired_given_promoted_probability)
                non_promoted = mass * q * (1.0 - model.promoted_probability)

            if desired:
                desired_key = (copies + 1) * _STATES_PER_COPY
                next_states[desired_key] = next_get(desired_key, 0.0) + desired
            if other:
                key = copies * _STATES_PER_COPY + _STATES_PER_FATE
                next_states[key] = next_get(key, 0.0) + other
            if non_promoted:
                key = copies * _STATES_PER_COPY + _STATES_PER_FATE + _PITIES
                next_states[key] = next_get(key, 0.0) + non_promoted
            if copies < target_copies <= copies + 1:
                first_hit[wish_number] += desired
        states = next_states
        mass_history.append(sum(states.values()))

    distribution: dict[int, float] = defaultdict(float)
    final_states: dict[WeaponWishState, float] = {}
    for encoded, probability in states.items():
        decoded = _decode_state(encoded)
        state = WeaponWishState(*decoded)
        distribution[state.copies] += probability
        final_states[state] = probability
    success = sum(p for c, p in distribution.items() if c >= target_copies)
    conditional = (
        sum(w * p for w, p in enumerate(first_hit)) / success if success else None
    )
    return WeaponCalculationResult(
        wishes=wishes,
        target_copies=target_copies,
        success_probability=success,
        copy_distribution=dict(sorted(distribution.items())),
        expected_copies=sum(c * p for c, p in distribution.items()),
        expected_wishes_if_success_within_budget=conditional,
        probability_mass_by_wish=tuple(mass_history),
        final_states=final_states,
    )


def iter_weapon_target_success_probabilities(
    *,
    initial_state: WeaponWishState,
    target_copies: int,
    max_wishes: int,
    model: WeaponProbabilityModel | None = None,
) -> Iterator[tuple[int, float]]:
    """Yield the exact non-decreasing weapon success curve from wish zero."""

    _validate_inputs(max_wishes, target_copies)
    model = model or official_only_weapon_model()
    if initial_state.copies >= target_copies:
        for wish_number in range(max_wishes + 1):
            yield wish_number, 1.0
        return
    active = {
        _encode_state(
            initial_state.pity,
            initial_state.promoted_guaranteed,
            initial_state.fate_point,
            initial_state.copies,
        ): 1.0
    }
    success = 0.0
    yield 0, 0.0
    for wish_number in range(1, max_wishes + 1):
        active, completed = _advance_target_states(
            active, target_copies=target_copies, model=model
        )
        success += completed
        if not active:
            success = 1.0
        yield wish_number, min(1.0, success)
