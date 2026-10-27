"""API contract and numerical checks; install .[web,web-test] to run."""

import importlib.util
import unittest
from unittest.mock import patch
from collections import defaultdict
from math import fsum

AVAILABLE = all(importlib.util.find_spec(name) for name in ("fastapi", "httpx"))
if AVAILABLE:
    from fastapi.testclient import TestClient
    from web.backend import app, WishRequest, calculate_wishes
    from genshin_wish import (
        CharacterGoal, WeaponGoal, WishState, WeaponWishState,
        community_soft_pity_model, community_weapon_soft_pity_model,
        with_capturing_radiance, calculate_combined_plan,
    )
    from genshin_wish.engine import next_state_probabilities
    from genshin_wish.weapon_engine import next_weapon_state_probabilities


@unittest.skipUnless(AVAILABLE, "install .[web,web-test] for web API tests")
class WebApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def calculate(self, **overrides):
        body = dict(mode="character", wish_budget=240, pity=37, target_copies=2)
        body.update(overrides)
        response = self.client.post("/api/calculate", json=body)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_serves_page_assets_and_version_from_one_origin(self):
        self.assertIn('id="wish_form"', self.client.get("/").text)
        self.assertEqual(self.client.get("/api/version").json()["version"], "1.0.3")
        for path in ("/static/script.js", "/static/startup.js", "/static/style.css"):
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_backend_version_is_dynamic_and_html_has_no_release_literals(self):
        with patch("web.backend.VERSION", "9.8.7"):
            self.assertEqual(self.client.get("/api/version").json()["version"], "9.8.7")
            self.assertEqual(self.calculate(wish_budget=0)["version"], "9.8.7")
        html = self.client.get("/").text
        self.assertIn("data-app-version", html)
        self.assertNotIn("1.0.", html)

    def test_character_enables_cr_and_preserves_regression(self):
        data = self.calculate()
        self.assertAlmostEqual(data["success_probability"], .91049583930138, delta=3e-14)
        thresholds = {row["probability"]: row["wishes"] for row in data["thresholds"]}
        self.assertEqual([thresholds[p] for p in (.9, .95, .99, 1)], [234, 267, 278, 323])
        self.assertIn("community", data["assumptions"]["capturing_radiance"])

    def test_weapon_regression_and_thresholds(self):
        data = self.calculate(mode="weapon", wish_budget=120)
        self.assertAlmostEqual(data["success_probability"], .7066535051236249, delta=3e-14)
        thresholds = {row["probability"]: row["wishes"] for row in data["thresholds"]}
        self.assertEqual([thresholds[p] for p in (.5, .75, .9, .95, .99)], [79, 128, 133, 135, 138])

    def test_combined_regression_and_three_outcomes(self):
        data = self.calculate(mode="combined")
        self.assertAlmostEqual(data["success_probability"], .4574509331, delta=1e-10)
        self.assertAlmostEqual(fsum(data["breakdown"].values()), 1.0, delta=3e-14)
        thresholds = {row["probability"]: row["wishes"] for row in data["thresholds"]}
        self.assertEqual([thresholds[p] for p in (.9, .95, .99, 1)], [332, 353, 403, 477])

    def test_outcome_mass_and_target_rank_in_each_mode(self):
        for mode in ("character", "weapon", "combined"):
            data = self.calculate(mode=mode, wish_budget=10, target_copies=4, weapon_target=3)
            rows = data["outcomes"]
            self.assertAlmostEqual(fsum(row["probability"] for row in rows), 1, delta=3e-14)
            self.assertEqual(len([row for row in rows if row["is_target"]]), 1)
            self.assertTrue(all(a["probability"] >= b["probability"] for a, b in zip(rows, rows[1:])))
            for row in rows:
                expected = 1 + sum(other["probability"] > row["probability"] for other in rows)
                self.assertEqual(row["rank"], expected)
            target = next(row for row in rows if row["is_target"])
            self.assertAlmostEqual(target["probability"], data["success_probability"], delta=3e-14)

    def test_zero_targets_zero_budget_and_guarantees(self):
        for mode in ("character", "weapon", "combined"):
            data = self.calculate(mode=mode, target_copies=0, weapon_target=0, wish_budget=0)
            self.assertEqual(data["success_probability"], 1)
            self.assertTrue(all(row["wishes"] == 0 for row in data["thresholds"]))
            self.assertEqual(data["conditional_expected_wishes"], 0)
            failed = self.calculate(mode=mode, wish_budget=0)
            self.assertEqual(failed["success_probability"], 0)
            self.assertIsNone(failed["conditional_expected_wishes"])
        data = self.calculate(mode="combined", wish_budget=2, pity=89, cr_counter=3,
                              target_copies=1, weapon_pity=79, fate_point=1, weapon_guaranteed=True)
        self.assertEqual(data["success_probability"], 1)
        self.assertEqual(data["thresholds"][-1]["wishes"], 2)

    def test_combined_endpoint_distribution_matches_small_sequential_dp(self):
        # Independent short sequential state enumeration, used only as a test.
        character_model = with_capturing_radiance(community_soft_pity_model())
        weapon_model = community_weapon_soft_pity_model()
        for budget in (0, 1, 2, 3, 5):
            character_state = WishState(89, False, 0, 2)
            weapon_state = WeaponWishState(79, True, 0)
            states = {(character_state, weapon_state): 1.0}
            for _ in range(budget):
                following = defaultdict(float)
                for (c, w), mass in states.items():
                    if c.copies < 1:
                        for nc, p in next_state_probabilities(c, character_model):
                            following[nc, w] += mass * p
                    elif w.copies < 2:
                        for nw, p in next_weapon_state_probabilities(w, weapon_model):
                            following[c, nw] += mass * p
                    else:
                        following[c, w] += mass
                states = following
            reference = defaultdict(float)
            for (c, w), mass in states.items():
                reference[c.copies, w.copies] += mass
            data = self.calculate(mode="combined", wish_budget=budget, pity=89, cr_counter=2,
                                  target_copies=1, weapon_pity=79, weapon_guaranteed=True, weapon_target=2)
            for row in data["outcomes"]:
                self.assertAlmostEqual(row["probability"], reference[row["character_copies"], row["weapon_copies"]], delta=3e-14)

    def test_invalid_api_inputs_are_rejected(self):
        for invalid in (
            {"mode": "unknown"}, {"wish_budget": -1}, {"wish_budget": 2001},
            {"pity": 90}, {"weapon_pity": 80}, {"cr_counter": 4}, {"fate_point": 2},
            {"target_copies": -1}, {"weapon_target": 11}, {"wish_budget": 1.5},
            {"is_guaranteed": "yes"}, {"unexpected": 1},
        ):
            response = self.client.post("/api/calculate", json={"wish_budget": 1, **invalid})
            self.assertEqual(response.status_code, 422, str(invalid))

    def test_single_completed_phase_reduces_to_other_banner(self):
        only_weapon = self.calculate(mode="weapon", wish_budget=120)
        combined = self.calculate(mode="combined", wish_budget=120, target_copies=0)
        self.assertAlmostEqual(combined["success_probability"], only_weapon["success_probability"], delta=3e-14)
        only_character = self.calculate()
        combined = self.calculate(mode="combined", weapon_target=0)
        self.assertAlmostEqual(combined["success_probability"], only_character["success_probability"], delta=3e-14)


if __name__ == "__main__":
    unittest.main()
