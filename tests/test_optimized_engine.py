import math
import unittest
from collections import defaultdict

from genshin_wish.engine import calculate, next_state_probabilities
from genshin_wish.model import WishState, community_soft_pity_model


def reference_dp(
    *, initial_state: WishState, wishes: int, target_copies: int
) -> tuple[dict[int, float], float, float, float | None]:
    """Small, readable WishState-keyed reference used only for equivalence tests."""

    model = community_soft_pity_model()
    states: dict[WishState, float] = {initial_state: 1.0}
    first_hit: dict[int, float] = defaultdict(float)
    for wish_number in range(1, wishes + 1):
        next_states: dict[WishState, float] = defaultdict(float)
        for state, state_mass in states.items():
            for next_state, transition_probability in next_state_probabilities(state, model):
                branch_mass = state_mass * transition_probability
                next_states[next_state] += branch_mass
                if state.copies < target_copies <= next_state.copies:
                    first_hit[wish_number] += branch_mass
        states = dict(next_states)

    distribution: dict[int, float] = defaultdict(float)
    for state, probability in states.items():
        distribution[state.copies] += probability
    distribution = dict(sorted(distribution.items()))
    success = math.fsum(
        probability for copies, probability in distribution.items() if copies >= target_copies
    )
    expected_copies = math.fsum(
        copies * probability for copies, probability in distribution.items()
    )
    conditional = (
        math.fsum(wish * probability for wish, probability in first_hit.items()) / success
        if success > 0.0
        else None
    )
    return distribution, success, expected_copies, conditional


class OptimizedEngineEquivalenceTests(unittest.TestCase):
    def test_integer_state_dp_agrees_with_reference_dp(self) -> None:
        state = WishState(37, False, 0)
        model = community_soft_pity_model()
        optimized = calculate(
            initial_state=state, wishes=100, target_copies=2, model=model
        )
        distribution, success, expected_copies, conditional = reference_dp(
            initial_state=state, wishes=100, target_copies=2
        )

        self.assertEqual(optimized.copy_distribution.keys(), distribution.keys())
        for copies in distribution:
            self.assertAlmostEqual(
                optimized.copy_distribution[copies], distribution[copies], delta=1e-15
            )
        self.assertAlmostEqual(optimized.success_probability, success, delta=1e-15)
        self.assertAlmostEqual(optimized.expected_copies, expected_copies, delta=1e-15)
        self.assertAlmostEqual(
            optimized.expected_wishes_if_success_within_budget,
            conditional,
            delta=1e-12,
        )
        self.assertTrue(
            all(math.isclose(mass, 1.0, abs_tol=1e-12) for mass in optimized.probability_mass_by_wish)
        )


if __name__ == "__main__":
    unittest.main()
