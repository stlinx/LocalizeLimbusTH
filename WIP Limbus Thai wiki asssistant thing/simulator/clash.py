from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Distribution = dict[int, float]


@dataclass(frozen=True)
class SkillSpec:
    id: str | None
    name: str
    base_power: int
    coins: tuple[int, ...]
    coin_operator: str = "ADD"
    identity_id: str | None = None
    slot: str | None = None
    uptie: int | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClashInput:
    skill: SkillSpec
    sp: int = 0
    final_power_modifier: int = 0
    label: str = ""


@dataclass(frozen=True)
class ClashResult:
    attacker: dict[str, Any]
    defender: dict[str, Any]
    probabilities: dict[str, float]
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


def heads_chance(sp: int | float) -> float:
    """Return Limbus-style heads chance from sanity.

    This first simulator uses the common player-facing rule: 0 SP is 50%,
    +45 SP is 95%, and -45 SP is 5%.
    """
    clamped_sp = max(-45.0, min(45.0, float(sp)))
    return (50.0 + clamped_sp) / 100.0


def skill_distribution(skill: SkillSpec, sp: int | float, final_power_modifier: int = 0) -> Distribution:
    chance = heads_chance(sp)
    distribution: Distribution = {skill.base_power + int(final_power_modifier): 1.0}
    for coin_power in skill.coins:
        next_distribution: Distribution = {}
        for power, probability in distribution.items():
            next_distribution[power] = next_distribution.get(power, 0.0) + probability * (1.0 - chance)
            heads_power = power + coin_power
            next_distribution[heads_power] = next_distribution.get(heads_power, 0.0) + probability * chance
        distribution = next_distribution
    return dict(sorted(distribution.items()))


def clash_probability(attacker_distribution: Distribution, defender_distribution: Distribution) -> dict[str, float]:
    win = 0.0
    lose = 0.0
    tie = 0.0
    for attacker_power, attacker_probability in attacker_distribution.items():
        for defender_power, defender_probability in defender_distribution.items():
            probability = attacker_probability * defender_probability
            if attacker_power > defender_power:
                win += probability
            elif attacker_power < defender_power:
                lose += probability
            else:
                tie += probability
    return {
        "attacker_win": win,
        "defender_win": lose,
        "tie": tie,
    }


def distribution_summary(distribution: Distribution) -> dict[str, Any]:
    expected = sum(power * probability for power, probability in distribution.items())
    return {
        "min": min(distribution) if distribution else None,
        "max": max(distribution) if distribution else None,
        "expected": expected,
        "outcomes": [
            {"power": power, "probability": probability}
            for power, probability in sorted(distribution.items())
        ],
    }


def skill_payload(clash_input: ClashInput, distribution: Distribution) -> dict[str, Any]:
    skill = clash_input.skill
    return {
        "label": clash_input.label,
        "sp": clash_input.sp,
        "heads_chance": heads_chance(clash_input.sp),
        "final_power_modifier": clash_input.final_power_modifier,
        "skill": {
            "identity_id": skill.identity_id,
            "skill_id": skill.id,
            "slot": skill.slot,
            "name": skill.name,
            "uptie": skill.uptie,
            "base_power": skill.base_power,
            "coins": list(skill.coins),
            "coin_operator": skill.coin_operator,
        },
        "distribution": distribution_summary(distribution),
    }


def simulate_clash(attacker: ClashInput, defender: ClashInput) -> ClashResult:
    attacker_distribution = skill_distribution(attacker.skill, attacker.sp, attacker.final_power_modifier)
    defender_distribution = skill_distribution(defender.skill, defender.sp, defender.final_power_modifier)
    probabilities = clash_probability(attacker_distribution, defender_distribution)
    warnings = tuple(dict.fromkeys((*attacker.skill.warnings, *defender.skill.warnings)))
    assumptions = (
        "Uses raw base power and coin power only.",
        "Heads chance is calculated as 50% + SP, clamped to -45..45 SP.",
        "Status effects, passives, resonance, offense/defense level, and special scripts are not applied yet.",
        "This is a single-roll distribution comparison, not the full multi-coin clash break sequence yet.",
    )
    return ClashResult(
        attacker=skill_payload(attacker, attacker_distribution),
        defender=skill_payload(defender, defender_distribution),
        probabilities=probabilities,
        assumptions=assumptions,
        warnings=warnings,
    )


def result_to_dict(result: ClashResult) -> dict[str, Any]:
    return {
        "attacker": result.attacker,
        "defender": result.defender,
        "probabilities": result.probabilities,
        "assumptions": list(result.assumptions),
        "warnings": list(result.warnings),
    }


def coin_power_total(base_power: int, coins: tuple[int, ...], heads: list[bool], final_power_modifier: int = 0) -> int:
    total = int(base_power) + int(final_power_modifier)
    for coin_power, is_heads in zip(coins, heads):
        if is_heads:
            total += int(coin_power)
    return total


def parse_fixed_rounds(value: Any, coin_count: int) -> list[list[bool]]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_rounds = [part.strip() for part in re_split_rounds(value) if part.strip()]
        return [[char.upper() == "H" for char in raw if char.upper() in {"H", "T"}] for raw in raw_rounds]
    rounds: list[list[bool]] = []
    for row in value or []:
        if isinstance(row, str):
            rounds.append([char.upper() == "H" for char in row if char.upper() in {"H", "T"}])
        else:
            rounds.append([bool(item) for item in row])
    return rounds


def re_split_rounds(value: str) -> list[str]:
    import re

    return re.split(r"[|,/\s]+", value.strip())


def _round_heads(rounds: list[list[bool]], round_index: int, coin_count: int) -> list[bool]:
    if round_index < len(rounds):
        row = list(rounds[round_index])
        if len(row) < coin_count:
            row.extend([False] * (coin_count - len(row)))
        return row[:coin_count]
    return [False] * coin_count


def simulate_clash_sequence(attacker: ClashInput, defender: ClashInput, attacker_rounds: Any = None, defender_rounds: Any = None) -> dict[str, Any]:
    attacker_remaining = list(attacker.skill.coins)
    defender_remaining = list(defender.skill.coins)
    attacker_fixed = parse_fixed_rounds(attacker_rounds, len(attacker_remaining))
    defender_fixed = parse_fixed_rounds(defender_rounds, len(defender_remaining))
    rounds: list[dict[str, Any]] = []
    winner = "clash_cancelled"
    max_rounds = 99

    for round_index in range(max_rounds):
        if not attacker_remaining or not defender_remaining:
            break
        attacker_heads = _round_heads(attacker_fixed, round_index, len(attacker_remaining))
        defender_heads = _round_heads(defender_fixed, round_index, len(defender_remaining))
        attacker_power = coin_power_total(attacker.skill.base_power, tuple(attacker_remaining), attacker_heads, attacker.final_power_modifier)
        defender_power = coin_power_total(defender.skill.base_power, tuple(defender_remaining), defender_heads, defender.final_power_modifier)
        if attacker_power > defender_power:
            loser = "defender"
            defender_remaining.pop()
        elif defender_power > attacker_power:
            loser = "attacker"
            attacker_remaining.pop()
        else:
            loser = "tie"
        rounds.append(
            {
                "round": round_index + 1,
                "attacker_power": attacker_power,
                "defender_power": defender_power,
                "attacker_heads": ["H" if value else "T" for value in attacker_heads],
                "defender_heads": ["H" if value else "T" for value in defender_heads],
                "loser": loser,
                "attacker_coins_remaining": len(attacker_remaining),
                "defender_coins_remaining": len(defender_remaining),
            }
        )

    if not attacker_remaining and defender_remaining:
        winner = "defender"
    elif not defender_remaining and attacker_remaining:
        winner = "attacker"
    elif not attacker_remaining and not defender_remaining:
        winner = "both_no_coins"
    elif len(rounds) >= max_rounds and attacker_remaining and defender_remaining:
        winner = "clash_cancelled"

    return {
        "mode": "deterministic_sequence",
        "winner": winner,
        "rounds": rounds,
        "max_rounds": max_rounds,
        "attacker": {
            "label": attacker.label,
            "sp": attacker.sp,
            "skill": skill_payload(attacker, {})["skill"],
            "coins_remaining": len(attacker_remaining),
            "attack_coins": len(attacker_remaining) if winner == "attacker" else 0,
        },
        "defender": {
            "label": defender.label,
            "sp": defender.sp,
            "skill": skill_payload(defender, {})["skill"],
            "coins_remaining": len(defender_remaining),
            "attack_coins": len(defender_remaining) if winner == "defender" else 0,
        },
        "assumptions": [
            "Deterministic test mode uses provided H/T coin results.",
            "A tied clash round rerolls without removing coins.",
            "The clash continues until one side loses all clashable coins, or until 99 tied/continued rounds cancel the clash.",
            "Status effects, passives, resonance, offense/defense level, and special scripts are not applied yet.",
        ],
        "warnings": list(dict.fromkeys((*attacker.skill.warnings, *defender.skill.warnings))),
    }
