import math
import unittest

from genshin_wish.engine import expected_wishes_to_target
from genshin_wish.model import WishState, community_soft_pity_model, official_only_model
from genshin_wish.waiting_time import first_five_star_distribution


class WaitingTimeTests(unittest.TestCase):
    def test_community_curve_is_the_documented_configurable_assumption(self) -> None:
        model = community_soft_pity_model()
        self.assertEqual(model.five_star_probability(72), 0.006)  # wish 73
        self.assertEqual(model.five_star_probability(73), 0.066)  # wish 74
        self.assertEqual(model.five_star_probability(74), 0.126)  # wish 75
        self.assertEqual(model.five_star_probability(89), 1.0)    # wish 90

        custom = community_soft_pity_model(
            base_probability=0.01, soft_pity_start_wish=80, increase_per_wish=0.1
        )
        self.assertEqual(custom.five_star_probability(78), 0.01)
        self.assertEqual(custom.five_star_probability(79), 0.11)

    def test_distribution_invariants_for_both_models(self) -> None:
        for model in (official_only_model(), community_soft_pity_model()):
            with self.subTest(model=model.name):
                distribution = first_five_star_distribution(model)
                self.assertTrue(math.isclose(sum(distribution.pmf), 1.0, abs_tol=1e-12))
                self.assertEqual(distribution.cdf[-1], 1.0)
                self.assertEqual(distribution.survival[-1], 0.0)
                self.assertTrue(all(a <= b for a, b in zip(distribution.cdf, distribution.cdf[1:])))

                survived_before = 1.0
                for probability, q_n, survived_after in zip(
                    distribution.pmf,
                    distribution.conditional_probabilities,
                    distribution.survival,
                ):
                    self.assertTrue(math.isclose(probability, survived_before * q_n, abs_tol=1e-15))
                    survived_before = survived_after

    def test_arbitrary_starting_pity_changes_support(self) -> None:
        distribution = first_five_star_distribution(
            community_soft_pity_model(), starting_pity=37
        )
        self.assertEqual(distribution.wish_numbers[0], 1)
        self.assertEqual(distribution.wish_numbers[-1], 53)
        self.assertEqual(distribution.cdf[-1], 1.0)

    def test_pmf_expectation_agrees_with_engine(self) -> None:
        for model in (official_only_model(), community_soft_pity_model()):
            for pity in (0, 37, 73, 89):
                with self.subTest(model=model.name, pity=pity):
                    distribution = first_five_star_distribution(model, starting_pity=pity)
                    engine_expectation = expected_wishes_to_target(
                        initial_state=WishState(pity=pity, guaranteed=True),
                        target_copies=1,
                        model=model,
                    )
                    self.assertTrue(
                        math.isclose(distribution.expected_wishes, engine_expectation, abs_tol=1e-12)
                    )


if __name__ == "__main__":
    unittest.main()
