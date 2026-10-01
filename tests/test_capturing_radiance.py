"""Exact CR rule tests and independent DP regression checks."""

import unittest
from collections import defaultdict
from dataclasses import replace
from math import fsum

from genshin_wish import (
    CapturingRadianceModel, ProbabilityModel, WishState, calculate,
    calculate_target_plan, community_soft_pity_model, expected_wishes_to_target,
    iter_target_success_probabilities, minimum_wishes_for_probability,
    official_only_model, simulate, threshold_table, with_capturing_radiance,
)
from genshin_wish.engine import next_state_probabilities
from genshin_wish.cli import collect_interactive_inputs, parse_cr_counter
from genshin_wish.planning import deterministic_wishes_to_target


def reference_dp(initial, wishes, target, model):
    """Literal Python translation of the user's C++ rules, independent of kernel."""
    states = {initial: 1.0}
    for _ in range(wishes):
        following = defaultdict(float)
        for state, mass in states.items():
            p, g, copies, c = state.pity, state.guaranteed, state.copies, state.cr_counter
            q = model.five_star_probabilities[p]
            if q < 1:
                following[WishState(p + 1, g, copies, c)] += mass * (1 - q)
            if g:
                following[WishState(0, False, copies + 1, c)] += mass * q
            else:
                r = (0.00018, 0.00018, 0.10, 1.0)[c]
                following[WishState(0, False, copies + 1, 1)] += mass * q * r
                if r < 1:
                    following[WishState(0, False, copies + 1, max(0, c - 1))] += mass * q * (1 - r) * .5
                    following[WishState(0, True, copies, min(3, c + 1))] += mass * q * (1 - r) * .5
        states = {s: p for s, p in following.items() if p > 0}
    return states, fsum(p for s, p in states.items() if s.copies >= target)


class CapturingRadianceTests(unittest.TestCase):
    def setUp(self):
        self.always = with_capturing_radiance(ProbabilityModel((1.0,) * 90))

    def test_initial_counter_and_positional_compatibility(self):
        self.assertEqual(WishState(37, False, 2).cr_counter, 1)

    def test_exact_c0_c1_c2_c3_transitions(self):
        for c, r in enumerate((0.00018, 0.00018, .1, 1.0)):
            expected = defaultdict(float)
            expected[WishState(0, False, 1, 1)] += r
            if r < 1:
                expected[WishState(0, False, 1, max(0, c - 1))] += (1 - r) * .5
                expected[WishState(0, True, 0, min(3, c + 1))] += (1 - r) * .5
            actual = defaultdict(float)
            for state, p in next_state_probabilities(WishState(cr_counter=c), self.always):
                actual[state] += p
            self.assertEqual(dict(actual), dict(expected))

    def test_guaranteed_result_preserves_all_counters(self):
        for c in range(4):
            self.assertEqual(
                next_state_probabilities(WishState(89, True, 2, c), self.always),
                ((WishState(0, False, 3, c), 1.0),),
            )

    def test_c3_always_triggers_cr_and_resets_c1(self):
        self.assertEqual(
            next_state_probabilities(WishState(cr_counter=3), self.always),
            ((WishState(0, False, 1, 1), 1.0),),
        )

    def test_missing_five_star_preserves_counter(self):
        model = with_capturing_radiance(ProbabilityModel((0.0,) * 89 + (1.0,)))
        for c in range(4):
            self.assertEqual(
                next_state_probabilities(WishState(12, False, 0, c), model),
                ((WishState(13, False, 0, c), 1.0),),
            )

    def test_replaceable_cr_model_loss_cap_and_win_floor(self):
        # The default C3 has no losses; disable CR to exercise its configured cap.
        rules = CapturingRadianceModel(probabilities=(0.0,) * 4)
        for c in range(4):
            for featured_probability in (0.0, 1.0):
                model = with_capturing_radiance(
                    ProbabilityModel((1.0,) * 90, featured_probability), rules
                )
                featured = bool(featured_probability)
                counter = max(0, c - 1) if featured else min(3, c + 1)
                self.assertEqual(
                    next_state_probabilities(WishState(cr_counter=c), model),
                    ((WishState(0, not featured, int(featured), counter), 1.0),),
                )

    def test_disabled_cr_preserves_nondefault_counter(self):
        state = WishState(89, False, 0, 2)
        for result in (
            calculate(initial_state=state, wishes=2, target_copies=1),
            calculate_target_plan(initial_state=state, wishes=2, target_copies=1),
        ):
            self.assertTrue(all(s.cr_counter == 2 for s in result.final_states))

    def test_full_and_target_dp_mass_conservation(self):
        model = with_capturing_radiance(community_soft_pity_model())
        results = []
        for function in (calculate, calculate_target_plan):
            result = function(initial_state=WishState(37), wishes=120, target_copies=2, model=model)
            results.append(result)
            self.assertTrue(all(abs(m - 1) < 2e-13 for m in result.probability_mass_by_wish))
            self.assertAlmostEqual(fsum(result.copy_distribution.values()), 1.0, delta=2e-13)
            self.assertTrue(all(0 <= p <= 1 for p in result.copy_distribution.values()))
        self.assertAlmostEqual(results[0].success_probability, results[1].success_probability, delta=2e-14)

    def test_all_outgoing_branch_masses_sum_to_one(self):
        model = with_capturing_radiance(community_soft_pity_model())
        for pity in range(90):
            for c in range(4):
                for guaranteed in (True, False):
                    branches = next_state_probabilities(WishState(pity, guaranteed, 0, c), model)
                    self.assertAlmostEqual(fsum(p for _, p in branches), 1.0, delta=2e-15)

    def test_kernel_matches_independent_cpp_style_reference(self):
        model = with_capturing_radiance(community_soft_pity_model())
        for c in range(4):
            state = WishState(87, False, 0, c)
            reference, success = reference_dp(state, 12, 2, model)
            exact = calculate(initial_state=state, wishes=12, target_copies=2, model=model)
            self.assertEqual(set(reference), set(exact.final_states))
            for s, p in reference.items():
                self.assertAlmostEqual(exact.final_states[s], p, delta=2e-15)
            self.assertAlmostEqual(exact.success_probability, success, delta=2e-15)

    def test_full_tail_target_hitting_remaining_and_inverse_agree(self):
        model = self.always
        state = WishState(cr_counter=2)
        result = calculate_target_plan(initial_state=state, wishes=5, target_copies=3, model=model)
        full = calculate(initial_state=state, wishes=5, target_copies=3, model=model)
        self.assertAlmostEqual(result.success_probability, full.success_probability, delta=2e-15)
        self.assertAlmostEqual(fsum(result.completion_time_distribution), result.success_probability)
        self.assertEqual(result.remaining_wishes_distribution, tuple(reversed(result.completion_time_distribution)))
        self.assertTrue(all(s.copies < 3 for s in result.final_states))
        curve = dict(iter_target_success_probabilities(initial_state=state, target_copies=3, max_wishes=10, model=model))
        self.assertAlmostEqual(curve[5], result.success_probability)
        for row in threshold_table(initial_state=state, target_copies=3, probabilities=(.5, .9, .99), model=model):
            self.assertGreaterEqual(curve[row.wishes], row.probability)
            self.assertLess(curve[row.wishes - 1], row.probability)

    def test_expectation_matches_finite_completion_pmf(self):
        for c in range(4):
            state = WishState(cr_counter=c)
            bound = deterministic_wishes_to_target(initial_state=state, target_copies=4, model=self.always)
            result = calculate_target_plan(initial_state=state, wishes=bound, target_copies=4, model=self.always)
            self.assertAlmostEqual(
                expected_wishes_to_target(initial_state=state, target_copies=4, model=self.always),
                fsum(t * p for t, p in enumerate(result.completion_time_distribution)), delta=2e-13,
            )

    def test_100_percent_uses_counter_aware_structural_bound(self):
        model = with_capturing_radiance(official_only_model())
        state = WishState(89, False, 0, 3)
        bound = minimum_wishes_for_probability(initial_state=state, target_copies=1, desired_probability=1.0, model=model)
        self.assertEqual(bound, 1)
        self.assertEqual(calculate_target_plan(initial_state=state, wishes=0, target_copies=1, model=model).success_probability, 0)
        self.assertEqual(calculate_target_plan(initial_state=state, wishes=1, target_copies=1, model=model).success_probability, 1)
        # Starting at C1, three copies cannot all take two 5-stars: C3 forces CR.
        self.assertEqual(deterministic_wishes_to_target(initial_state=WishState(), target_copies=3, model=model), 450)

    def test_zero_target_and_zero_budget(self):
        for target in (0, 1):
            result = calculate_target_plan(initial_state=WishState(), wishes=0, target_copies=target, model=self.always)
            self.assertEqual(result.success_probability, float(target == 0))

    def test_legacy_regression_is_explicitly_preserved(self):
        result = calculate_target_plan(initial_state=WishState(37), wishes=240, target_copies=2, model=community_soft_pity_model())
        self.assertAlmostEqual(result.success_probability, .90053302850222, delta=2e-14)

    def test_new_cr_regression_is_separate_from_legacy(self):
        model = with_capturing_radiance(community_soft_pity_model())
        result = calculate_target_plan(initial_state=WishState(37), wishes=240, target_copies=2, model=model)
        # The changed outcome is documented beside the retained legacy regression:
        # C2 boosts the next non-guaranteed chance after an actual C1 loss.
        self.assertAlmostEqual(result.success_probability, .91049583930138, delta=2e-14)
        self.assertAlmostEqual(expected_wishes_to_target(initial_state=WishState(37), target_copies=2, model=model), 159.296037166793, delta=2e-10)

    def test_model_can_be_enabled_replaced_and_disabled_without_changing_pity(self):
        original = community_soft_pity_model()
        enabled = with_capturing_radiance(original)
        self.assertEqual(enabled.five_star_probabilities, original.five_star_probabilities)
        self.assertIsNone(replace(enabled, capturing_radiance=None).capturing_radiance)
        self.assertEqual(with_capturing_radiance(original, CapturingRadianceModel(probabilities=(1.0,) * 4)).capturing_radiance.probabilities, (1.0,) * 4)

    def test_invalid_counter_and_rules(self):
        for value in (-1, 4, 1.5, True):
            with self.assertRaises(ValueError):
                WishState(cr_counter=value)
        for values in ((0.0,), (0.0, .1, .2, float('nan'))):
            with self.assertRaises(ValueError):
                CapturingRadianceModel(probabilities=values)

    def test_interactive_cr_selection_and_counter_validation(self):
        responses = iter(("37", "n", "240", "2", "cr", "4", ""))
        output = []
        request = collect_interactive_inputs(input_fn=lambda _: next(responses), output_fn=output.append)
        self.assertEqual(request.state.cr_counter, 1)
        self.assertIsNotNone(request.model.capturing_radiance)
        self.assertTrue(any("CR counter must be between" in line for line in output))
        self.assertEqual(parse_cr_counter("3"), 3)

    def test_seeded_simulation_agrees_with_exact(self):
        exact = calculate_target_plan(initial_state=WishState(cr_counter=2), wishes=4, target_copies=3, model=self.always)
        sampled = simulate(initial_state=WishState(cr_counter=2), wishes=4, target_copies=3, model=self.always, trials=30_000, seed=401)
        self.assertAlmostEqual(exact.success_probability, sampled.success_probability, delta=.015)


if __name__ == '__main__':
    unittest.main()
