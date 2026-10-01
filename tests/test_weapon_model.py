import math
import unittest

from genshin_wish.weapon_engine import next_weapon_state_probabilities
from genshin_wish.weapon_model import (
    WeaponProbabilityModel,
    WeaponWishState,
    official_only_weapon_model,
    community_weapon_soft_pity_model,
)


class WeaponTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.always = WeaponProbabilityModel((1.0,) * 80)

    def branches(self, state: WeaponWishState) -> dict[WeaponWishState, float]:
        return dict(next_weapon_state_probabilities(state, self.always))

    def test_fresh_five_star_has_all_three_outcomes(self) -> None:
        branches = self.branches(WeaponWishState(12, False, 0, 0))
        self.assertEqual(branches[WeaponWishState(0, False, 0, 1)], 0.375)
        self.assertEqual(branches[WeaponWishState(0, False, 1, 0)], 0.375)
        self.assertEqual(branches[WeaponWishState(0, True, 1, 0)], 0.25)
        self.assertEqual(sum(branches.values()), 1.0)

    def test_promoted_guarantee_excludes_non_promoted_outcome(self) -> None:
        branches = self.branches(WeaponWishState(30, True, 0, 0))
        self.assertEqual(branches, {
            WeaponWishState(0, False, 0, 1): 0.5,
            WeaponWishState(0, False, 1, 0): 0.5,
        })

    def test_fate_point_forces_desired_and_clears_both_flags(self) -> None:
        self.assertEqual(
            self.branches(WeaponWishState(44, True, 1, 2)),
            {WeaponWishState(0, False, 0, 3): 1.0},
        )

    def test_hard_pity_has_no_non_five_star_branch(self) -> None:
        branches = next_weapon_state_probabilities(
            WeaponWishState(79), official_only_weapon_model()
        )
        self.assertTrue(all(state.pity == 0 for state, _ in branches))
        self.assertTrue(math.isclose(sum(p for _, p in branches), 1.0))

    def test_no_five_star_preserves_rule_state_and_increments_pity(self) -> None:
        model = WeaponProbabilityModel((0.0,) * 79 + (1.0,))
        self.assertEqual(
            next_weapon_state_probabilities(WeaponWishState(4, True, 1, 2), model),
            ((WeaponWishState(5, True, 1, 2), 1.0),),
        )

    def test_invalid_state_and_model_are_rejected(self) -> None:
        for pity in (-1, 80):
            with self.assertRaises(ValueError):
                WeaponWishState(pity)
        with self.assertRaises(ValueError):
            WeaponWishState(fate_point=2)
        with self.assertRaises(ValueError):
            WeaponProbabilityModel((0.007,) * 80)

    def test_outgoing_mass_is_one_for_every_rule_state_and_pity(self) -> None:
        for model in (official_only_weapon_model(), community_weapon_soft_pity_model()):
            for pity in range(80):
                for guaranteed in (False, True):
                    for fate in (0, 1):
                        branches = next_weapon_state_probabilities(
                            WeaponWishState(pity, guaranteed, fate), model
                        )
                        self.assertTrue(
                            math.isclose(sum(p for _, p in branches), 1.0, abs_tol=1e-15)
                        )


if __name__ == "__main__":
    unittest.main()
