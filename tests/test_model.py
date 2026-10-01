import unittest

from genshin_wish.engine import next_state_probabilities
from genshin_wish.model import ProbabilityModel, WishState, official_only_model


class TransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = official_only_model()

    def test_hard_pity_always_produces_a_five_star_and_resets_pity(self) -> None:
        branches = next_state_probabilities(WishState(89, True, 0), self.model)
        self.assertEqual(branches, ((WishState(0, False, 1), 1.0),))

    def test_losing_activates_guarantee_and_resets_pity(self) -> None:
        model = ProbabilityModel((1.0,) * 90, featured_probability=0.5)
        branches = dict(next_state_probabilities(WishState(10, False, 0), model))
        self.assertEqual(branches[WishState(0, True, 0)], 0.5)

    def test_guaranteed_five_star_is_featured_and_clears_guarantee(self) -> None:
        model = ProbabilityModel((1.0,) * 90)
        branches = next_state_probabilities(WishState(5, True, 2), model)
        self.assertEqual(branches, ((WishState(0, False, 3), 1.0),))

    def test_featured_win_clears_guarantee(self) -> None:
        model = ProbabilityModel((1.0,) * 90, featured_probability=1.0)
        branches = next_state_probabilities(WishState(5, False, 0), model)
        self.assertEqual(branches, ((WishState(0, False, 1), 1.0),))

    def test_model_rejects_non_forced_hard_pity(self) -> None:
        with self.assertRaises(ValueError):
            ProbabilityModel((0.006,) * 90)


if __name__ == "__main__":
    unittest.main()

