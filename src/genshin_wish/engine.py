"""Exact dynamic-programming calculations for Character Event Wishes."""

from __future__ import annotations

from collections.abc import Iterator
from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping

from .model import ProbabilityModel, WishState, official_only_model
from .results import TargetPlanningResult


_PITIES_PER_GUARANTEE_STATE = 90
_STATES_PER_COPY = 180


def _encode_state(pity: int, guaranteed: bool, copies: int) -> int:
    """Encode an internal state as one integer for compact DP indexing."""

    return copies * _STATES_PER_COPY + (90 if guaranteed else 0) + pity


def _decode_state(encoded: int) -> tuple[int, bool, int]:
    copies = encoded // _STATES_PER_COPY
    remainder = encoded - copies * _STATES_PER_COPY
    guaranteed = remainder >= _PITIES_PER_GUARANTEE_STATE
    pity = remainder - _PITIES_PER_GUARANTEE_STATE if guaranteed else remainder
    return pity, guaranteed, copies


@dataclass(frozen=True, slots=True)
class CalculationResult:
    wishes: int
    target_copies: int
    success_probability: float
    copy_distribution: Mapping[int, float]
    expected_copies: float
    expected_wishes_if_success_within_budget: float | None
    probability_mass_by_wish: tuple[float, ...]
    final_states: Mapping[WishState, float]


def _validate_inputs(wishes: int, target_copies: int) -> None:
    if wishes < 0:
        raise ValueError("wishes cannot be negative")
    if target_copies < 0:
        raise ValueError("target_copies cannot be negative")


def next_state_probabilities(
    state: WishState, model: ProbabilityModel
) -> tuple[tuple[WishState, float], ...]:
    """Enumerate every possible state after one wish.

    Zero-probability branches are omitted. With CR, distinct events may lead
    to the same state (e.g. CR and a normal C2 win both end at C1); callers
    must add branch masses rather than overwrite equal destinations.
    """

    five_star = model.five_star_probability(state.pity)
    if model.capturing_radiance is not None or state.cr_counter != 1:
        from .cr_engine import five_star_outcomes

        branches = []
        if five_star < 1:
            branches.append((WishState(state.pity + 1, state.guaranteed, state.copies, state.cr_counter), 1 - five_star))
        for featured, counter, probability in five_star_outcomes(model, state.cr_counter, state.guaranteed):
            if five_star * probability > 0:
                branches.append((WishState(0, not featured, state.copies + int(featured), counter), five_star * probability))
        return tuple(branches)
    branches: list[tuple[WishState, float]] = []

    if five_star < 1.0:
        branches.append(
            (WishState(state.pity + 1, state.guaranteed, state.copies), 1.0 - five_star)
        )

    if state.guaranteed:
        if five_star:
            branches.append((WishState(0, False, state.copies + 1), five_star))
    else:
        featured = five_star * model.featured_probability
        off_banner = five_star * (1.0 - model.featured_probability)
        if featured:
            branches.append((WishState(0, False, state.copies + 1), featured))
        if off_banner:
            branches.append((WishState(0, True, state.copies), off_banner))

    return tuple(branches)


def calculate(
    *,
    initial_state: WishState,
    wishes: int,
    target_copies: int,
    model: ProbabilityModel | None = None,
) -> CalculationResult:
    """Propagate the complete state distribution for exactly ``wishes`` wishes.

    Copy counts are left uncapped so ``copy_distribution`` is the full
    distribution, not just success/failure.  The hitting-time accumulator
    records the first wish on which the requested target is reached.
    """

    _validate_inputs(wishes, target_copies)
    model = model or official_only_model()
    if model.capturing_radiance is not None or initial_state.cr_counter != 1:
        from .cr_engine import calculate_counter_full
        return calculate_counter_full(initial_state=initial_state, wishes=wishes, target_copies=target_copies, model=model)
    # Full-distribution state becomes fairly dense at useful budgets. A flat
    # buffer avoids per-state dict entries while retaining every nonzero copy,
    # guarantee, and pity combination. Public outputs remain explicit states.
    initial_key = _encode_state(
        initial_state.pity, initial_state.guaranteed, initial_state.copies
    )
    states = [0.0] * ((initial_state.copies + 1) * _STATES_PER_COPY)
    states[initial_key] = 1.0
    mass_history = [1.0]
    success_by_first_wish: dict[int, float] = defaultdict(float)
    probabilities = model.five_star_probabilities
    featured_probability = model.featured_probability
    off_banner_probability = 1.0 - featured_probability

    already_successful = initial_state.copies >= target_copies
    if already_successful:
        success_by_first_wish[0] = 1.0

    for wish_number in range(1, wishes + 1):
        next_states = [0.0] * (
            (initial_state.copies + wish_number + 1) * _STATES_PER_COPY
        )
        for encoded, state_mass in enumerate(states):
            if state_mass == 0.0:
                continue
            copies = encoded // _STATES_PER_COPY
            remainder = encoded - copies * _STATES_PER_COPY
            guaranteed = remainder >= _PITIES_PER_GUARANTEE_STATE
            pity = remainder - _PITIES_PER_GUARANTEE_STATE if guaranteed else remainder
            q = probabilities[pity]
            if q < 1.0:
                next_states[encoded + 1] += state_mass * (1.0 - q)

            featured_key = (copies + 1) * _STATES_PER_COPY
            if guaranteed:
                featured_mass = state_mass * q
                next_states[featured_key] += featured_mass
            else:
                featured_mass = state_mass * q * featured_probability
                next_states[featured_key] += featured_mass
                off_banner_key = copies * _STATES_PER_COPY + 90
                next_states[off_banner_key] += state_mass * q * off_banner_probability

            if not already_successful and copies < target_copies <= copies + 1:
                success_by_first_wish[wish_number] += featured_mass
        states = next_states
        mass_history.append(sum(states))

    distribution: dict[int, float] = defaultdict(float)
    final_states: dict[WishState, float] = {}
    for encoded, probability in enumerate(states):
        if probability == 0.0:
            continue
        copies = encoded // _STATES_PER_COPY
        distribution[copies] += probability
        final_states[WishState(*_decode_state(encoded))] = probability

    success_probability = sum(
        probability for copies, probability in distribution.items() if copies >= target_copies
    )
    expected_copies = sum(copies * probability for copies, probability in distribution.items())
    if success_probability > 0.0:
        conditional_expected = sum(
            wish * probability for wish, probability in success_by_first_wish.items()
        ) / success_probability
    else:
        conditional_expected = None

    return CalculationResult(
        wishes=wishes,
        target_copies=target_copies,
        success_probability=success_probability,
        copy_distribution=dict(sorted(distribution.items())),
        expected_copies=expected_copies,
        expected_wishes_if_success_within_budget=conditional_expected,
        probability_mass_by_wish=tuple(mass_history),
        final_states=final_states,
    )


def _advance_target_states(
    active_states: Mapping[int, float],
    *,
    target_copies: int,
    probabilities: tuple[float, ...],
    featured_probability: float,
    off_banner_probability: float,
) -> tuple[dict[int, float], float]:
    """Advance unfinished states once and return newly completed mass."""

    next_active: dict[int, float] = {}
    next_get = next_active.get
    completed_mass = 0.0
    for encoded, state_mass in active_states.items():
        copies = encoded // _STATES_PER_COPY
        remainder = encoded - copies * _STATES_PER_COPY
        guaranteed = remainder >= _PITIES_PER_GUARANTEE_STATE
        pity = remainder - _PITIES_PER_GUARANTEE_STATE if guaranteed else remainder
        q = probabilities[pity]
        if q < 1.0:
            no_five_star_key = encoded + 1
            next_active[no_five_star_key] = next_get(no_five_star_key, 0.0) + (
                state_mass * (1.0 - q)
            )

        if guaranteed:
            featured_mass = state_mass * q
            off_banner_mass = 0.0
        else:
            featured_mass = state_mass * q * featured_probability
            off_banner_mass = state_mass * q * off_banner_probability

        if copies + 1 >= target_copies:
            completed_mass += featured_mass
        elif featured_mass:
            featured_key = (copies + 1) * _STATES_PER_COPY
            next_active[featured_key] = next_get(featured_key, 0.0) + featured_mass
        if off_banner_mass:
            off_banner_key = copies * _STATES_PER_COPY + 90
            next_active[off_banner_key] = next_get(off_banner_key, 0.0) + off_banner_mass
    return next_active, completed_mass


def calculate_target_plan(
    *,
    initial_state: WishState,
    wishes: int,
    target_copies: int,
    model: ProbabilityModel | None = None,
) -> TargetPlanningResult:
    """Calculate exact outcomes when wishing stops immediately at the target."""

    _validate_inputs(wishes, target_copies)
    model = model or official_only_model()
    if model.capturing_radiance is not None or initial_state.cr_counter != 1:
        from .cr_engine import calculate_counter_target
        return calculate_counter_target(initial_state=initial_state, wishes=wishes, target_copies=target_copies, model=model)
    completion = [0.0] * (wishes + 1)
    mass_history = [1.0]
    active_counts: list[int]

    if initial_state.copies >= target_copies:
        completion[0] = 1.0
        active_states: dict[int, float] = {}
        active_counts = [0]
        mass_history.extend([1.0] * wishes)
        active_counts.extend([0] * wishes)
    else:
        active_states = {
            _encode_state(
                initial_state.pity, initial_state.guaranteed, initial_state.copies
            ): 1.0
        }
        active_counts = [1]
        success_mass = 0.0
        probabilities = model.five_star_probabilities
        featured_probability = model.featured_probability
        off_banner_probability = 1.0 - featured_probability

        for wish_number in range(1, wishes + 1):
            if active_states:
                next_active, completed_mass = _advance_target_states(
                    active_states,
                    target_copies=target_copies,
                    probabilities=probabilities,
                    featured_probability=featured_probability,
                    off_banner_probability=off_banner_probability,
                )
                if not next_active:
                    # Structural certainty: assign any rounding residue to the
                    # completion wish so success + unfinished remains exactly 1.
                    completed_mass = 1.0 - success_mass
                completion[wish_number] = completed_mass
                success_mass += completed_mass
                active_states = next_active
            mass_history.append(success_mass + sum(active_states.values()))
            active_counts.append(len(active_states))

    success_probability = sum(completion)
    unfinished_probability = sum(active_states.values())
    copy_distribution = {copies: 0.0 for copies in range(target_copies + 1)}
    final_states: dict[WishState, float] = {}
    for encoded, probability in active_states.items():
        pity, guaranteed, copies = _decode_state(encoded)
        copy_distribution[copies] += probability
        final_states[WishState(pity, guaranteed, copies)] = probability
    copy_distribution[target_copies] += success_probability

    remaining = [0.0] * (wishes + 1)
    for completion_wish, probability in enumerate(completion):
        remaining[wishes - completion_wish] = probability
    if success_probability > 0.0:
        conditional_remaining = [
            probability / success_probability for probability in remaining
        ]
        conditional_expected_completion = sum(
            wish * probability for wish, probability in enumerate(completion)
        ) / success_probability
        conditional_expected_remaining = sum(
            remaining_wishes * probability
            for remaining_wishes, probability in enumerate(conditional_remaining)
        )
    else:
        conditional_remaining = [0.0] * (wishes + 1)
        conditional_expected_completion = None
        conditional_expected_remaining = None

    expected_copies = sum(
        copies * probability for copies, probability in copy_distribution.items()
    )
    expected_wishes_consumed = sum(
        wish * probability for wish, probability in enumerate(completion)
    ) + wishes * unfinished_probability

    return TargetPlanningResult(
        wishes=wishes,
        target_copies=target_copies,
        success_probability=success_probability,
        unfinished_probability=unfinished_probability,
        copy_distribution=copy_distribution,
        expected_copies=expected_copies,
        expected_wishes_if_success_within_budget=conditional_expected_completion,
        expected_wishes_consumed=expected_wishes_consumed,
        expected_remaining_wishes_if_success=conditional_expected_remaining,
        completion_time_distribution=tuple(completion),
        remaining_wishes_distribution=tuple(remaining),
        conditional_remaining_wishes_distribution=tuple(conditional_remaining),
        probability_mass_by_wish=tuple(mass_history),
        active_state_count_by_wish=tuple(active_counts),
        final_states=final_states,
    )


def iter_target_success_probabilities(
    *,
    initial_state: WishState,
    target_copies: int,
    model: ProbabilityModel | None = None,
    max_wishes: int,
) -> Iterator[tuple[int, float]]:
    """Yield exact cumulative target probability after each wish from 0 onward.

    States that have reached the target are absorbed into ``success_mass``.
    This uses the same transitions as :func:`calculate`, but avoids retaining
    copy counts beyond the target when a caller only needs a success curve.
    """

    _validate_inputs(max_wishes, target_copies)
    model = model or official_only_model()
    if model.capturing_radiance is not None or initial_state.cr_counter != 1:
        from .cr_engine import iter_counter_success
        yield from iter_counter_success(initial_state=initial_state, target_copies=target_copies, max_wishes=max_wishes, model=model)
        return
    if initial_state.copies >= target_copies:
        for wish_number in range(max_wishes + 1):
            yield wish_number, 1.0
        return

    active_states: dict[int, float] = {
        _encode_state(initial_state.pity, initial_state.guaranteed, initial_state.copies): 1.0
    }
    success_mass = 0.0
    probabilities = model.five_star_probabilities
    featured_probability = model.featured_probability
    off_banner_probability = 1.0 - featured_probability
    yield 0, 0.0

    for wish_number in range(1, max_wishes + 1):
        next_active, completed_mass = _advance_target_states(
            active_states,
            target_copies=target_copies,
            probabilities=probabilities,
            featured_probability=featured_probability,
            off_banner_probability=off_banner_probability,
        )
        success_mass += completed_mass
        active_states = next_active
        # Empty active state is structural certainty, not a tolerance-based
        # approximation to it. This matters for inverse planning at 100%.
        if not active_states:
            success_mass = 1.0
        yield wish_number, min(1.0, success_mass)


def expected_wishes_to_target(
    *,
    initial_state: WishState,
    target_copies: int,
    model: ProbabilityModel | None = None,
) -> float:
    """Return the unconditional expected wishes needed to reach the target.

    This is solved exactly (up to floating-point arithmetic) by backward
    recurrence.  At a fixed copy count, guaranteed expectations are computed
    first; that makes the non-guaranteed off-banner transition known too.
    """

    _validate_inputs(0, target_copies)
    if initial_state.copies >= target_copies:
        return 0.0
    model = model or official_only_model()

    # Maps copy count to arrays indexed by pity.
    if model.capturing_radiance is not None or initial_state.cr_counter != 1:
        from .cr_engine import completion_value
        return completion_value(initial_state=initial_state, target_copies=target_copies, model=model)
    guaranteed_values: dict[int, list[float]] = {}
    normal_values: dict[int, list[float]] = {}

    for copies in range(target_copies - 1, initial_state.copies - 1, -1):
        next_copy_normal = 0.0 if copies + 1 >= target_copies else normal_values[copies + 1][0]

        guaranteed = [0.0] * 90
        for pity in range(89, -1, -1):
            q = model.five_star_probability(pity)
            no_five_star = 0.0 if pity == 89 else (1.0 - q) * guaranteed[pity + 1]
            guaranteed[pity] = 1.0 + no_five_star + q * next_copy_normal
        guaranteed_values[copies] = guaranteed

        normal = [0.0] * 90
        for pity in range(89, -1, -1):
            q = model.five_star_probability(pity)
            no_five_star = 0.0 if pity == 89 else (1.0 - q) * normal[pity + 1]
            after_five_star = q * (
                model.featured_probability * next_copy_normal
                + (1.0 - model.featured_probability) * guaranteed[0]
            )
            normal[pity] = 1.0 + no_five_star + after_five_star
        normal_values[copies] = normal

    values = guaranteed_values if initial_state.guaranteed else normal_values
    return values[initial_state.copies][initial_state.pity]
