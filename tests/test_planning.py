import unittest

from genshin_wish.engine import calculate, iter_target_success_probabilities
from genshin_wish.model import (
    ProbabilityModel,
    WishState,
    community_soft_pity_model,
    official_only_model,
)
from genshin_wish.planning import (
    deterministic_wishes_to_target,
    minimum_wishes_for_probability,
    threshold_table,
)


class InversePlanningTests(unittest.TestCase):
    def test_returns_minimum_after_long_probability_plateau(self) -> None:
        model = ProbabilityModel((0.0,) * 89 + (1.0,), featured_probability=1.0)
        state = WishState(0, False, 0)
        minimum = minimum_wishes_for_probability(
            initial_state=state,
            target_copies=1,
            desired_probability=0.5,
            model=model,
        )
        self.assertEqual(minimum, 90)
        self.assertEqual(
            calculate(
                initial_state=state, wishes=minimum - 1, target_copies=1, model=model
            ).success_probability,
            0.0,
        )

    def test_one_fewer_wish_does_not_qualify(self) -> None:
        model = community_soft_pity_model()
        state = WishState(37, False, 0)
        rows = threshold_table(
            initial_state=state,
            target_copies=2,
            probabilities=(0.50, 0.90, 0.99),
            model=model,
        )
        curve = dict(
            iter_target_success_probabilities(
                initial_state=state,
                target_copies=2,
                model=model,
                max_wishes=max(row.wishes for row in rows),
            )
        )
        for row in rows:
            self.assertGreaterEqual(curve[row.wishes], row.probability)
            self.assertLess(curve[row.wishes - 1], row.probability)

    def test_higher_confidence_never_requires_fewer_wishes(self) -> None:
        rows = threshold_table(
            initial_state=WishState(37),
            target_copies=2,
            probabilities=(0.0, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0),
            model=community_soft_pity_model(),
        )
        wishes = [row.wishes for row in rows]
        self.assertTrue(all(a <= b for a, b in zip(wishes, wishes[1:])))

    def test_higher_copy_target_never_requires_fewer_wishes(self) -> None:
        model = community_soft_pity_model()
        requirements = [
            minimum_wishes_for_probability(
                initial_state=WishState(37),
                target_copies=target,
                desired_probability=0.9,
                model=model,
            )
            for target in range(1, 5)
        ]
        self.assertTrue(all(a <= b for a, b in zip(requirements, requirements[1:])))

    def test_zero_target_and_zero_confidence_require_zero_wishes(self) -> None:
        model = official_only_model()
        self.assertEqual(
            minimum_wishes_for_probability(
                initial_state=WishState(89, True),
                target_copies=0,
                desired_probability=1.0,
                model=model,
            ),
            0,
        )
        self.assertEqual(
            minimum_wishes_for_probability(
                initial_state=WishState(),
                target_copies=100,
                desired_probability=0.0,
                model=model,
            ),
            0,
        )

    def test_100_percent_uses_finite_structural_guarantee(self) -> None:
        model = community_soft_pity_model()
        state = WishState(89, False, 0)
        self.assertEqual(
            deterministic_wishes_to_target(
                initial_state=state, target_copies=1, model=model
            ),
            91,
        )
        self.assertEqual(
            minimum_wishes_for_probability(
                initial_state=state,
                target_copies=1,
                desired_probability=1.0,
                model=model,
            ),
            91,
        )
        probability_before = calculate(
            initial_state=state, wishes=90, target_copies=1, model=model
        ).success_probability
        self.assertLess(probability_before, 1.0)

    def test_already_guaranteed_at_hard_pity_needs_one_wish(self) -> None:
        self.assertEqual(
            minimum_wishes_for_probability(
                initial_state=WishState(89, True),
                target_copies=1,
                desired_probability=1.0,
                model=official_only_model(),
            ),
            1,
        )

    def test_unusually_large_target_has_finite_bound_without_dp(self) -> None:
        self.assertEqual(
            minimum_wishes_for_probability(
                initial_state=WishState(),
                target_copies=100,
                desired_probability=1.0,
                model=official_only_model(),
            ),
            18_000,
        )

    def test_incremental_curve_matches_full_engine(self) -> None:
        state = WishState(37)
        model = community_soft_pity_model()
        curve = dict(
            iter_target_success_probabilities(
                initial_state=state, target_copies=2, model=model, max_wishes=240
            )
        )
        exact = calculate(
            initial_state=state, wishes=240, target_copies=2, model=model
        )
        self.assertAlmostEqual(curve[240], exact.success_probability, delta=1e-12)

    def test_probability_trajectory_is_non_decreasing(self) -> None:
        trajectory = [
            probability
            for _, probability in iter_target_success_probabilities(
                initial_state=WishState(0),
                target_copies=3,
                model=community_soft_pity_model(),
                max_wishes=500,
            )
        ]
        self.assertTrue(all(a <= b for a, b in zip(trajectory, trajectory[1:])))

    def test_invalid_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            minimum_wishes_for_probability(
                initial_state=WishState(), target_copies=-1, desired_probability=0.5
            )
        for confidence in (-0.01, 1.01):
            with self.assertRaises(ValueError):
                minimum_wishes_for_probability(
                    initial_state=WishState(),
                    target_copies=1,
                    desired_probability=confidence,
                )


if __name__ == "__main__":
    unittest.main()
