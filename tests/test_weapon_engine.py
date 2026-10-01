import math
import unittest

from genshin_wish.weapon_engine import (
    calculate_weapon,
    calculate_weapon_target_plan,
    iter_weapon_target_success_probabilities,
)
from genshin_wish.weapon_model import (
    WeaponProbabilityModel,
    WeaponWishState,
    community_weapon_soft_pity_model,
    official_only_weapon_model,
)
from genshin_wish.weapon_simulation import simulate_weapon


class WeaponEngineTests(unittest.TestCase):
    def test_zero_target_completes_without_spending(self) -> None:
        result = calculate_weapon_target_plan(
            initial_state=WeaponWishState(), wishes=100, target_copies=0
        )
        self.assertEqual(result.success_probability, 1.0)
        self.assertEqual(result.completion_time_distribution[0], 1.0)
        self.assertEqual(result.remaining_wishes_distribution[100], 1.0)
        self.assertEqual(result.expected_wishes_consumed, 0.0)

    def test_absorbing_target_never_produces_extra_copies(self) -> None:
        result = calculate_weapon_target_plan(
            initial_state=WeaponWishState(),
            wishes=400,
            target_copies=2,
            model=community_weapon_soft_pity_model(),
        )
        self.assertEqual(set(result.copy_distribution), {0, 1, 2})
        self.assertTrue(all(state.copies < 2 for state in result.final_states))

    def test_mass_hitting_time_and_remaining_budget_invariants(self) -> None:
        budget = 180
        result = calculate_weapon_target_plan(
            initial_state=WeaponWishState(25, True, 1),
            wishes=budget,
            target_copies=2,
            model=official_only_weapon_model(),
        )
        self.assertTrue(all(math.isclose(m, 1.0, abs_tol=2e-14) for m in result.probability_mass_by_wish))
        self.assertTrue(math.isclose(sum(result.completion_time_distribution), result.success_probability, abs_tol=2e-14))
        self.assertTrue(math.isclose(result.success_probability + result.unfinished_probability, 1.0, abs_tol=2e-14))
        for t, probability in enumerate(result.completion_time_distribution):
            self.assertEqual(result.remaining_wishes_distribution[budget - t], probability)

    def test_target_success_equals_full_distribution_tail(self) -> None:
        state = WeaponWishState(31, False, 0)
        model = community_weapon_soft_pity_model()
        target = calculate_weapon_target_plan(
            initial_state=state, wishes=220, target_copies=2, model=model
        )
        full = calculate_weapon(
            initial_state=state, wishes=220, target_copies=2, model=model
        )
        self.assertAlmostEqual(target.success_probability, full.success_probability, delta=3e-14)

    def test_success_trajectory_is_non_decreasing(self) -> None:
        curve = [
            probability
            for _, probability in iter_weapon_target_success_probabilities(
                initial_state=WeaponWishState(),
                target_copies=3,
                max_wishes=480,
                model=official_only_weapon_model(),
            )
        ]
        self.assertTrue(all(a <= b + 1e-15 for a, b in zip(curve, curve[1:])))

    def test_always_five_star_fate_state_completes_on_first_wish(self) -> None:
        model = WeaponProbabilityModel((1.0,) * 80)
        result = calculate_weapon_target_plan(
            initial_state=WeaponWishState(0, True, 1),
            wishes=5,
            target_copies=1,
            model=model,
        )
        self.assertEqual(result.completion_time_distribution[1], 1.0)
        self.assertEqual(result.expected_wishes_consumed, 1.0)

    def test_seeded_monte_carlo_agrees_with_exact_dp(self) -> None:
        state = WeaponWishState(23, False, 0)
        model = community_weapon_soft_pity_model()
        exact = calculate_weapon_target_plan(
            initial_state=state, wishes=180, target_copies=2, model=model
        )
        sampled = simulate_weapon(
            initial_state=state,
            wishes=180,
            target_copies=2,
            trials=20_000,
            seed=731,
            model=model,
        )
        self.assertAlmostEqual(sampled.success_probability, exact.success_probability, delta=0.015)


if __name__ == "__main__":
    unittest.main()
