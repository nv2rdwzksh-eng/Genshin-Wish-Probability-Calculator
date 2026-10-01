import math
import unittest

from genshin_wish.engine import calculate, expected_wishes_to_target
from genshin_wish.model import ProbabilityModel, WishState, official_only_model
from genshin_wish.simulation import simulate


class EngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = official_only_model()

    def test_zero_wishes_cannot_add_copies(self) -> None:
        result = calculate(
            initial_state=WishState(37, False, 0),
            wishes=0,
            target_copies=1,
            model=self.model,
        )
        self.assertEqual(result.success_probability, 0.0)
        self.assertEqual(result.copy_distribution, {0: 1.0})

    def test_probability_bounds_and_mass_conservation(self) -> None:
        result = calculate(
            initial_state=WishState(37, False, 0),
            wishes=240,
            target_copies=2,
            model=self.model,
        )
        self.assertTrue(0.0 <= result.success_probability <= 1.0)
        self.assertTrue(all(0.0 <= p <= 1.0 for p in result.copy_distribution.values()))
        self.assertTrue(all(math.isclose(mass, 1.0, abs_tol=1e-12) for mass in result.probability_mass_by_wish))
        self.assertTrue(math.isclose(sum(result.copy_distribution.values()), 1.0, abs_tol=1e-12))

    def test_more_wishes_never_decreases_success_probability(self) -> None:
        probabilities = [
            calculate(
                initial_state=WishState(37, False, 0),
                wishes=wishes,
                target_copies=2,
                model=self.model,
            ).success_probability
            for wishes in range(0, 251, 50)
        ]
        self.assertTrue(all(a <= b + 1e-15 for a, b in zip(probabilities, probabilities[1:])))

    def test_guaranteed_hard_pity_succeeds_in_one_wish(self) -> None:
        result = calculate(
            initial_state=WishState(89, True, 0), wishes=1, target_copies=1, model=self.model
        )
        self.assertEqual(result.success_probability, 1.0)
        self.assertEqual(result.expected_wishes_if_success_within_budget, 1.0)

    def test_expected_wishes_with_always_five_star_model(self) -> None:
        model = ProbabilityModel((1.0,) * 90, featured_probability=0.5)
        # Each copy needs one 5-star on a win or two on a loss: E = 1.5.
        self.assertEqual(
            expected_wishes_to_target(
                initial_state=WishState(), target_copies=2, model=model
            ),
            3.0,
        )

    def test_monte_carlo_agrees_with_exact_result(self) -> None:
        state = WishState(37, False, 0)
        exact = calculate(
            initial_state=state, wishes=240, target_copies=2, model=self.model
        )
        sampled = simulate(
            initial_state=state,
            wishes=240,
            target_copies=2,
            trials=20_000,
            seed=12345,
            model=self.model,
        )
        self.assertAlmostEqual(sampled.success_probability, exact.success_probability, delta=0.015)


if __name__ == "__main__":
    unittest.main()
