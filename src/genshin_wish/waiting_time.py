"""First-5-star waiting-time analysis for a configured probability model."""

from __future__ import annotations

from dataclasses import dataclass

from .model import ProbabilityModel


@dataclass(frozen=True, slots=True)
class WaitingTimeDistribution:
    """Distribution of wishes until the next 5-star.

    Every tuple is aligned with ``wish_numbers``. At position ``i``:

    - ``pmf[i]`` is P(X = n)
    - ``cdf[i]`` is P(X <= n)
    - ``survival[i]`` is P(X > n)
    - ``conditional_probabilities[i]`` is q_n, the probability of a 5-star on
      wish n conditional on not having received one earlier
    """

    starting_pity: int
    wish_numbers: tuple[int, ...]
    pmf: tuple[float, ...]
    cdf: tuple[float, ...]
    survival: tuple[float, ...]
    conditional_probabilities: tuple[float, ...]

    @property
    def expected_wishes(self) -> float:
        return sum(n * probability for n, probability in zip(self.wish_numbers, self.pmf))


def first_five_star_distribution(
    model: ProbabilityModel, *, starting_pity: int = 0
) -> WaitingTimeDistribution:
    """Calculate the exact waiting-time distribution up to hard pity."""

    if not 0 <= starting_pity <= 89:
        raise ValueError("starting_pity must be between 0 and 89 inclusive")

    wish_numbers: list[int] = []
    pmf: list[float] = []
    cdf: list[float] = []
    survival: list[float] = []
    conditional_probabilities: list[float] = []
    survived_before_wish = 1.0

    for elapsed_wishes, pity in enumerate(range(starting_pity, 90), start=1):
        q_n = model.five_star_probability(pity)
        probability_at_n = survived_before_wish * q_n
        survived_after_wish = survived_before_wish * (1.0 - q_n)

        wish_numbers.append(elapsed_wishes)
        conditional_probabilities.append(q_n)
        pmf.append(probability_at_n)
        survival.append(survived_after_wish)
        cdf.append(1.0 - survived_after_wish)

        survived_before_wish = survived_after_wish

    return WaitingTimeDistribution(
        starting_pity=starting_pity,
        wish_numbers=tuple(wish_numbers),
        pmf=tuple(pmf),
        cdf=tuple(cdf),
        survival=tuple(survival),
        conditional_probabilities=tuple(conditional_probabilities),
    )
