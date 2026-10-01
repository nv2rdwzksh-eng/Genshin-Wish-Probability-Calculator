import math
import unittest

from genshin_wish.cli import format_full_distribution_report, format_planning_report
from genshin_wish.engine import calculate, calculate_target_plan
from genshin_wish.model import ProbabilityModel, WishState, community_soft_pity_model
from genshin_wish.planning import calculate_plan


class TargetAwarePlanningTests(unittest.TestCase):
    def test_planning_never_produces_copies_above_target(self) -> None:
        result = calculate_target_plan(
            initial_state=WishState(),
            wishes=320,
            target_copies=3,
            model=community_soft_pity_model(),
        )
        self.assertEqual(set(result.copy_distribution), {0, 1, 2, 3})
        self.assertTrue(all(state.copies < 3 for state in result.final_states))

    def test_target_completion_stops_consuming_wishes(self) -> None:
        model = ProbabilityModel((1.0,) * 90, featured_probability=1.0)
        result = calculate_target_plan(
            initial_state=WishState(), wishes=10, target_copies=1, model=model
        )
        self.assertEqual(result.completion_time_distribution[1], 1.0)
        self.assertEqual(result.remaining_wishes_distribution[9], 1.0)
        self.assertEqual(result.expected_wishes_consumed, 1.0)
        self.assertEqual(result.active_state_count_by_wish[1:], (0,) * 10)

    def test_success_matches_full_distribution_tail(self) -> None:
        state = WishState(37, False)
        model = community_soft_pity_model()
        planning = calculate_target_plan(
            initial_state=state, wishes=240, target_copies=2, model=model
        )
        full = calculate(
            initial_state=state, wishes=240, target_copies=2, model=model
        )
        self.assertAlmostEqual(
            planning.success_probability, full.success_probability, delta=2e-15
        )

    def test_hitting_time_sums_to_success(self) -> None:
        result = calculate_target_plan(
            initial_state=WishState(),
            wishes=320,
            target_copies=3,
            model=community_soft_pity_model(),
        )
        self.assertTrue(
            math.isclose(
                sum(result.completion_time_distribution),
                result.success_probability,
                abs_tol=1e-14,
            )
        )

    def test_remaining_wishes_are_the_image_of_completion_time(self) -> None:
        budget = 200
        result = calculate_target_plan(
            initial_state=WishState(),
            wishes=budget,
            target_copies=2,
            model=community_soft_pity_model(),
        )
        for completion_wish, probability in enumerate(
            result.completion_time_distribution
        ):
            remaining = budget - completion_wish
            self.assertEqual(result.remaining_wishes_distribution[remaining], probability)
            if probability > 0.0:
                self.assertEqual(completion_wish + remaining, budget)
        self.assertTrue(
            math.isclose(
                sum(result.conditional_remaining_wishes_distribution),
                1.0,
                abs_tol=1e-14,
            )
        )

    def test_zero_target_completes_at_wish_zero(self) -> None:
        result = calculate_target_plan(
            initial_state=WishState(), wishes=50, target_copies=0
        )
        self.assertEqual(result.success_probability, 1.0)
        self.assertEqual(result.completion_time_distribution[0], 1.0)
        self.assertEqual(result.remaining_wishes_distribution[50], 1.0)
        self.assertEqual(result.expected_wishes_consumed, 0.0)

    def test_too_small_budget_remains_unsuccessful(self) -> None:
        model = ProbabilityModel((0.0,) * 89 + (1.0,), featured_probability=1.0)
        result = calculate_target_plan(
            initial_state=WishState(), wishes=89, target_copies=1, model=model
        )
        self.assertEqual(result.success_probability, 0.0)
        self.assertEqual(result.unfinished_probability, 1.0)
        self.assertEqual(result.copy_distribution, {0: 1.0, 1: 0.0})

    def test_success_plus_unfinished_mass_is_conserved(self) -> None:
        result = calculate_target_plan(
            initial_state=WishState(37),
            wishes=240,
            target_copies=2,
            model=community_soft_pity_model(),
        )
        self.assertTrue(
            math.isclose(
                result.success_probability + result.unfinished_probability,
                1.0,
                abs_tol=2e-14,
            )
        )
        self.assertTrue(
            all(math.isclose(mass, 1.0, abs_tol=2e-14) for mass in result.probability_mass_by_wish)
        )

    def test_target_aware_report_sums_to_one_and_always_shows_target(self) -> None:
        model = community_soft_pity_model()
        plan = calculate_plan(
            initial_state=WishState(), wishes=1, target_copies=3, model=model
        )
        report = format_planning_report(plan, model=model)
        self.assertTrue(math.isclose(sum(plan.calculation.copy_distribution.values()), 1.0))
        self.assertIn("Target reached (3 copies; stopped):", report)
        self.assertNotIn("Exactly 4", report)

    def test_full_analysis_still_allows_higher_copy_counts(self) -> None:
        model = ProbabilityModel((1.0,) * 90, featured_probability=1.0)
        planning = calculate_target_plan(
            initial_state=WishState(), wishes=3, target_copies=1, model=model
        )
        full = calculate(
            initial_state=WishState(), wishes=3, target_copies=1, model=model
        )
        self.assertEqual(planning.copy_distribution, {0: 0.0, 1: 1.0})
        self.assertEqual(full.copy_distribution, {3: 1.0})
        report = format_full_distribution_report(full, model=model)
        self.assertIn("Exactly 3: 100.00000000%", report)


if __name__ == "__main__":
    unittest.main()
