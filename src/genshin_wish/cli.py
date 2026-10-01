"""Interactive and argument-driven character/weapon wish planner."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import fsum
from typing import Mapping, TypeVar

from .engine import CalculationResult, calculate
from .model import ProbabilityModel, WishState, community_soft_pity_model, official_only_model
from .capturing_radiance import with_capturing_radiance
from .combined_planning import (
    CharacterGoal, WeaponGoal, CombinedPlanningResult,
    deterministic_combined_wishes_to_target, prepare_combined_distribution,
)
from .planning import (
    ThresholdRequirement,
    WishPlan,
    calculate_plan,
    minimum_wishes_for_probability,
    threshold_table,
)
from .weapon_engine import WeaponCalculationResult, calculate_weapon
from .weapon_model import (
    WeaponProbabilityModel,
    WeaponWishState,
    community_weapon_soft_pity_model,
    official_only_weapon_model,
)
from .weapon_planning import (
    WeaponWishPlan,
    calculate_weapon_plan,
    minimum_weapon_wishes_for_probability,
    weapon_threshold_table,
)

InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]
ParsedValue = TypeVar("ParsedValue")


@dataclass(frozen=True, slots=True)
class InteractiveInputs:
    state: WishState
    wishes: int
    target_copies: int
    model: ProbabilityModel


@dataclass(frozen=True, slots=True)
class WeaponInteractiveInputs:
    state: WeaponWishState
    wishes: int
    target_copies: int
    model: WeaponProbabilityModel


@dataclass(frozen=True, slots=True)
class CompactDistribution:
    """Presentation-only view of a complete exact copy distribution."""

    individual_outcomes: tuple[tuple[int, float], ...]
    combined_probability: float


def compact_copy_distribution(
    distribution: Mapping[int, float],
    *,
    target_copies: int,
    display_threshold: float = 0.005,
) -> CompactDistribution:
    """Group sub-threshold outcomes without changing the source distribution."""

    if not 0.0 <= display_threshold <= 1.0:
        raise ValueError("display_threshold must be between 0 and 1")
    if target_copies < 0:
        raise ValueError("target_copies cannot be negative")

    individual = tuple(
        sorted(
            (
                (copies, probability)
                for copies, probability in distribution.items()
                if probability >= display_threshold or copies == target_copies
            ),
            key=lambda item: item[0],
        )
    )
    if target_copies not in distribution:
        individual = tuple(
            sorted((*individual, (target_copies, 0.0)), key=lambda item: item[0])
        )
    displayed_counts = {copies for copies, _ in individual}
    combined = fsum(
        probability
        for copies, probability in distribution.items()
        if copies not in displayed_counts
    )
    return CompactDistribution(individual, combined)


def parse_nonnegative_integer(value: str, field_name: str) -> int:
    try:
        parsed = int(value.strip())
    except ValueError as error:
        raise ValueError(f"{field_name} must be a whole number") from error
    if parsed < 0:
        raise ValueError(f"{field_name} cannot be negative")
    return parsed


def parse_pity(value: str) -> int:
    pity = parse_nonnegative_integer(value, "current pity")
    if pity > 89:
        raise ValueError("current pity must be between 0 and 89")
    return pity


def parse_cr_counter(value: str) -> int:
    counter = parse_nonnegative_integer(value or "1", "CR counter")
    if counter > 3:
        raise ValueError("CR counter must be between 0 and 3")
    return counter


def parse_weapon_pity(value: str) -> int:
    pity = parse_nonnegative_integer(value, "current weapon pity")
    if pity > 79:
        raise ValueError("current weapon pity must be between 0 and 79")
    return pity


def parse_fate_point(value: str) -> int:
    fate_point = parse_nonnegative_integer(value, "Fate Point")
    if fate_point not in (0, 1):
        raise ValueError("Fate Point must be 0 or 1 under the current rules")
    return fate_point


def parse_banner_choice(value: str) -> str:
    choice = value.strip()
    if choice not in {"1", "2", "3"}:
        raise ValueError("choose 1, 2, or 3")
    return choice


def parse_yes_no(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"y", "yes"}:
        return True
    if normalized in {"n", "no"}:
        return False
    raise ValueError("enter y or n")


def parse_confidence_percent(value: str) -> float:
    normalized = value.strip()
    if normalized.endswith("%"):
        normalized = normalized[:-1].strip()
    try:
        percentage = float(normalized)
    except ValueError as error:
        raise ValueError("confidence must be a number from 0 to 100") from error
    if not 0.0 <= percentage <= 100.0:
        raise ValueError("confidence must be between 0% and 100%")
    return percentage / 100.0


def model_from_choice(value: str) -> ProbabilityModel:
    normalized = value.strip().lower()
    if normalized in {"1", "official", "official-only"}:
        return official_only_model()
    if normalized in {"2", "community", "community-soft-pity"}:
        return community_soft_pity_model()
    if normalized in {"cr", "community-cr"}:
        return with_capturing_radiance(community_soft_pity_model())
    if normalized == "official-cr":
        return with_capturing_radiance(official_only_model())
    raise ValueError("choose 1, 2, cr, or official-cr")


def weapon_model_from_choice(value: str) -> WeaponProbabilityModel:
    normalized = value.strip().lower()
    if normalized in {"1", "official", "official-only"}:
        return official_only_weapon_model()
    if normalized in {"2", "community", "community-soft-pity"}:
        return community_weapon_soft_pity_model()
    raise ValueError("choose 1 or 2")


def _prompt_until_valid(
    prompt: str,
    parser: Callable[[str], ParsedValue],
    *,
    input_fn: InputFunction,
    output_fn: OutputFunction,
) -> ParsedValue:
    while True:
        try:
            return parser(input_fn(prompt))
        except ValueError as error:
            output_fn(f"Invalid input: {error}")


def collect_interactive_inputs(
    *, input_fn: InputFunction = input, output_fn: OutputFunction = print,
    wishes: int | None = None, include_current_copies: bool = False,
) -> InteractiveInputs:
    output_fn("=== Genshin Wish Probability Calculator ===")
    output_fn("")
    pity = _prompt_until_valid(
        "Current pity: ", parse_pity, input_fn=input_fn, output_fn=output_fn
    )
    guaranteed = _prompt_until_valid(
        "Guaranteed featured 5-star? [y/n]: ",
        parse_yes_no,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    if wishes is None:
        wishes = _prompt_until_valid(
            "Available wishes: ",
            lambda value: parse_nonnegative_integer(value, "available wishes"),
            input_fn=input_fn,
            output_fn=output_fn,
        )
    target = _prompt_until_valid(
        "Target copies: ",
        lambda value: parse_nonnegative_integer(value, "target copies"),
        input_fn=input_fn,
        output_fn=output_fn,
    )
    copies = 0
    if include_current_copies:
        copies = _prompt_until_valid(
            "Target-character copies already credited [Enter for 0]: ",
            lambda value: parse_nonnegative_integer(value or "0", "current copies"),
            input_fn=input_fn, output_fn=output_fn,
        )
    output_fn("")
    output_fn("Probability model:")
    output_fn("1. Official-only baseline")
    output_fn("2. Community soft-pity assumption (not an official per-wish formula)")
    output_fn("cr. Community soft pity + community Capturing Radiance counter assumption")
    output_fn("official-cr. Baseline pity + community Capturing Radiance counter assumption")
    model = _prompt_until_valid(
        "> ", model_from_choice, input_fn=input_fn, output_fn=output_fn
    )
    counter = 1
    if model.capturing_radiance is not None:
        counter = _prompt_until_valid(
            "Assumed CR counter [0-3, Enter for initial C1]: ",
            parse_cr_counter, input_fn=input_fn, output_fn=output_fn,
        )
    return InteractiveInputs(
        state=WishState(pity=pity, guaranteed=guaranteed, copies=copies, cr_counter=counter),
        wishes=wishes,
        target_copies=target,
        model=model,
    )


def collect_weapon_interactive_inputs(
    *, input_fn: InputFunction = input, output_fn: OutputFunction = print,
    wishes: int | None = None, include_current_copies: bool = False,
) -> WeaponInteractiveInputs:
    output_fn("=== Weapon Event Wish Planner (post-Version 5.0 rules) ===")
    output_fn("Assumes Epitomized Path is charted for the desired promoted weapon.")
    output_fn("")
    pity = _prompt_until_valid(
        "Current weapon pity: ", parse_weapon_pity, input_fn=input_fn, output_fn=output_fn
    )
    guaranteed = _prompt_until_valid(
        "Next 5-star guaranteed to be a promoted weapon? [y/n]: ",
        parse_yes_no,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    fate_point = _prompt_until_valid(
        "Current Epitomized Path Fate Point [0/1]: ",
        parse_fate_point,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    if wishes is None:
        wishes = _prompt_until_valid(
            "Available wishes: ",
            lambda value: parse_nonnegative_integer(value, "available wishes"),
            input_fn=input_fn,
            output_fn=output_fn,
        )
    target = _prompt_until_valid(
        "Target weapon copies: ",
        lambda value: parse_nonnegative_integer(value, "target weapon copies"),
        input_fn=input_fn,
        output_fn=output_fn,
    )
    copies = 0
    if include_current_copies:
        copies = _prompt_until_valid(
            "Target-weapon copies already credited [Enter for 0]: ",
            lambda value: parse_nonnegative_integer(value or "0", "current weapon copies"),
            input_fn=input_fn, output_fn=output_fn,
        )
    output_fn("")
    output_fn("Weapon 5-star probability model:")
    output_fn("1. Official-only baseline")
    output_fn("2. Community soft-pity assumption (not an official per-wish formula)")
    model = _prompt_until_valid(
        "> ", weapon_model_from_choice, input_fn=input_fn, output_fn=output_fn
    )
    return WeaponInteractiveInputs(
        WeaponWishState(pity, guaranteed, fate_point, copies), wishes, target, model
    )


def format_planning_report(plan: WishPlan, *, model: ProbabilityModel) -> str:
    result = plan.calculation
    lines = [
        "",
        "=== Planning Report ===",
        f"Model: {model.name}",
        "Capturing Radiance: " + (model.capturing_radiance.name if model.capturing_radiance else "disabled (legacy featured rules)"),
        f"Available wishes: {result.wishes}",
        f"Target copies: {result.target_copies}",
        "",
        f"P(target reached): {result.success_probability:.8%}",
        f"Expected featured copies when stopping at target: {result.expected_copies:.6f}",
        f"Unconditional expected wishes to target, E[T]: {plan.unconditional_expected_wishes:.3f}",
    ]
    conditional = result.expected_wishes_if_success_within_budget
    if conditional is None:
        conditional_text = "not defined (target cannot be reached within this budget)"
    else:
        conditional_text = f"{conditional:.3f}"
    lines.append(
        "Conditional expected completion wish, E[T | T <= budget]: " + conditional_text
    )
    lines.append(f"Expected wishes actually consumed: {result.expected_wishes_consumed:.3f}")
    if result.expected_remaining_wishes_if_success is None:
        remaining_text = "not defined (no successful trajectories within budget)"
    else:
        remaining_text = f"{result.expected_remaining_wishes_if_success:.3f}"
    lines.append("Expected wishes remaining given success: " + remaining_text)
    lines.extend(["", "Target-aware copy distribution (stop immediately at target):"])

    for copies in range(result.target_copies):
        lines.append(
            f"  Exactly {copies} before budget exhaustion: "
            f"{result.copy_distribution[copies]:.8%}"
        )
    lines.append(
        f"  Target reached ({result.target_copies} copies; stopped): "
        f"{result.copy_distribution[result.target_copies]:.8%}"
    )
    return "\n".join(lines)


def format_full_distribution_report(
    result: CalculationResult, *, model: ProbabilityModel
) -> str:
    """Format the advanced continue-pulling analysis explicitly."""

    lines = [
        "",
        "=== Full-Distribution Analysis ===",
        "Semantics: spend exactly the full budget regardless of earlier results.",
        f"Model: {model.name}",
        "Capturing Radiance: " + (model.capturing_radiance.name if model.capturing_radiance else "disabled (legacy featured rules)"),
        f"Wishes spent: {result.wishes}",
        f"P(at least {result.target_copies} copies): {result.success_probability:.8%}",
        f"Expected featured copies: {result.expected_copies:.6f}",
        "",
        "Continued-pulling copy distribution:",
    ]
    compact = compact_copy_distribution(
        result.copy_distribution, target_copies=result.target_copies
    )
    for copies, probability in compact.individual_outcomes:
        lines.append(f"  Exactly {copies}: {probability:.8%}")
    if compact.combined_probability > 0.0:
        lines.append(
            "  Other outcomes below 0.5% each (combined): "
            f"{compact.combined_probability:.8%}"
        )
    return "\n".join(lines)


def format_weapon_planning_report(
    plan: WeaponWishPlan, *, model: WeaponProbabilityModel
) -> str:
    result = plan.calculation
    conditional = result.expected_wishes_if_success_within_budget
    remaining = result.expected_remaining_wishes_if_success
    lines = [
        "",
        "=== Weapon Planning Report ===",
        "Semantics: stop wishing immediately when the target is reached.",
        f"Model: {model.name}",
        f"Available wishes: {result.wishes}",
        f"Target weapon copies: {result.target_copies}",
        "",
        f"P(target reached): {result.success_probability:.8%}",
        f"Expected target copies when stopping: {result.expected_copies:.6f}",
        f"Unconditional expected wishes to target, E[T]: {plan.unconditional_expected_wishes:.3f}",
        "Conditional expected completion wish, E[T | T <= budget]: "
        + (f"{conditional:.3f}" if conditional is not None else "not defined"),
        f"Expected wishes actually consumed: {result.expected_wishes_consumed:.3f}",
        "Expected wishes remaining given success: "
        + (f"{remaining:.3f}" if remaining is not None else "not defined"),
        "",
        "Target-aware weapon-copy distribution:",
    ]
    for copies in range(result.target_copies):
        lines.append(
            f"  Exactly {copies} before budget exhaustion: "
            f"{result.copy_distribution[copies]:.8%}"
        )
    lines.append(
        f"  Target reached ({result.target_copies} copies; stopped): "
        f"{result.copy_distribution[result.target_copies]:.8%}"
    )
    return "\n".join(lines)


def format_weapon_full_distribution_report(
    result: WeaponCalculationResult, *, model: WeaponProbabilityModel
) -> str:
    lines = [
        "",
        "=== Weapon Full-Distribution Analysis ===",
        "Semantics: spend exactly the full budget regardless of earlier results.",
        f"Model: {model.name}",
        f"Wishes spent: {result.wishes}",
        f"P(at least {result.target_copies} target copies): {result.success_probability:.8%}",
        f"Expected target copies: {result.expected_copies:.6f}",
        "",
        "Continued-pulling target-weapon copy distribution:",
    ]
    compact = compact_copy_distribution(
        result.copy_distribution, target_copies=result.target_copies
    )
    for copies, probability in compact.individual_outcomes:
        lines.append(f"  Exactly {copies}: {probability:.8%}")
    if compact.combined_probability > 0.0:
        lines.append(
            "  Other outcomes below 0.5% each (combined): "
            f"{compact.combined_probability:.8%}"
        )
    return "\n".join(lines)


def format_threshold_table(rows: Sequence[ThresholdRequirement]) -> str:
    lines = ["", "Probability target    Wishes required"]
    for row in rows:
        lines.append(f"{row.probability:>17.0%}    {row.wishes:>15}")
    return "\n".join(lines)


def format_combined_planning_report(
    result: CombinedPlanningResult, *, character_goal: CharacterGoal,
    weapon_goal: WeaponGoal,
) -> str:
    conditional_remaining = result.expected_remaining_wishes_given_character_success
    conditional_total = result.expected_total_completion_wish_given_success
    return "\n".join([
        "", "=== Combined Planning Report: Character -> Weapon ===",
        f"Total wish budget: {result.total_wishes}",
        f"Character target: {character_goal.target_copies} total copies",
        f"Character start: pity {character_goal.initial_state.pity}, featured guarantee "
        f"{'yes' if character_goal.initial_state.guaranteed else 'no'}, "
        f"CR counter C{character_goal.initial_state.cr_counter}, "
        f"credited copies {character_goal.initial_state.copies}",
        f"Character model: {character_goal.model.name}",
        "Capturing Radiance: " + (
            character_goal.model.capturing_radiance.name
            if character_goal.model.capturing_radiance else "disabled"
        ),
        f"Weapon target: {weapon_goal.target_copies} total copies",
        f"Weapon start: pity {weapon_goal.initial_state.pity}, promoted guarantee "
        f"{'yes' if weapon_goal.initial_state.promoted_guaranteed else 'no'}, "
        f"Fate Point {weapon_goal.initial_state.fate_point}, "
        f"credited copies {weapon_goal.initial_state.copies}",
        f"Weapon model: {weapon_goal.model.name}",
        "Stop at each target; weapon phase uses the supplied weapon state.",
        "Results are exact under the selected probability-model assumptions.",
        "", "Outcome breakdown:",
        f"  All goals completed: {result.success_probability:.8%}",
        "  Character completed, weapon not completed: "
        f"{result.character_success_weapon_failure_probability:.8%}",
        f"  Character not completed: {result.character_failure_probability:.8%}",
        "", "Expected wishes remaining after character target "
        "(zero on character failure): "
        f"{result.expected_remaining_wishes_after_character:.3f}",
        "Expected wishes remaining given character success: " + (
            f"{conditional_remaining:.3f}" if conditional_remaining is not None
            else "not defined (character target cannot complete within budget)"
        ),
        "Expected total completion wish given both goals succeed: " + (
            f"{conditional_total:.3f}" if conditional_total is not None
            else "not defined (both goals cannot complete within budget)"
        ),
    ])


def run_combined_interactive(
    *, input_fn: InputFunction = input, output_fn: OutputFunction = print,
) -> None:
    output_fn("=== Character -> Weapon Planning ===")
    budget = _prompt_until_valid(
        "Total wish budget: ",
        lambda value: parse_nonnegative_integer(value, "total wish budget"),
        input_fn=input_fn, output_fn=output_fn,
    )
    output_fn("Targets are total copies including any already credited copies.")
    output_fn("\nCharacter initial state and target:")
    character = collect_interactive_inputs(
        input_fn=input_fn, output_fn=output_fn,
        wishes=budget, include_current_copies=True,
    )
    output_fn("\nWeapon initial state and target:")
    weapon = collect_weapon_interactive_inputs(
        input_fn=input_fn, output_fn=output_fn,
        wishes=budget, include_current_copies=True,
    )
    character_goal = CharacterGoal(character.state, character.target_copies, character.model)
    weapon_goal = WeaponGoal(weapon.state, weapon.target_copies, weapon.model)
    bound = deterministic_combined_wishes_to_target(
        character_goal=character_goal, weapon_goal=weapon_goal,
    )
    # Prepare once so the report and the following inverse prompt reuse both
    # phase calculations, including any requested confidence up to certainty.
    distribution = prepare_combined_distribution(
        character_goal=character_goal, weapon_goal=weapon_goal,
        max_wishes=max(budget, bound),
    )
    output_fn(format_combined_planning_report(
        distribution.report(budget), character_goal=character_goal, weapon_goal=weapon_goal,
    ))
    while True:
        raw = input_fn(
            "\nCombined confidence [0-100%, Enter for 50/75/90/95/99% table]: "
        ).strip()
        if not raw:
            output_fn(format_threshold_table(distribution.threshold_table()))
            return
        try:
            confidence = parse_confidence_percent(raw)
            minimum = distribution.minimum_wishes(confidence)
            output_fn(f"Minimum total wishes for at least {confidence:.2%} combined success: {minimum}")
            return
        except ValueError as error:
            output_fn(f"Invalid input: {error}")


def run_interactive(
    *, input_fn: InputFunction = input, output_fn: OutputFunction = print
) -> None:
    request = collect_interactive_inputs(input_fn=input_fn, output_fn=output_fn)
    plan = calculate_plan(
        initial_state=request.state,
        wishes=request.wishes,
        target_copies=request.target_copies,
        model=request.model,
    )
    output_fn(format_planning_report(plan, model=request.model))

    while True:
        raw_confidence = input_fn(
            "\nInverse-planning confidence [0-100%, Enter for 50/75/90/95/99% table]: "
        ).strip()
        if not raw_confidence:
            rows = threshold_table(
                initial_state=request.state,
                target_copies=request.target_copies,
                model=request.model,
            )
            output_fn(format_threshold_table(rows))
            return
        try:
            confidence = parse_confidence_percent(raw_confidence)
            wishes = minimum_wishes_for_probability(
                initial_state=request.state,
                target_copies=request.target_copies,
                desired_probability=confidence,
                model=request.model,
            )
            output_fn(f"Minimum wishes for at least {confidence:.2%} success: {wishes}")
            return
        except ValueError as error:
            output_fn(f"Invalid input: {error}")


def run_weapon_interactive(
    *, input_fn: InputFunction = input, output_fn: OutputFunction = print
) -> None:
    request = collect_weapon_interactive_inputs(input_fn=input_fn, output_fn=output_fn)
    plan = calculate_weapon_plan(
        initial_state=request.state,
        wishes=request.wishes,
        target_copies=request.target_copies,
        model=request.model,
    )
    output_fn(format_weapon_planning_report(plan, model=request.model))
    while True:
        raw = input_fn(
            "\nInverse-planning confidence [0-100%, Enter for 50/75/90/95/99% table]: "
        ).strip()
        if not raw:
            output_fn(
                format_threshold_table(
                    weapon_threshold_table(
                        initial_state=request.state,
                        target_copies=request.target_copies,
                        model=request.model,
                    )
                )
            )
            return
        try:
            confidence = parse_confidence_percent(raw)
            minimum = minimum_weapon_wishes_for_probability(
                initial_state=request.state,
                target_copies=request.target_copies,
                desired_probability=confidence,
                model=request.model,
            )
            output_fn(
                f"Minimum weapon wishes for at least {confidence:.2%} success: {minimum}"
            )
            return
        except ValueError as error:
            output_fn(f"Invalid input: {error}")


def run_banner_interactive(
    *, input_fn: InputFunction = input, output_fn: OutputFunction = print
) -> None:
    output_fn("=== Genshin Wish Probability Calculator v0.5 ===")
    output_fn("1. Character Event Wish planning")
    output_fn("2. Weapon Event Wish planning")
    output_fn("3. Combined Character -> Weapon planning")
    banner = _prompt_until_valid(
        "> ", parse_banner_choice,
        input_fn=input_fn,
        output_fn=output_fn,
    )
    if banner == "1":
        run_interactive(input_fn=input_fn, output_fn=output_fn)
    elif banner == "2":
        run_weapon_interactive(input_fn=input_fn, output_fn=output_fn)
    else:
        run_combined_interactive(input_fn=input_fn, output_fn=output_fn)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pity", type=int)
    parser.add_argument(
        "--banner", choices=("character", "weapon", "combined"), default="character"
    )
    parser.add_argument("--guaranteed", action="store_true")
    parser.add_argument("--capturing-radiance", action="store_true", help="enable community CR counter assumption for characters")
    parser.add_argument("--cr-counter", type=int, default=1, help="character CR counter, 0..3 (default 1)")
    parser.add_argument("--fate-point", type=int, default=0, help="weapon banner: 0 or 1")
    parser.add_argument("--wishes", type=int)
    parser.add_argument("--target", type=int, help="total target copies")
    parser.add_argument("--character-copies", type=int, default=0, help="combined: already credited character copies")
    parser.add_argument("--weapon-pity", type=int, help="combined: initial weapon pity")
    parser.add_argument("--weapon-guaranteed", action="store_true", help="combined: next weapon 5-star guaranteed promoted")
    parser.add_argument("--weapon-target", type=int, help="combined: total target weapon copies")
    parser.add_argument("--weapon-copies", type=int, default=0, help="combined: already credited weapon copies")
    parser.add_argument("--weapon-model", choices=("official-only", "community-soft-pity"), default="official-only")
    parser.add_argument(
        "--model", choices=("official-only", "community-soft-pity"), default="official-only"
    )
    parser.add_argument("--confidence", help="inverse target as a percentage, e.g. 90")
    parser.add_argument("--threshold-table", action="store_true")
    parser.add_argument(
        "--mode",
        choices=("planning", "full-distribution"),
        default="planning",
        help="planning stops at the target; full-distribution spends every wish",
    )
    return parser


def _run_combined_arguments(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.mode != "planning":
        parser.error("combined mode stops at each target; use --mode planning")
    required = (args.wishes, args.pity, args.target, args.weapon_pity, args.weapon_target)
    if all(value is None for value in required):
        if args.capturing_radiance or args.cr_counter != 1:
            parser.error("supply combined state/target flags or choose CR in the interactive menu")
        run_combined_interactive()
        return
    if any(value is None for value in required):
        parser.error("combined mode requires --wishes, --pity, --target, --weapon-pity, and --weapon-target")
    try:
        budget = parse_nonnegative_integer(str(args.wishes), "total wish budget")
        character_model = model_from_choice(args.model)
        if args.capturing_radiance:
            character_model = with_capturing_radiance(character_model)
        character_goal = CharacterGoal(
            WishState(
                parse_pity(str(args.pity)), args.guaranteed,
                parse_nonnegative_integer(str(args.character_copies), "current character copies"),
                parse_cr_counter(str(args.cr_counter)),
            ),
            parse_nonnegative_integer(str(args.target), "character target copies"),
            character_model,
        )
        weapon_goal = WeaponGoal(
            WeaponWishState(
                parse_weapon_pity(str(args.weapon_pity)), args.weapon_guaranteed,
                parse_fate_point(str(args.fate_point)),
                parse_nonnegative_integer(str(args.weapon_copies), "current weapon copies"),
            ),
            parse_nonnegative_integer(str(args.weapon_target), "weapon target copies"),
            weapon_model_from_choice(args.weapon_model),
        )
        confidence = (
            parse_confidence_percent(args.confidence) if args.confidence is not None else None
        )
        horizon = budget
        if args.threshold_table or confidence is not None:
            horizon = max(horizon, deterministic_combined_wishes_to_target(
                character_goal=character_goal, weapon_goal=weapon_goal,
            ))
        distribution = prepare_combined_distribution(
            character_goal=character_goal, weapon_goal=weapon_goal, max_wishes=horizon,
        )
    except ValueError as error:
        parser.error(str(error))
    print(format_combined_planning_report(
        distribution.report(budget), character_goal=character_goal, weapon_goal=weapon_goal,
    ))
    if confidence is not None:
        minimum = distribution.minimum_wishes(confidence)
        print(f"\nMinimum total wishes for at least {confidence:.2%} combined success: {minimum}")
    if args.threshold_table:
        print(format_threshold_table(distribution.threshold_table()))


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.banner == "combined":
        _run_combined_arguments(args, parser)
        return
    supplied = (args.pity, args.wishes, args.target)
    if all(value is None for value in supplied):
        if args.capturing_radiance or args.cr_counter != 1:
            parser.error("supply --pity, --wishes, and --target with CR flags, or choose CR in the interactive model menu")
        run_banner_interactive()
        return
    if any(value is None for value in supplied):
        parser.error("--pity, --wishes, and --target must be supplied together")

    try:
        pity = (
            parse_weapon_pity(str(args.pity))
            if args.banner == "weapon"
            else parse_pity(str(args.pity))
        )
        wishes = parse_nonnegative_integer(str(args.wishes), "available wishes")
        target = parse_nonnegative_integer(str(args.target), "target copies")
        model = (
            weapon_model_from_choice(args.model)
            if args.banner == "weapon"
            else model_from_choice(args.model)
        )
        fate_point = parse_fate_point(str(args.fate_point))
        counter = parse_cr_counter(str(args.cr_counter))
        if args.banner == "weapon" and (args.capturing_radiance or args.cr_counter != 1):
            raise ValueError("Capturing Radiance options apply only to the character banner")
        if args.capturing_radiance:
            model = with_capturing_radiance(model)
        confidence = (
            parse_confidence_percent(args.confidence) if args.confidence is not None else None
        )
    except ValueError as error:
        parser.error(str(error))

    if args.banner == "weapon":
        weapon_state = WeaponWishState(pity, args.guaranteed, fate_point)
        if args.mode == "planning":
            weapon_plan = calculate_weapon_plan(
                initial_state=weapon_state,
                wishes=wishes,
                target_copies=target,
                model=model,
            )
            print(format_weapon_planning_report(weapon_plan, model=model))
        else:
            weapon_full = calculate_weapon(
                initial_state=weapon_state,
                wishes=wishes,
                target_copies=target,
                model=model,
            )
            print(format_weapon_full_distribution_report(weapon_full, model=model))
        if confidence is not None:
            minimum = minimum_weapon_wishes_for_probability(
                initial_state=weapon_state,
                target_copies=target,
                desired_probability=confidence,
                model=model,
            )
            print(f"\nMinimum weapon wishes for at least {confidence:.2%} success: {minimum}")
        if args.threshold_table:
            print(
                format_threshold_table(
                    weapon_threshold_table(
                        initial_state=weapon_state, target_copies=target, model=model
                    )
                )
            )
        return

    state = WishState(pity=pity, guaranteed=args.guaranteed, cr_counter=counter)
    if args.mode == "planning":
        plan = calculate_plan(
            initial_state=state, wishes=wishes, target_copies=target, model=model
        )
        print(format_planning_report(plan, model=model))
    else:
        full_result = calculate(
            initial_state=state, wishes=wishes, target_copies=target, model=model
        )
        print(format_full_distribution_report(full_result, model=model))
    if confidence is not None:
        minimum = minimum_wishes_for_probability(
            initial_state=state,
            target_copies=target,
            desired_probability=confidence,
            model=model,
        )
        print(f"\nMinimum wishes for at least {confidence:.2%} success: {minimum}")
    if args.threshold_table:
        print(
            format_threshold_table(
                threshold_table(initial_state=state, target_copies=target, model=model)
            )
        )


if __name__ == "__main__":
    main()
