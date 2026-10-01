import unittest

from genshin_wish.weapon_engine import iter_weapon_target_success_probabilities
from genshin_wish.weapon_model import (
    WeaponWishState,
    community_weapon_soft_pity_model,
    official_only_weapon_model,
)
from genshin_wish.weapon_planning import (
    deterministic_weapon_wishes_to_target,
    expected_weapon_wishes_to_target,
    minimum_weapon_wishes_for_probability,
    weapon_threshold_table,
)


class WeaponInversePlanningTests(unittest.TestCase):
    def test_backward_expectation_matches_completion_distribution(self) -> None:
        from genshin_wish.weapon_engine import calculate_weapon_target_plan

        state = WeaponWishState(27, True, 0)
        model = official_only_weapon_model()
        bound = deterministic_weapon_wishes_to_target(
            initial_state=state, target_copies=2, model=model
        )
        result = calculate_weapon_target_plan(
            initial_state=state, wishes=bound, target_copies=2, model=model
        )
        from_pmf = sum(
            wish * probability
            for wish, probability in enumerate(result.completion_time_distribution)
        )
        self.assertAlmostEqual(
            expected_weapon_wishes_to_target(
                initial_state=state, target_copies=2, model=model
            ),
            from_pmf,
            delta=1e-10,
        )

    def test_current_rule_has_finite_160_wish_fresh_guarantee(self) -> None:
        model = official_only_weapon_model()
        self.assertEqual(
            deterministic_weapon_wishes_to_target(
                initial_state=WeaponWishState(), target_copies=1, model=model
            ),
            160,
        )
        curve = dict(
            iter_weapon_target_success_probabilities(
                initial_state=WeaponWishState(),
                target_copies=1,
                max_wishes=160,
                model=model,
            )
        )
        self.assertLess(curve[159], 1.0)
        self.assertEqual(curve[160], 1.0)
        self.assertEqual(
            minimum_weapon_wishes_for_probability(
                initial_state=WeaponWishState(),
                target_copies=1,
                desired_probability=1.0,
                model=model,
            ),
            160,
        )

    def test_fate_at_hard_pity_needs_one_wish(self) -> None:
        self.assertEqual(
            minimum_weapon_wishes_for_probability(
                initial_state=WeaponWishState(79, True, 1),
                target_copies=1,
                desired_probability=1.0,
            ),
            1,
        )

    def test_thresholds_are_minimum_and_ordered(self) -> None:
        state = WeaponWishState(22, False, 0)
        model = community_weapon_soft_pity_model()
        rows = weapon_threshold_table(
            initial_state=state,
            target_copies=2,
            probabilities=(0.0, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0),
            model=model,
        )
        self.assertTrue(all(a.wishes <= b.wishes for a, b in zip(rows, rows[1:])))
        curve = dict(
            iter_weapon_target_success_probabilities(
                initial_state=state,
                target_copies=2,
                max_wishes=max(row.wishes for row in rows),
                model=model,
            )
        )
        for row in rows[1:-1]:
            self.assertGreaterEqual(curve[row.wishes], row.probability)
            self.assertLess(curve[row.wishes - 1], row.probability)

    def test_higher_target_never_needs_fewer_wishes(self) -> None:
        model = community_weapon_soft_pity_model()
        values = [
            minimum_weapon_wishes_for_probability(
                initial_state=WeaponWishState(),
                target_copies=target,
                desired_probability=0.9,
                model=model,
            )
            for target in range(1, 5)
        ]
        self.assertTrue(all(a <= b for a, b in zip(values, values[1:])))

    def test_zero_target_and_zero_confidence_need_zero(self) -> None:
        self.assertEqual(
            minimum_weapon_wishes_for_probability(
                initial_state=WeaponWishState(), target_copies=0, desired_probability=1.0
            ),
            0,
        )
        self.assertEqual(
            minimum_weapon_wishes_for_probability(
                initial_state=WeaponWishState(), target_copies=99, desired_probability=0.0
            ),
            0,
        )

    def test_invalid_inputs_are_rejected(self) -> None:
        for probability in (-0.1, 1.1):
            with self.assertRaises(ValueError):
                minimum_weapon_wishes_for_probability(
                    initial_state=WeaponWishState(),
                    target_copies=1,
                    desired_probability=probability,
                )


if __name__ == "__main__":
    unittest.main()
