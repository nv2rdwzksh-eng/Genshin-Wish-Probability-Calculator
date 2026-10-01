"""Exact Character and Weapon Event Wish probability calculations."""

from .engine import (
    CalculationResult,
    TargetPlanningResult,
    calculate,
    calculate_target_plan,
    expected_wishes_to_target,
    iter_target_success_probabilities,
)
from .model import ProbabilityModel, WishState, community_soft_pity_model, official_only_model
from .planning import (
    ThresholdRequirement,
    WishPlan,
    calculate_plan,
    deterministic_wishes_to_target,
    minimum_wishes_for_probability,
    threshold_table,
)
from .simulation import SimulationResult, simulate
from .capturing_radiance import CapturingRadianceModel, with_capturing_radiance
from .waiting_time import WaitingTimeDistribution, first_five_star_distribution
from .weapon_engine import (
    WeaponCalculationResult,
    calculate_weapon,
    calculate_weapon_target_plan,
    iter_weapon_target_success_probabilities,
    next_weapon_state_probabilities,
)
from .weapon_model import (
    WeaponProbabilityModel,
    WeaponWishState,
    community_weapon_soft_pity_model,
    official_only_weapon_model,
)
from .weapon_planning import (
    WeaponWishPlan,
    calculate_weapon_plan,
    deterministic_weapon_wishes_to_target,
    expected_weapon_wishes_to_target,
    minimum_weapon_wishes_for_probability,
    weapon_threshold_table,
)
from .weapon_simulation import WeaponSimulationResult, simulate_weapon
from .combined_planning import (
    CharacterGoal, WeaponGoal, CombinedPlanningResult, CombinedCompletionDistribution,
    calculate_combined_plan, prepare_combined_distribution,
    deterministic_combined_wishes_to_target,
    minimum_combined_wishes_for_probability, combined_threshold_table,
)

__all__ = [
    "CharacterGoal",
    "WeaponGoal",
    "CombinedPlanningResult",
    "CombinedCompletionDistribution",
    "calculate_combined_plan",
    "prepare_combined_distribution",
    "deterministic_combined_wishes_to_target",
    "minimum_combined_wishes_for_probability",
    "combined_threshold_table",
    "CapturingRadianceModel",
    "with_capturing_radiance",
    "CalculationResult",
    "ProbabilityModel",
    "SimulationResult",
    "WishState",
    "WishPlan",
    "WaitingTimeDistribution",
    "WeaponCalculationResult",
    "WeaponProbabilityModel",
    "WeaponSimulationResult",
    "WeaponWishPlan",
    "WeaponWishState",
    "ThresholdRequirement",
    "TargetPlanningResult",
    "calculate",
    "calculate_target_plan",
    "calculate_plan",
    "calculate_weapon",
    "calculate_weapon_plan",
    "calculate_weapon_target_plan",
    "community_soft_pity_model",
    "community_weapon_soft_pity_model",
    "deterministic_wishes_to_target",
    "deterministic_weapon_wishes_to_target",
    "expected_wishes_to_target",
    "expected_weapon_wishes_to_target",
    "first_five_star_distribution",
    "iter_target_success_probabilities",
    "iter_weapon_target_success_probabilities",
    "minimum_wishes_for_probability",
    "minimum_weapon_wishes_for_probability",
    "next_weapon_state_probabilities",
    "official_only_model",
    "official_only_weapon_model",
    "simulate",
    "simulate_weapon",
    "threshold_table",
    "weapon_threshold_table",
]

