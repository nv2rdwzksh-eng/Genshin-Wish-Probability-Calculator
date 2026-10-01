"""Wish state and configurable probability assumptions.

The engine deliberately knows nothing about a particular soft-pity formula.  A
``ProbabilityModel`` supplies the probability of a 5-star for every possible
starting pity value.  Index 0 is a wish made at zero pity; index 89 is the 90th
wish after the previous 5-star and must therefore contain 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from .capturing_radiance import CapturingRadianceModel


@dataclass(frozen=True, slots=True)
class WishState:
    """State immediately before a wish.

    ``pity`` is the number of consecutive wishes since the last 5-star,
    ``guaranteed`` says whether the next 5-star is featured, and ``copies`` is
    the number of featured copies obtained during the calculation so far.
    ``cr_counter`` is the assumed hidden Capturing Radiance counter (0..3),
    initially C1. Appending it preserves the old three positional arguments.
    """

    pity: int = 0
    guaranteed: bool = False
    copies: int = 0
    cr_counter: int = 1

    def __post_init__(self) -> None:
        if not 0 <= self.pity <= 89:
            raise ValueError("pity must be between 0 and 89 inclusive")
        if self.copies < 0:
            raise ValueError("copies cannot be negative")
        if type(self.cr_counter) is not int or not 0 <= self.cr_counter <= 3:
            raise ValueError("cr_counter must be an integer between 0 and 3")


@dataclass(frozen=True, slots=True)
class ProbabilityModel:
    """All numerical assumptions used by the transition engine."""

    five_star_probabilities: tuple[float, ...]
    featured_probability: float = 0.5
    name: str = "custom"
    capturing_radiance: CapturingRadianceModel | None = None

    def __post_init__(self) -> None:
        if len(self.five_star_probabilities) != 90:
            raise ValueError("five_star_probabilities must contain 90 entries")
        if any(not 0.0 <= value <= 1.0 for value in self.five_star_probabilities):
            raise ValueError("all 5-star probabilities must be between 0 and 1")
        if self.five_star_probabilities[89] != 1.0:
            raise ValueError("the probability at pity 89 must be 1.0 (hard pity)")
        if not 0.0 <= self.featured_probability <= 1.0:
            raise ValueError("featured_probability must be between 0 and 1")
        if self.capturing_radiance is not None and not isinstance(self.capturing_radiance, CapturingRadianceModel):
            raise ValueError("capturing_radiance must be a CapturingRadianceModel or None")

    @classmethod
    def from_table(
        cls,
        probabilities: Sequence[float],
        *,
        featured_probability: float = 0.5,
        name: str = "custom table",
        capturing_radiance: CapturingRadianceModel | None = None,
    ) -> "ProbabilityModel":
        """Build a model from probabilities indexed by current pity (0..89)."""

        return cls(tuple(float(value) for value in probabilities), featured_probability, name, capturing_radiance)

    def five_star_probability(self, pity: int) -> float:
        """Return P(5-star on the next wish | current pity)."""

        if not 0 <= pity <= 89:
            raise ValueError("pity must be between 0 and 89 inclusive")
        return self.five_star_probabilities[pity]


def official_only_model() -> ProbabilityModel:
    """Return the conservative baseline with no assumed soft-pity ramp.

    It uses the published 0.6% base probability for pity 0..88 and forces a
    5-star at pity 89.  This is intentionally *not* a claim that the actual
    per-wish rate remains flat until hard pity; it is a replaceable baseline.
    """

    return ProbabilityModel(
        five_star_probabilities=(0.006,) * 89 + (1.0,),
        featured_probability=0.5,
        name="official-only baseline (0.6% flat, then hard pity)",
    )


def community_soft_pity_model(
    *,
    base_probability: float = 0.006,
    soft_pity_start_wish: int = 74,
    increase_per_wish: float = 0.06,
    featured_probability: float = 0.5,
) -> ProbabilityModel:
    """Return a configurable *assumed* community soft-pity curve.

    The default assumption is 0.6% through wish 73, then an increase of six
    percentage points on every wish beginning with wish 74. Wish 90 is forced
    independently. This curve is a modeling choice, not an official formula.

    Wish numbers are one-based since the previous 5-star, whereas a
    ``WishState`` stores zero-based current pity. Probabilities are capped at
    1.0 in case custom parameters reach certainty before wish 90.
    """

    if not 0.0 <= base_probability <= 1.0:
        raise ValueError("base_probability must be between 0 and 1")
    if not 1 <= soft_pity_start_wish <= 89:
        raise ValueError("soft_pity_start_wish must be between 1 and 89")
    if increase_per_wish < 0.0:
        raise ValueError("increase_per_wish cannot be negative")

    probabilities: list[float] = []
    for wish_number in range(1, 90):
        if wish_number < soft_pity_start_wish:
            probability = base_probability
        else:
            ramp_step = wish_number - soft_pity_start_wish + 1
            probability = min(1.0, base_probability + ramp_step * increase_per_wish)
        probabilities.append(probability)
    probabilities.append(1.0)

    return ProbabilityModel(
        five_star_probabilities=tuple(probabilities),
        featured_probability=featured_probability,
        name=(
            "community soft-pity assumption "
            f"(base {base_probability:.3%}, +{increase_per_wish:.1%}/wish "
            f"from wish {soft_pity_start_wish}, hard pity 90)"
        ),
    )

