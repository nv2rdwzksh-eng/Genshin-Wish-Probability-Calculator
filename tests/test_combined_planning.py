"""Independent tiny-path enumeration and composition invariants."""

import unittest
from math import fsum
from unittest.mock import patch

from genshin_wish import (
    CharacterGoal, WeaponGoal, ProbabilityModel, WeaponProbabilityModel,
    WishState, WeaponWishState, with_capturing_radiance,
    community_soft_pity_model, community_weapon_soft_pity_model,
    calculate_combined_plan, prepare_combined_distribution,
    combined_threshold_table, minimum_combined_wishes_for_probability,
    deterministic_combined_wishes_to_target,
)
from genshin_wish.engine import calculate_target_plan
from genshin_wish.weapon_engine import calculate_weapon_target_plan


def enumerate_paths(character, weapon, budget):
    """Brute-force each pull path, without production transitions/convolution.

    This deliberately follows phases directly and is used only at tiny budgets.
    It reads configured rates but implements the outcome rules independently.
    """
    outcomes = [0.0, 0.0, 0.0]  # both, character-only, character failed
    character_pmf = [0.0] * (budget + 1)
    total_pmf = [0.0] * (budget + 1)

    def weapon_paths(state, elapsed, mass):
        if state.copies >= weapon.target_copies:
            outcomes[0] += mass
            total_pmf[elapsed] += mass
            return
        if elapsed == budget:
            outcomes[1] += mass
            return
        q = weapon.model.five_star_probabilities[state.pity]
        if q < 1:
            weapon_paths(WeaponWishState(state.pity + 1, state.promoted_guaranteed, state.fate_point, state.copies), elapsed + 1, mass * (1 - q))
        if state.fate_point:
            desired, other, loss = 1.0, 0.0, 0.0
        else:
            promoted = 1.0 if state.promoted_guaranteed else weapon.model.promoted_probability
            desired = promoted * weapon.model.desired_given_promoted_probability
            other = promoted * (1 - weapon.model.desired_given_promoted_probability)
            loss = 1 - promoted
        for new_state, p in (
            (WeaponWishState(0, False, 0, state.copies + 1), desired),
            (WeaponWishState(0, False, 1, state.copies), other),
            (WeaponWishState(0, True, 1, state.copies), loss),
        ):
            if q * p:
                weapon_paths(new_state, elapsed + 1, mass * q * p)

    def character_paths(state, elapsed, mass):
        if state.copies >= character.target_copies:
            character_pmf[elapsed] += mass
            weapon_paths(weapon.initial_state, elapsed, mass)
            return
        if elapsed == budget:
            outcomes[2] += mass
            return
        q = character.model.five_star_probabilities[state.pity]
        c = state.cr_counter
        if q < 1:
            character_paths(WishState(state.pity + 1, state.guaranteed, state.copies, c), elapsed + 1, mass * (1 - q))
        if state.guaranteed:
            branches = [(True, c, 1.0)]
        else:
            cr = character.model.capturing_radiance
            r = cr.probabilities[c] if cr else 0.0
            f = character.model.featured_probability
            branches = [
                (True, cr.reset_counter if cr else c, r),
                (True, cr.win_counters[c] if cr else c, (1 - r) * f),
                (False, cr.loss_counters[c] if cr else c, (1 - r) * (1 - f)),
            ]
        for featured, counter, p in branches:
            if q * p:
                character_paths(WishState(0, not featured, state.copies + int(featured), counter), elapsed + 1, mass * q * p)

    character_paths(character.initial_state, 0, 1.0)
    return outcomes, character_pmf, total_pmf


class CombinedPlanningTests(unittest.TestCase):
    def setUp(self):
        self.character_model = ProbabilityModel((.4,) * 89 + (1.0,))
        self.weapon_model = WeaponProbabilityModel((.3,) * 79 + (1.0,))

    def goals(self, character_state=None, weapon_state=None, character_target=1, weapon_target=1, cr=False):
        return (
            CharacterGoal(character_state or WishState(), character_target,
                          with_capturing_radiance(self.character_model) if cr else self.character_model),
            WeaponGoal(weapon_state or WeaponWishState(), weapon_target, self.weapon_model),
        )

    def test_independent_tiny_path_reference_for_all_cr_counters(self):
        for counter in range(4):
            character, weapon = self.goals(
                WishState(88, False, 0, counter), WeaponWishState(78, True, 0),
                character_target=2, cr=True,
            )
            for budget in range(6):
                with self.subTest(counter=counter, budget=budget):
                    reference, character_pmf, total_pmf = enumerate_paths(character, weapon, budget)
                    result = calculate_combined_plan(character_goal=character, weapon_goal=weapon, total_wishes=budget)
                    actual = (result.success_probability, result.character_success_weapon_failure_probability, result.character_failure_probability)
                    for a, b in zip(actual, reference):
                        self.assertAlmostEqual(a, b, delta=3e-14)
                    for a, b in zip(result.character_completion_time_distribution, character_pmf):
                        self.assertAlmostEqual(a, b, delta=3e-14)
                    for a, b in zip(result.total_completion_time_distribution, total_pmf):
                        self.assertAlmostEqual(a, b, delta=3e-14)

    def test_mass_conservation_and_conditional_moments(self):
        character, weapon = self.goals(cr=True)
        result = calculate_combined_plan(character_goal=character, weapon_goal=weapon, total_wishes=12)
        self.assertAlmostEqual(fsum((result.success_probability, result.character_success_weapon_failure_probability, result.character_failure_probability)), 1.0, delta=2e-14)
        self.assertAlmostEqual(fsum(result.total_completion_time_distribution), result.success_probability, delta=2e-14)
        self.assertAlmostEqual(fsum(result.conditional_character_remaining_wishes_distribution), 1.0, delta=2e-14)
        self.assertAlmostEqual(result.expected_remaining_wishes_after_character, result.character_success_probability * result.expected_remaining_wishes_given_character_success, delta=2e-14)
        self.assertAlmostEqual(result.expected_total_completion_wish_given_success, fsum(t * p for t, p in enumerate(result.total_completion_time_distribution)) / result.success_probability, delta=2e-14)
        self.assertEqual(result.character_remaining_wishes_distribution, tuple(reversed(result.character_completion_time_distribution)))

    def test_zero_weapon_target_reduces_to_character(self):
        character, weapon = self.goals(weapon_target=0, cr=True)
        result = calculate_combined_plan(character_goal=character, weapon_goal=weapon, total_wishes=10)
        single = character.calculate(10)
        self.assertAlmostEqual(result.success_probability, single.success_probability, delta=2e-14)
        self.assertEqual(result.character_success_weapon_failure_probability, 0)
        self.assertEqual(result.total_completion_time_distribution, single.completion_time_distribution)

    def test_zero_character_target_reduces_to_weapon(self):
        character, weapon = self.goals(character_target=0)
        result = calculate_combined_plan(character_goal=character, weapon_goal=weapon, total_wishes=10)
        single = weapon.calculate(10)
        self.assertAlmostEqual(result.success_probability, single.success_probability, delta=2e-14)
        self.assertEqual(result.character_failure_probability, 0)
        self.assertEqual(result.expected_remaining_wishes_given_character_success, 10)
        self.assertEqual(result.character_completion_time_distribution[0], 1)

    def test_already_completed_character_uses_supplied_weapon_state(self):
        character, weapon = self.goals(WishState(50, True, 2, 3), WeaponWishState(79, True, 1), character_target=2)
        result = calculate_combined_plan(character_goal=character, weapon_goal=weapon, total_wishes=1)
        self.assertEqual(result.success_probability, 1)
        self.assertEqual(result.expected_total_completion_wish_given_success, 1)

    def test_already_completed_weapon_reduces_to_character(self):
        character, weapon = self.goals(weapon_state=WeaponWishState(10, True, 1, 4), weapon_target=3)
        result = calculate_combined_plan(character_goal=character, weapon_goal=weapon, total_wishes=5)
        self.assertAlmostEqual(result.success_probability, character.calculate(5).success_probability)

    def test_both_already_complete_at_zero(self):
        character, weapon = self.goals(WishState(copies=2), WeaponWishState(copies=2), 1, 1)
        result = calculate_combined_plan(character_goal=character, weapon_goal=weapon, total_wishes=0)
        self.assertEqual(result.success_probability, 1)
        self.assertEqual(result.expected_total_completion_wish_given_success, 0)
        self.assertEqual(minimum_combined_wishes_for_probability(character_goal=character, weapon_goal=weapon, desired_probability=1), 0)

    def test_zero_budget_when_targets_unmet(self):
        character, weapon = self.goals()
        result = calculate_combined_plan(character_goal=character, weapon_goal=weapon, total_wishes=0)
        self.assertEqual(result.success_probability, 0)
        self.assertEqual(result.character_failure_probability, 1)
        self.assertEqual(result.expected_remaining_wishes_after_character, 0)
        self.assertIsNone(result.expected_remaining_wishes_given_character_success)
        self.assertIsNone(result.expected_total_completion_wish_given_success)

    def test_character_impossible_within_budget(self):
        character = CharacterGoal(model=ProbabilityModel((0.0,) * 89 + (1.0,)))
        weapon = WeaponGoal()
        result = calculate_combined_plan(character_goal=character, weapon_goal=weapon, total_wishes=89)
        self.assertEqual(result.character_failure_probability, 1)
        self.assertEqual(result.success_probability, 0)

    def test_weapon_impossible_within_remaining_budget(self):
        character, weapon = self.goals(WishState(89, True), WeaponWishState(79, True, 1))
        result = calculate_combined_plan(character_goal=character, weapon_goal=weapon, total_wishes=1)
        self.assertEqual(result.character_success_weapon_failure_probability, 1)
        self.assertEqual(result.character_failure_probability, 0)
        self.assertEqual(result.success_probability, 0)

    def test_last_wish_completion_counts_and_weapon_state_is_preserved(self):
        for counter in range(4):
            character, weapon = self.goals(WishState(89, True, 0, counter), WeaponWishState(79, True, 1), cr=True)
            initial_weapon = weapon.initial_state
            result = calculate_combined_plan(character_goal=character, weapon_goal=weapon, total_wishes=2)
            self.assertEqual(result.success_probability, 1)
            self.assertEqual(result.total_completion_time_distribution[2], 1)
            self.assertEqual(result.expected_total_completion_wish_given_success, 2)
            self.assertEqual(weapon.initial_state, initial_weapon)

    def test_no_independent_full_budget_product_shortcut(self):
        character, weapon = self.goals(WishState(89, True), WeaponWishState(79, True, 1))
        # Each standalone goal succeeds with a one-wish budget, but both cannot
        # share that same one wish. A full-budget success product would be wrong.
        self.assertEqual(character.calculate(1).success_probability * weapon.calculate(1).success_probability, 1)
        self.assertEqual(calculate_combined_plan(character_goal=character, weapon_goal=weapon, total_wishes=1).success_probability, 0)

    def test_weapon_hard_pity_promoted_and_fate_states(self):
        for guaranteed in (False, True):
            for fate in (0, 1):
                character, weapon = self.goals(
                    WishState(89, True), WeaponWishState(79, guaranteed, fate),
                )
                result = calculate_combined_plan(
                    character_goal=character, weapon_goal=weapon, total_wishes=2,
                )
                expected = 1.0 if fate else (.5 if guaranteed else .375)
                self.assertEqual(result.success_probability, expected)
                self.assertEqual(result.character_failure_probability, 0)
                self.assertEqual(result.character_success_weapon_failure_probability, 1 - expected)

    def test_success_equals_character_pmf_times_weapon_cdf(self):
        character, weapon = self.goals(cr=True)
        prepared = prepare_combined_distribution(character_goal=character, weapon_goal=weapon, max_wishes=15)
        cdf = []
        cumulative = 0.0
        for p in prepared.weapon_result.completion_time_distribution:
            cumulative += p
            cdf.append(cumulative)
        identity = fsum(p * cdf[15 - t] for t, p in enumerate(prepared.character_result.completion_time_distribution))
        self.assertAlmostEqual(prepared.report(15).success_probability, identity, delta=2e-14)

    def test_more_budget_never_decreases_success(self):
        character, weapon = self.goals(cr=True)
        prepared = prepare_combined_distribution(character_goal=character, weapon_goal=weapon, max_wishes=25)
        probabilities = [prepared.report(n).success_probability for n in range(26)]
        self.assertTrue(all(a <= b for a, b in zip(probabilities, probabilities[1:])))

    def test_inverse_minimum_and_confidence_monotonicity(self):
        character = CharacterGoal(WishState(), 2, with_capturing_radiance(ProbabilityModel((1.0,) * 90)))
        weapon = WeaponGoal(model=WeaponProbabilityModel((1.0,) * 80))
        bound = deterministic_combined_wishes_to_target(character_goal=character, weapon_goal=weapon)
        prepared = prepare_combined_distribution(character_goal=character, weapon_goal=weapon, max_wishes=bound)
        rows = combined_threshold_table(character_goal=character, weapon_goal=weapon, probabilities=(0, .5, .75, .9, .95, .99, 1))
        self.assertTrue(all(a.wishes <= b.wishes for a, b in zip(rows, rows[1:])))
        for row in rows:
            self.assertGreaterEqual(prepared.report(row.wishes).success_probability, row.probability)
            if row.wishes:
                self.assertLess(prepared.report(row.wishes - 1).success_probability, row.probability)

    def test_inverse_respects_long_plateaus(self):
        character = CharacterGoal(WishState(87, True), model=ProbabilityModel((0.0,) * 89 + (1.0,)))
        weapon = WeaponGoal(WeaponWishState(77, True, 1), model=WeaponProbabilityModel((0.0,) * 79 + (1.0,)))
        self.assertEqual(minimum_combined_wishes_for_probability(character_goal=character, weapon_goal=weapon, desired_probability=.5), 6)

    def test_100_percent_cr_and_weapon_structural_bounds(self):
        character, weapon = self.goals(WishState(89, False, 0, 3), WeaponWishState(79, True, 1), cr=True)
        self.assertEqual(minimum_combined_wishes_for_probability(character_goal=character, weapon_goal=weapon, desired_probability=1), 2)
        with patch('genshin_wish.combined_planning.calculate_target_plan', side_effect=AssertionError('100% must use bounds')):
            self.assertEqual(minimum_combined_wishes_for_probability(character_goal=CharacterGoal(), weapon_goal=WeaponGoal(), desired_probability=1), 340)

    def test_zero_confidence_needs_zero_wishes(self):
        self.assertEqual(minimum_combined_wishes_for_probability(character_goal=CharacterGoal(), weapon_goal=WeaponGoal(), desired_probability=0), 0)

    def test_each_phase_runs_once_for_many_reports_and_thresholds(self):
        character, weapon = self.goals()
        with patch('genshin_wish.combined_planning.calculate_target_plan', wraps=calculate_target_plan) as c, patch('genshin_wish.combined_planning.calculate_weapon_target_plan', wraps=calculate_weapon_target_plan) as w:
            prepared = prepare_combined_distribution(character_goal=character, weapon_goal=weapon, max_wishes=340)
            for budget in (0, 5, 20, 100, 340):
                prepared.report(budget)
            prepared.threshold_table()
            self.assertEqual(c.call_count, 1)
            self.assertEqual(w.call_count, 1)

    def test_invalid_inputs_and_incomplete_prepared_horizon(self):
        for count in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                CharacterGoal(target_copies=count)
            with self.assertRaises(ValueError):
                WeaponGoal(target_copies=count)
            with self.assertRaises(ValueError):
                calculate_combined_plan(character_goal=CharacterGoal(), weapon_goal=WeaponGoal(), total_wishes=count)
        for p in (-.1, 1.1, float('nan')):
            with self.assertRaises(ValueError):
                minimum_combined_wishes_for_probability(character_goal=CharacterGoal(), weapon_goal=WeaponGoal(), desired_probability=p)
        prepared = prepare_combined_distribution(character_goal=CharacterGoal(), weapon_goal=WeaponGoal(), max_wishes=0)
        with self.assertRaises(ValueError):
            prepared.report(1)
        with self.assertRaises(ValueError):
            prepared.minimum_wishes(.5)

    def test_prepared_certainty_can_report_larger_budgets(self):
        character, weapon = self.goals(WishState(89, True), WeaponWishState(79, True, 1))
        prepared = prepare_combined_distribution(character_goal=character, weapon_goal=weapon, max_wishes=2)
        result = prepared.report(20)
        self.assertEqual(result.success_probability, 1)
        self.assertEqual(result.expected_total_completion_wish_given_success, 2)
        self.assertEqual(result.expected_remaining_wishes_given_character_success, 19)

    def test_legacy_and_cr_enabled_regressions_remain_unchanged(self):
        for model, expected in (
            (community_soft_pity_model(), .90053302850222),
            (with_capturing_radiance(community_soft_pity_model()), .91049583930138),
        ):
            result = calculate_combined_plan(character_goal=CharacterGoal(WishState(37), 2, model), weapon_goal=WeaponGoal(target_copies=0), total_wishes=240)
            self.assertAlmostEqual(result.success_probability, expected, delta=2e-14)

    def test_realistic_confidence_minimums_against_reports(self):
        character = CharacterGoal(WishState(37), 2, with_capturing_radiance(community_soft_pity_model()))
        weapon = WeaponGoal(model=community_weapon_soft_pity_model())
        prepared = prepare_combined_distribution(
            character_goal=character, weapon_goal=weapon, max_wishes=477,
        )
        for confidence in (.50, .75, .90, .95, .99):
            minimum = prepared.minimum_wishes(confidence)
            self.assertGreaterEqual(prepared.report(minimum).success_probability, confidence)
            self.assertLess(prepared.report(minimum - 1).success_probability, confidence)


if __name__ == '__main__':
    unittest.main()
