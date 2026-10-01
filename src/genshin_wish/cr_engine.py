"""Counter-aware exact character calculations using compiled local transitions.

Copy count is an outer dimension; the 720 local states are four counters,
two guarantee flags, and 90 pity values. One compiled kernel serves full DP,
absorbing DP, inverse planning, expectation, and structural certainty.
"""

from collections import defaultdict
from math import fsum

from .model import ProbabilityModel, WishState
from .results import TargetPlanningResult

LOCAL_STATES = 720


def encode(state: WishState) -> int:
    return state.copies * LOCAL_STATES + state.cr_counter * 180 + int(state.guaranteed) * 90 + state.pity


def decode(key: int) -> WishState:
    copies, local = divmod(key, LOCAL_STATES)
    counter, local = divmod(local, 180)
    guaranteed, pity = divmod(local, 90)
    return WishState(pity, bool(guaranteed), copies, counter)


def five_star_outcomes(model: ProbabilityModel, counter: int, guaranteed: bool):
    if guaranteed:
        return ((True, counter, 1.0),)
    if model.capturing_radiance is not None:
        return model.capturing_radiance.five_star_outcomes(counter, model.featured_probability)
    return tuple(
        (featured, counter, probability)
        for featured, probability in (
            (True, model.featured_probability), (False, 1 - model.featured_probability)
        ) if probability > 0
    )


def kernel(model: ProbabilityModel):
    """Compile local destinations once; offsets include copy increments."""
    transitions = []
    for local in range(LOCAL_STATES):
        state = decode(local)
        q = model.five_star_probabilities[state.pity]
        branches = []
        if q < 1:
            branches.append((local + 1, False, 1 - q))
        for featured, counter, probability in five_star_outcomes(
            model, state.cr_counter, state.guaranteed
        ):
            if q * probability > 0:
                destination = counter * 180 + (0 if featured else 90)
                branches.append((destination + (LOCAL_STATES if featured else 0), featured, q * probability))
        transitions.append(tuple(branches))
    return transitions


def advance(states, transitions, target=None):
    next_states = {}
    get = next_states.get
    completed = 0.0
    for key, mass in states.items():
        copies, local = divmod(key, LOCAL_STATES)
        base = copies * LOCAL_STATES
        for destination, featured, probability in transitions[local]:
            branch_mass = mass * probability
            if target is not None and featured and copies + 1 >= target:
                completed += branch_mass
            else:
                next_key = base + destination
                next_states[next_key] = get(next_key, 0.0) + branch_mass
    return next_states, completed


def calculate_counter_target(*, initial_state, wishes, target_copies, model):
    transitions = kernel(model)
    completion = [0.0] * (wishes + 1)
    already_complete = initial_state.copies >= target_copies
    completion[0] = float(already_complete)
    active = {} if already_complete else {encode(initial_state): 1.0}
    success = completion[0]
    masses, counts = [1.0], [len(active)]
    for t in range(1, wishes + 1):
        if active:
            active, completed = advance(active, transitions, target_copies)
            if not active:
                completed = max(0.0, 1 - success)
            completion[t] = completed
            success += completed
        masses.append(success + fsum(active.values()))
        counts.append(len(active))
    success = fsum(completion)
    unfinished = fsum(active.values())
    distribution = {c: 0.0 for c in range(target_copies + 1)}
    final_states = {decode(key): mass for key, mass in active.items()}
    for state, mass in final_states.items():
        distribution[state.copies] += mass
    distribution[target_copies] += success
    remaining = tuple(reversed(completion))
    conditional_remaining = tuple(p / success for p in remaining) if success else (0.0,) * (wishes + 1)
    completion_moment = fsum(t * p for t, p in enumerate(completion))
    return TargetPlanningResult(
        wishes=wishes, target_copies=target_copies,
        success_probability=success, unfinished_probability=unfinished,
        copy_distribution=distribution,
        expected_copies=fsum(c * p for c, p in distribution.items()),
        expected_wishes_if_success_within_budget=completion_moment / success if success else None,
        expected_wishes_consumed=completion_moment + wishes * unfinished,
        expected_remaining_wishes_if_success=(wishes - completion_moment / success) if success else None,
        completion_time_distribution=tuple(completion),
        remaining_wishes_distribution=remaining,
        conditional_remaining_wishes_distribution=conditional_remaining,
        probability_mass_by_wish=tuple(masses),
        active_state_count_by_wish=tuple(counts), final_states=final_states,
    )


def calculate_counter_full(*, initial_state, wishes, target_copies, model):
    # Imported locally to preserve the existing public CalculationResult class.
    from .engine import CalculationResult

    transitions = kernel(model)
    # Full distributions become dense. A flat buffer avoids a dictionary
    # allocation/hash operation per branch while keeping every copy count.
    states = [0.0] * ((initial_state.copies + 1) * LOCAL_STATES)
    states[encode(initial_state)] = 1.0
    masses = [1.0]
    moment = 0.0
    for t in range(1, wishes + 1):
        next_states = [0.0] * ((initial_state.copies + t + 1) * LOCAL_STATES)
        crossing = 0.0
        for key, mass in enumerate(states):
            if not mass:
                continue
            copies, local = divmod(key, LOCAL_STATES)
            base = copies * LOCAL_STATES
            for destination, featured, probability in transitions[local]:
                branch_mass = mass * probability
                next_states[base + destination] += branch_mass
                if featured and copies == target_copies - 1:
                    crossing += branch_mass
        moment += t * crossing
        states = next_states
        masses.append(fsum(states))
    distribution = defaultdict(float)
    final_states = {}
    for key, mass in enumerate(states):
        if not mass:
            continue
        state = decode(key)
        distribution[state.copies] += mass
        final_states[state] = mass
    success = fsum(p for c, p in distribution.items() if c >= target_copies)
    return CalculationResult(
        wishes, target_copies, success, dict(sorted(distribution.items())),
        fsum(c * p for c, p in distribution.items()),
        moment / success if success else None, tuple(masses), final_states,
    )


def iter_counter_success(*, initial_state, target_copies, max_wishes, model):
    transitions = kernel(model)
    complete = initial_state.copies >= target_copies
    active = {} if complete else {encode(initial_state): 1.0}
    success = float(complete)
    yield 0, success
    for t in range(1, max_wishes + 1):
        active, completed = advance(active, transitions, target_copies)
        success = min(1.0, success + completed) if active else 1.0
        yield t, success


def completion_value(*, initial_state, target_copies, model, worst_case=False):
    """Backward recurrence for E[T] or the longest positive-probability path.

    At each copy count, all guaranteed states are solved first: a guaranteed
    result advances copies without changing the counter. Non-guaranteed
    losses can then reference those values without cyclic dependencies.
    Only the next copy's 720 values are retained, so memory is O(720).
    """
    if initial_state.copies >= target_copies:
        return 0 if worst_case else 0.0
    next_copy = [0.0] * LOCAL_STATES
    for copies in range(target_copies - 1, initial_state.copies - 1, -1):
        values = [0.0] * LOCAL_STATES
        for guaranteed in (True, False):
            for counter in range(4):
                outcomes = five_star_outcomes(model, counter, guaranteed)
                for pity in range(89, -1, -1):
                    local = counter * 180 + int(guaranteed) * 90 + pity
                    q = model.five_star_probabilities[pity]
                    branches = []
                    if q < 1:
                        branches.append((1 - q, values[local + 1]))
                    for featured, new_counter, probability in outcomes:
                        if q * probability > 0:
                            destination = new_counter * 180 + (0 if featured else 90)
                            after = next_copy[destination] if featured else values[destination]
                            branches.append((q * probability, after))
                    values[local] = 1 + (
                        max(after for _, after in branches) if worst_case
                        else fsum(p * after for p, after in branches)
                    )
        next_copy = values
    value = next_copy[encode(initial_state) % LOCAL_STATES]
    return int(value) if worst_case else value
