import unittest
from math import fsum

from genshin_wish.cli import (
    compact_copy_distribution,
    collect_interactive_inputs,
    parse_confidence_percent,
    parse_nonnegative_integer,
    parse_pity,
    parse_fate_point,
    parse_weapon_pity,
    parse_yes_no,
    run_banner_interactive,
    run_interactive,
)


class CliValidationTests(unittest.TestCase):
    def test_compact_distribution_uses_half_percent_threshold(self) -> None:
        distribution = {0: 0.002, 1: 0.005, 2: 0.500, 3: 0.001, 4: 0.490, 5: 0.002}
        compact = compact_copy_distribution(distribution, target_copies=3)
        displayed = dict(compact.individual_outcomes)

        self.assertIn(1, displayed)  # Exactly 0.5% is displayed.
        self.assertIn(2, displayed)
        self.assertIn(3, displayed)  # Target is displayed below the threshold.
        self.assertIn(4, displayed)
        self.assertNotIn(0, displayed)
        self.assertNotIn(5, displayed)
        self.assertAlmostEqual(compact.combined_probability, 0.004, delta=1e-15)
        self.assertAlmostEqual(
            fsum(displayed.values()) + compact.combined_probability, 1.0, delta=1e-15
        )

    def test_compaction_does_not_modify_full_distribution(self) -> None:
        distribution = {0: 0.004, 1: 0.996}
        original = distribution.copy()
        compact = compact_copy_distribution(distribution, target_copies=7)
        self.assertEqual(distribution, original)
        self.assertEqual(dict(compact.individual_outcomes)[7], 0.0)
        self.assertEqual(compact.combined_probability, 0.004)

    def test_pity_validation(self) -> None:
        self.assertEqual(parse_pity("89"), 89)
        for value in ("-1", "90", "not a number"):
            with self.assertRaises(ValueError):
                parse_pity(value)

    def test_weapon_pity_and_fate_validation(self) -> None:
        self.assertEqual(parse_weapon_pity("79"), 79)
        self.assertEqual(parse_fate_point("1"), 1)
        for value in ("-1", "80", "x"):
            with self.assertRaises(ValueError):
                parse_weapon_pity(value)
        for value in ("-1", "2", "x"):
            with self.assertRaises(ValueError):
                parse_fate_point(value)

    def test_negative_counts_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_nonnegative_integer("-1", "available wishes")

    def test_yes_no_validation(self) -> None:
        self.assertTrue(parse_yes_no("YES"))
        self.assertFalse(parse_yes_no("n"))
        with self.assertRaises(ValueError):
            parse_yes_no("maybe")

    def test_confidence_validation(self) -> None:
        self.assertEqual(parse_confidence_percent("0"), 0.0)
        self.assertEqual(parse_confidence_percent("90%"), 0.9)
        self.assertEqual(parse_confidence_percent("100"), 1.0)
        for value in ("-1", "101", "hello"):
            with self.assertRaises(ValueError):
                parse_confidence_percent(value)

    def test_interactive_prompts_retry_with_clear_errors(self) -> None:
        responses = iter(("90", "89", "maybe", "y", "-1", "0", "0", "3", "2"))
        output: list[str] = []
        request = collect_interactive_inputs(
            input_fn=lambda _prompt: next(responses), output_fn=output.append
        )
        self.assertEqual(request.state.pity, 89)
        self.assertTrue(request.state.guaranteed)
        self.assertEqual(request.wishes, 0)
        self.assertEqual(request.target_copies, 0)
        self.assertIn("community soft-pity assumption", request.model.name)
        self.assertGreaterEqual(sum(line.startswith("Invalid input:") for line in output), 4)

    def test_complete_interactive_zero_target_session(self) -> None:
        responses = iter(("0", "n", "0", "0", "1", ""))
        output: list[str] = []
        run_interactive(input_fn=lambda _prompt: next(responses), output_fn=output.append)
        rendered = "\n".join(output)
        self.assertIn("P(target reached): 100.00000000%", rendered)
        self.assertIn("Probability target", rendered)

    def test_top_level_cli_can_select_weapon_planning(self) -> None:
        responses = iter(("2", "79", "y", "1", "1", "1", "1", "100"))
        output: list[str] = []
        run_banner_interactive(
            input_fn=lambda _prompt: next(responses), output_fn=output.append
        )
        rendered = "\n".join(output)
        self.assertIn("Weapon Event Wish Planner", rendered)
        self.assertIn("P(target reached): 100.00000000%", rendered)
        self.assertIn("Minimum weapon wishes for at least 100.00% success: 1", rendered)


if __name__ == "__main__":
    unittest.main()
