from __future__ import annotations

from dataclasses import dataclass, field
from math import floor
from typing import Any


@dataclass(frozen=True)
class DamageInput:
    coin_roll: float
    offense_level: float = 0
    defense_level: float = 0
    damage_type_resistance: float = 1.0
    sin_resistance: float = 1.0
    stagger_level: int = 0
    critical: bool = False
    clash_count: int = 0
    observation_level: int = 0
    dynamic_modifier: float = 0.0
    attack_adders: tuple[float, ...] = field(default_factory=tuple)


def resistance_modifier(resistance: float) -> float:
    value = float(resistance)
    if value < 0:
        return -0.5
    if value < 1:
        return (value - 1.0) / 2.0
    return value - 1.0


def damage_type_modifier(resistance: float, stagger_level: int = 0) -> float:
    if int(stagger_level) > 0:
        return int(stagger_level) * 0.5 + 0.5
    return resistance_modifier(resistance)


def offense_defense_modifier(offense_level: float, defense_level: float) -> float:
    diff = float(offense_level) - float(defense_level)
    if diff == 0:
        return 0.0
    return diff / (abs(diff) + 25.0)


def static_modifier(data: DamageInput) -> dict[str, float]:
    parts = {
        "damage_type": damage_type_modifier(data.damage_type_resistance, data.stagger_level),
        "sin": resistance_modifier(data.sin_resistance),
        "offense_defense": offense_defense_modifier(data.offense_level, data.defense_level),
        "critical": 0.2 if data.critical else 0.0,
        "clash_count": max(0, int(data.clash_count)) * 0.03,
        "observation": max(0, int(data.observation_level)) * 0.03,
    }
    parts["total"] = sum(parts.values())
    return parts


def calculate_damage(data: DamageInput) -> dict[str, Any]:
    coin_roll = max(0.0, float(data.coin_roll))
    static = static_modifier(data)
    dynamic = float(data.dynamic_modifier)
    raw = coin_roll * (1.0 + static["total"]) * (1.0 + dynamic)
    minimum_from_coin = coin_roll * 0.05
    before_adders = max(raw, minimum_from_coin, 1.0)
    adders = sum(float(value) for value in data.attack_adders)
    final = max(1, floor(before_adders + adders))
    return {
        "coin_roll": coin_roll,
        "static_modifier": static,
        "dynamic_modifier": dynamic,
        "attack_adders": list(data.attack_adders),
        "raw_damage": raw,
        "minimum_from_coin": minimum_from_coin,
        "damage_before_adders": floor(before_adders),
        "final_damage": final,
        "assumptions": [
            "Damage is calculated per coin roll.",
            "Resistance, offense/defense, critical, clash count, and observation are static modifiers.",
            "Status/passive/skill percentage bonuses are represented as one dynamic modifier until the effect parser is expanded.",
            "Attack adders are added after base final damage; complex adders still need individual handlers.",
        ],
    }


def damage_input_from_payload(payload: dict[str, Any]) -> DamageInput:
    return DamageInput(
        coin_roll=float(payload.get("coin_roll") or payload.get("power") or 0),
        offense_level=float(payload.get("offense_level") or 0),
        defense_level=float(payload.get("defense_level") or 0),
        damage_type_resistance=float(payload.get("damage_type_resistance") or payload.get("resistance") or 1),
        sin_resistance=float(payload.get("sin_resistance") or 1),
        stagger_level=int(payload.get("stagger_level") or 0),
        critical=bool(payload.get("critical") or False),
        clash_count=int(payload.get("clash_count") or 0),
        observation_level=int(payload.get("observation_level") or 0),
        dynamic_modifier=float(payload.get("dynamic_modifier") or 0),
        attack_adders=tuple(float(value) for value in (payload.get("attack_adders") or [])),
    )


def simulate_damage_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return calculate_damage(damage_input_from_payload(payload))
