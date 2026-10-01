import unittest
import xml.etree.ElementTree as ET

from genshin_wish.model import community_soft_pity_model, official_only_model
from genshin_wish.plotting import _svg_plot
from genshin_wish.waiting_time import first_five_star_distribution


class PlottingTests(unittest.TestCase):
    def test_svg_output_is_valid_and_marks_soft_pity(self) -> None:
        baseline = first_five_star_distribution(official_only_model())
        soft = first_five_star_distribution(community_soft_pity_model())
        svg = _svg_plot(
            baseline=baseline.pmf,
            soft_pity=soft.pmf,
            title="test",
            y_label="P(X = n)",
            y_max=max(max(baseline.pmf), max(soft.pmf)) * 1.08,
        )
        root = ET.fromstring(svg)
        self.assertTrue(root.tag.endswith("svg"))
        self.assertIn("assumed soft-pity region", svg)


if __name__ == "__main__":
    unittest.main()
