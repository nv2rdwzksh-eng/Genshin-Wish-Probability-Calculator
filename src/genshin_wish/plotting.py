"""Generate dependency-free v0.2 first-5-star PMF and CDF SVG plots."""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
from typing import Sequence

from .model import community_soft_pity_model, official_only_model
from .waiting_time import first_five_star_distribution


def _svg_plot(
    *,
    baseline: Sequence[float],
    soft_pity: Sequence[float],
    title: str,
    y_label: str,
    y_max: float,
) -> str:
    width, height = 1000, 560
    left, right, top, bottom = 92, 28, 55, 78
    plot_width = width - left - right
    plot_height = height - top - bottom

    def x_position(wish: int) -> float:
        return left + (wish - 1) / 89 * plot_width

    def y_position(value: float) -> float:
        return top + (1.0 - value / y_max) * plot_height

    def points(values: Sequence[float]) -> str:
        return " ".join(
            f"{x_position(wish):.2f},{y_position(value):.2f}"
            for wish, value in enumerate(values, start=1)
        )

    soft_start_x = x_position(74)
    hard_pity_x = x_position(90)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-family="sans-serif" font-size="21" font-weight="600">{escape(title)}</text>',
        f'<rect x="{soft_start_x:.2f}" y="{top}" width="{hard_pity_x - soft_start_x:.2f}" height="{plot_height}" fill="#f3b61f" opacity="0.16"/>',
    ]

    for step in range(6):
        value = y_max * step / 5
        y = y_position(value)
        parts.extend(
            [
                f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" stroke="#d9dee7" stroke-width="1"/>',
                f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" font-family="sans-serif" font-size="12" fill="#344054">{value:.0%}</text>',
            ]
        )

    for wish in (1, 20, 40, 60, 74, 80, 90):
        x = x_position(wish)
        parts.extend(
            [
                f'<line x1="{x:.2f}" y1="{top + plot_height}" x2="{x:.2f}" y2="{top + plot_height + 6}" stroke="#344054"/>',
                f'<text x="{x:.2f}" y="{top + plot_height + 24}" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#344054">{wish}</text>',
            ]
        )

    parts.extend(
        [
            f'<line x1="{left}" y1="{top + plot_height}" x2="{width - right}" y2="{top + plot_height}" stroke="#344054" stroke-width="1.5"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#344054" stroke-width="1.5"/>',
            f'<line x1="{hard_pity_x:.2f}" y1="{top}" x2="{hard_pity_x:.2f}" y2="{top + plot_height}" stroke="#b42318" stroke-width="1.5" stroke-dasharray="6 5"/>',
            f'<polyline points="{points(baseline)}" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linejoin="round"/>',
            f'<polyline points="{points(soft_pity)}" fill="none" stroke="#d97706" stroke-width="2.5" stroke-linejoin="round"/>',
            f'<text x="{left + plot_width / 2}" y="{height - 20}" text-anchor="middle" font-family="sans-serif" font-size="14">Wish since previous 5-star</text>',
            f'<text x="22" y="{top + plot_height / 2}" text-anchor="middle" font-family="sans-serif" font-size="14" transform="rotate(-90 22 {top + plot_height / 2})">{escape(y_label)}</text>',
            f'<rect x="{left + 14}" y="{top + 12}" width="310" height="75" rx="6" fill="#ffffff" stroke="#d0d5dd" opacity="0.94"/>',
            f'<line x1="{left + 28}" y1="{top + 33}" x2="{left + 62}" y2="{top + 33}" stroke="#2563eb" stroke-width="3"/><text x="{left + 72}" y="{top + 38}" font-family="sans-serif" font-size="13">Official-only flat baseline</text>',
            f'<line x1="{left + 28}" y1="{top + 59}" x2="{left + 62}" y2="{top + 59}" stroke="#d97706" stroke-width="3"/><text x="{left + 72}" y="{top + 64}" font-family="sans-serif" font-size="13">Community soft-pity assumption</text>',
            f'<text x="{(soft_start_x + hard_pity_x) / 2:.2f}" y="{top + plot_height - 14}" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#8a5200">assumed soft-pity region</text>',
            '</svg>',
        ]
    )
    return "\n".join(parts)


def create_waiting_time_plots(output_directory: str | Path) -> tuple[Path, Path]:
    """Create PMF and CDF SVGs comparing the two bundled models."""

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    baseline = first_five_star_distribution(official_only_model())
    soft = first_five_star_distribution(community_soft_pity_model())

    pmf_path = output_directory / "first_five_star_pmf.svg"
    pmf_y_max = max(max(baseline.pmf), max(soft.pmf)) * 1.08
    pmf_path.write_text(
        _svg_plot(
            baseline=baseline.pmf,
            soft_pity=soft.pmf,
            title="First 5-star waiting-time PMF",
            y_label="P(X = n)",
            y_max=pmf_y_max,
        ),
        encoding="utf-8",
    )

    cdf_path = output_directory / "first_five_star_cdf.svg"
    cdf_path.write_text(
        _svg_plot(
            baseline=baseline.cdf,
            soft_pity=soft.cdf,
            title="First 5-star waiting-time CDF",
            y_label="P(X <= n)",
            y_max=1.0,
        ),
        encoding="utf-8",
    )
    return pmf_path, cdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="plots")
    args = parser.parse_args()
    for path in create_waiting_time_plots(args.output_dir):
        print(path)


if __name__ == "__main__":
    main()
