"""Replaceable community Capturing Radiance assumptions, separate from pity."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import ProbabilityModel


@dataclass(frozen=True, slots=True)
class CapturingRadianceModel:
    """CR is checked before the ordinary featured roll on non-guaranteed 5-stars.

    The hidden counter and every probability here are modeling assumptions,
    not an officially published transition schedule. 0.018% means 0.00018.
    """

    probabilities: tuple[float, ...] = (0.00018, 0.00018, 0.10, 1.0)
    reset_counter: int = 1
    win_counters: tuple[int, ...] = (0, 0, 1, 2)
    loss_counters: tuple[int, ...] = (1, 2, 3, 3)
    name: str = "community CR hidden-counter assumption"

    def __post_init__(self) -> None:
        if len(self.probabilities) != 4 or any(
            not 0 <= p <= 1 for p in self.probabilities
        ):
            raise ValueError("CR probabilities must contain four values in [0, 1]")
        for counters in (self.win_counters, self.loss_counters):
            if len(counters) != 4 or any(type(c) is not int or not 0 <= c <= 3 for c in counters):
                raise ValueError("CR counter transitions must contain four integers in [0, 3]")
        if type(self.reset_counter) is not int or not 0 <= self.reset_counter <= 3:
            raise ValueError("CR reset counter must be an integer in [0, 3]")

    def five_star_outcomes(
        self, counter: int, featured_probability: float
    ) -> tuple[tuple[bool, int, float], ...]:
        """Return (featured, next counter, probability) for a non-guaranteed 5-star."""

        r = self.probabilities[counter]
        return tuple(
            (featured, next_counter, probability)
            for featured, next_counter, probability in (
                (True, self.reset_counter, r),
                (True, self.win_counters[counter], (1 - r) * featured_probability),
                (False, self.loss_counters[counter], (1 - r) * (1 - featured_probability)),
            )
            if probability > 0
        )


def with_capturing_radiance(
    model: "ProbabilityModel", rules: CapturingRadianceModel | None = None
) -> "ProbabilityModel":
    """Enable CR without changing the supplied per-wish pity schedule."""

    rules = rules or CapturingRadianceModel()
    return replace(model, capturing_radiance=rules)
