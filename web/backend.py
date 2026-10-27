"""Local v1.0 web adapter. Probability rules remain in genshin_wish.

Run from the repository root: python -m uvicorn web.backend:app --host 127.0.0.1
"""

from itertools import accumulate
from math import fsum
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from genshin_wish import (
    CharacterGoal, WeaponGoal, WishState, WeaponWishState,
    community_soft_pity_model, community_weapon_soft_pity_model,
    expected_wishes_to_target, expected_weapon_wishes_to_target,
    prepare_combined_distribution, with_capturing_radiance,
)
from genshin_wish.weapon_engine import iter_weapon_target_success_probabilities

VERSION = "1.0.3"
WEB_ROOT = Path(__file__).resolve().parent


class WishRequest(BaseModel):
    """Web limits bound interactive work; the Python engines stay general."""

    model_config = ConfigDict(extra="forbid", strict=True)
    mode: Literal["character", "weapon", "combined"] = "character"
    wish_budget: int = Field(ge=0, le=2000)
    pity: int = Field(default=0, ge=0, le=89)
    is_guaranteed: bool = False
    target_copies: int = Field(default=1, ge=0, le=10)
    cr_counter: int = Field(default=1, ge=0, le=3)
    weapon_pity: int = Field(default=0, ge=0, le=79)
    weapon_guaranteed: bool = False
    fate_point: int = Field(default=0, ge=0, le=1)
    weapon_target: int = Field(default=1, ge=0, le=10)


app = FastAPI(title="Genshin Wish Probability Calculator", version=VERSION)
# Serve the UI and API together: no hard-coded API host or permissive CORS.
app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/api/version")
def version():
    return {"version": VERSION}


def _rank_outcomes(outcomes, character_target, weapon_target):
    """Exact ties share a competition rank; copy counts break display ties."""
    outcomes.sort(key=lambda row: (-row["probability"], row["character_copies"], row["weapon_copies"]))
    previous = None
    rank = 0
    for position, row in enumerate(outcomes, 1):
        if row["probability"] != previous:
            rank = position
        row["rank"] = rank
        row["is_target"] = (row["character_copies"] == character_target and row["weapon_copies"] == weapon_target)
        previous = row["probability"]
    return outcomes


def _combined_outcomes(request, character, weapon, prepared, report):
    """Exact capped (character, weapon) distribution via weighted CDF tails.

    Unfinished character paths have zero weapons. On character-success paths,
    compute P(W>=j) once for all remaining budgets, then difference adjacent
    tails. No weapon DP is repeated per character completion time.
    """
    budget = request.wish_budget
    k, m = character.target_copies, weapon.target_copies
    at_budget = character.calculate(budget) if budget < prepared.character_result.wishes else prepared.character_result
    outcomes = [
        {"character_copies": count, "weapon_copies": 0, "probability": probability}
        for count, probability in at_budget.copy_distribution.items() if count < k
    ]
    tails = [report.character_success_probability]
    for target in range(1, m):
        cdf = tuple(probability for _, probability in iter_weapon_target_success_probabilities(
            initial_state=weapon.initial_state, target_copies=target,
            max_wishes=budget, model=weapon.model,
        ))
        tails.append(fsum(
            p * cdf[budget - t]
            for t, p in enumerate(report.character_completion_time_distribution) if p
        ))
    if m:
        tails.append(report.success_probability)
    tails.append(0.0)
    for copies in range(m + 1):
        outcomes.append({
            "character_copies": k, "weapon_copies": copies,
            "probability": max(0.0, tails[copies] - tails[copies + 1]),
        })
    return outcomes


@app.post("/api/calculate")
def calculate_wishes(request: WishRequest):
    character = CharacterGoal(
        WishState(request.pity, request.is_guaranteed, 0, request.cr_counter),
        request.target_copies, with_capturing_radiance(community_soft_pity_model()),
    )
    weapon = WeaponGoal(
        WeaponWishState(request.weapon_pity, request.weapon_guaranteed, request.fate_point),
        request.weapon_target, community_weapon_soft_pity_model(),
    )
    budget = request.wish_budget
    if request.mode == "combined":
        bound = character.certain_wishes() + weapon.certain_wishes()
        prepared = prepare_combined_distribution(character_goal=character, weapon_goal=weapon, max_wishes=bound)
        report = prepared.report(budget)
        success = report.success_probability
        outcomes = _combined_outcomes(request, character, weapon, prepared, report)
        thresholds = [{"probability": row.probability, "wishes": row.wishes}
                      for row in prepared.threshold_table((0, .50, .75, .90, .95, .99, 1))]
        conditional = report.expected_total_completion_wish_given_success
        remaining = report.expected_remaining_wishes_given_character_success
        expected = expected_wishes_to_target(
            initial_state=character.initial_state, target_copies=character.target_copies, model=character.model,
        ) + expected_weapon_wishes_to_target(
            initial_state=weapon.initial_state, target_copies=weapon.target_copies, model=weapon.model,
        )
        breakdown = {"both": success, "character_only": report.character_success_weapon_failure_probability,
                     "character_failed": report.character_failure_probability}
        target_c, target_w = request.target_copies, request.weapon_target
    else:
        goal = character if request.mode == "character" else weapon
        bound = goal.certain_wishes()
        trajectory = goal.calculate(bound)
        report = trajectory if budget == bound else goal.calculate(budget)
        cdf = tuple(min(1.0, p) for p in accumulate(trajectory.completion_time_distribution))
        thresholds = []
        for p in (0, .50, .75, .90, .95, .99, 1):
            n = bound if p == 1 else next(n for n, value in enumerate(cdf) if value >= p)
            thresholds.append({"probability": p, "wishes": n})
        success = report.success_probability
        conditional = report.expected_wishes_if_success_within_budget
        remaining = report.expected_remaining_wishes_if_success
        if request.mode == "character":
            expected = expected_wishes_to_target(initial_state=character.initial_state, target_copies=character.target_copies, model=character.model)
            target_c, target_w = request.target_copies, 0
        else:
            expected = expected_weapon_wishes_to_target(initial_state=weapon.initial_state, target_copies=weapon.target_copies, model=weapon.model)
            target_c, target_w = 0, request.weapon_target
        outcomes = [{"character_copies": copies if request.mode == "character" else 0,
                     "weapon_copies": copies if request.mode == "weapon" else 0, "probability": p}
                    for copies, p in report.copy_distribution.items()]
        breakdown = {"success": success, "unfinished": max(0.0, 1 - success)}

    return {
        "version": VERSION, "request": request.model_dump(),
        "success_probability": min(1.0, max(0.0, success)),
        "outcomes": _rank_outcomes(outcomes, target_c, target_w), "thresholds": thresholds,
        "expected_wishes": expected, "conditional_expected_wishes": conditional,
        "conditional_remaining_wishes": remaining, "breakdown": breakdown,
        "assumptions": {"character": character.model.name,
                        "capturing_radiance": character.model.capturing_radiance.name,
                        "weapon": weapon.model.name,
                        "policy": "stop_at_target; character_first_in_combined"},
    }
