"""Current Weapon Event Wish state and configurable probability assumptions.

The rule object models the post-Version 5.0 one-Fate-Point Epitomized Path.
Soft pity is deliberately supplied as a table rather than embedded in the DP.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class WeaponWishState:
    """State immediately before a weapon wish.

    ``fate_point`` is banner-period-specific and assumes that a course is
    charted for the selected target weapon. It may coexist with
    ``promoted_guaranteed`` after a non-promoted 5-star; Fate takes precedence.
    """

    pity: int = 0
    promoted_guaranteed: bool = False
    fate_point: int = 0
    copies: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.pity <= 79:
            raise ValueError("weapon pity must be between 0 and 79 inclusive")
        if self.fate_point not in (0, 1):
            raise ValueError("Fate Point must be 0 or 1 under the post-Version 5.0 rules")
        if self.copies < 0:
            raise ValueError("copies cannot be negative")


@dataclass(frozen=True, slots=True)
class WeaponProbabilityModel:
    """All numerical and outcome-selection assumptions used by weapon DP."""

    five_star_probabilities: tuple[float, ...]
    promoted_probability: float = 0.75
    desired_given_promoted_probability: float = 0.5
    fate_points_required: int = 1
    name: str = "custom weapon model"

    def __post_init__(self) -> None:
        if len(self.five_star_probabilities) != 80:
            raise ValueError("five_star_probabilities must contain 80 entries")
        if any(not 0.0 <= value <= 1.0 for value in self.five_star_probabilities):
            raise ValueError("all 5-star probabilities must be between 0 and 1")
        if self.five_star_probabilities[79] != 1.0:
            raise ValueError("the probability at weapon pity 79 must be 1.0 (hard pity)")
        if not 0.0 <= self.promoted_probability <= 1.0:
            raise ValueError("promoted_probability must be between 0 and 1")
        if not 0.0 <= self.desired_given_promoted_probability <= 1.0:
            raise ValueError(
                "desired_given_promoted_probability must be between 0 and 1"
            )
        if self.fate_points_required != 1:
            raise ValueError("v0.4 models the current one-Fate-Point rule only")

    @classmethod
    def from_table(
        cls,
        probabilities: Sequence[float],
        *,
        promoted_probability: float = 0.75,
        desired_given_promoted_probability: float = 0.5,
        name: str = "custom weapon table",
    ) -> "WeaponProbabilityModel":
        return cls(
            tuple(float(value) for value in probabilities),
            promoted_probability,
            desired_given_promoted_probability,
            1,
            name,
        )

    def five_star_probability(self, pity: int) -> float:
        if not 0 <= pity <= 79:
            raise ValueError("weapon pity must be between 0 and 79 inclusive")
        return self.five_star_probabilities[pity]


def official_only_weapon_model() -> WeaponProbabilityModel:
    """Published base rate/outcome rules with no assumed soft-pity ramp.

    The flat 0.7% section is a transparent comparison baseline, not a claim
    about the game's unpublished conditional rates before hard pity.
    """

    return WeaponProbabilityModel(
        five_star_probabilities=(0.007,) * 79 + (1.0,),
        promoted_probability=0.75,
        desired_given_promoted_probability=0.5,
        name="official-only weapon baseline (0.7% flat, then hard pity 80)",
    )


def community_weapon_soft_pity_model(
    *,
    base_probability: float = 0.007,
    soft_pity_start_wish: int = 63,
    increase_per_wish: float = 0.07,
    promoted_probability: float = 0.75,
    desired_given_promoted_probability: float = 0.5,
) -> WeaponProbabilityModel:
    """Configurable community-estimated curve, not an official formula.

    Defaults keep 0.7% through wish 62 and add seven percentage points from
    wish 63. Values are capped at 1; wish 80 is independently forced. The
    table is replaceable because the exact ramp is not officially published.
    """

    if not 0.0 <= base_probability <= 1.0:
        raise ValueError("base_probability must be between 0 and 1")
    if not 1 <= soft_pity_start_wish <= 79:
        raise ValueError("soft_pity_start_wish must be between 1 and 79")
    if increase_per_wish < 0.0:
        raise ValueError("increase_per_wish cannot be negative")

    probabilities: list[float] = []
    for wish_number in range(1, 80):
        if wish_number < soft_pity_start_wish:
            probability = base_probability
        else:
            step = wish_number - soft_pity_start_wish + 1
            probability = min(1.0, base_probability + step * increase_per_wish)
        probabilities.append(probability)
    probabilities.append(1.0)
    return WeaponProbabilityModel(
        tuple(probabilities),
        promoted_probability,
        desired_given_promoted_probability,
        1,
        (
            "community weapon soft-pity assumption "
            f"(base {base_probability:.3%}, +{increase_per_wish:.1%}/wish "
            f"from wish {soft_pity_start_wish}, official hard pity 80)"
        ),
    )
