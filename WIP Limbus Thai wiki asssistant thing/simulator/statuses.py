from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StatusRule:
    key: str
    implementation: str
    timing: tuple[str, ...]
    stack_fields: tuple[str, ...] = ("potency", "count")
    summary: str = ""
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "implementation": self.implementation,
            "timing": list(self.timing),
            "stack_fields": list(self.stack_fields),
            "summary": self.summary,
            "notes": list(self.notes),
        }


STATUS_RULES: dict[str, StatusRule] = {
    "Breath": StatusRule(
        "Breath",
        "partial",
        ("before_coin_toss", "on_crit", "turn_end"),
        summary="Poise: potency raises critical chance; count is consumed after successful crit checks.",
        notes=("Exact count consumption and crit timing still need validation.",),
    ),
    "Bleeding": StatusRule(
        "Bleeding",
        "planned",
        ("before_attack_coin_toss",),
        summary="Bleed: when the unit tosses an attack coin, take fixed damage based on potency and reduce count.",
    ),
    "Combustion": StatusRule(
        "Combustion",
        "planned",
        ("turn_end", "activate"),
        summary="Burn: fixed damage timing/status activation needs explicit handler.",
    ),
    "Rupture": StatusRule(
        "Rupture",
        "planned",
        ("on_hit",),
        summary="Rupture: extra fixed damage on hit, then count changes.",
    ),
    "Tremor": StatusRule(
        "Tremor",
        "planned",
        ("burst",),
        summary="Tremor: stores potency/count and needs burst/conversion handlers.",
    ),
    "Vibration": StatusRule(
        "Vibration",
        "alias",
        ("burst",),
        summary="Alias seen in localization for Tremor-style text.",
    ),
    "Sinking": StatusRule(
        "Sinking",
        "planned",
        ("on_hit",),
        summary="Sinking: SP loss or gloom damage depending on target type.",
    ),
    "Charge": StatusRule(
        "Charge",
        "planned",
        ("resource", "turn_end"),
        summary="Charge: resource consumed by skill conditions and usually reduced at turn end.",
    ),
    "Paralysis": StatusRule(
        "Paralysis",
        "planned",
        ("before_coin_toss",),
        summary="Paralyze: forces coin power to 0 for affected coin tosses.",
    ),
    "Fragile": StatusRule(
        "Fragile",
        "planned",
        ("damage_modifier",),
        summary="Fragile: increases damage taken by count.",
    ),
    "Protection": StatusRule(
        "Protection",
        "planned",
        ("damage_modifier",),
        summary="Protection: reduces damage taken by count.",
    ),
    "DamageUp": StatusRule(
        "DamageUp",
        "planned",
        ("damage_modifier",),
        summary="Damage Up: increases damage dealt by count.",
    ),
    "AttackPowerUp": StatusRule(
        "AttackPowerUp",
        "planned",
        ("clash_power", "attack_power"),
        summary="Attack Power Up: affects final attack/clash power.",
    ),
    "AttackPowerDown": StatusRule(
        "AttackPowerDown",
        "planned",
        ("clash_power", "attack_power"),
        summary="Attack Power Down: lowers final attack/clash power.",
    ),
    "DefensePowerUp": StatusRule(
        "DefensePowerUp",
        "planned",
        ("defense_power",),
        summary="Defense Power Up: affects defensive skill power.",
    ),
    "DefensePowerDown": StatusRule(
        "DefensePowerDown",
        "planned",
        ("defense_power",),
        summary="Defense Power Down: lowers defensive skill power.",
    ),
    "SlashTakeDamageUp": StatusRule(
        "SlashTakeDamageUp",
        "planned",
        ("damage_modifier",),
        summary="Slash Fragility: increases slash damage taken.",
    ),
    "PierceTakeDamageUp": StatusRule(
        "PierceTakeDamageUp",
        "planned",
        ("damage_modifier",),
        summary="Pierce Fragility: increases pierce damage taken.",
    ),
    "BluntTakeDamageUp": StatusRule(
        "BluntTakeDamageUp",
        "planned",
        ("damage_modifier",),
        summary="Blunt Fragility: increases blunt damage taken.",
    ),
}


ALIASES = {
    "Poise": "Breath",
    "Burn": "Combustion",
    "Bleed": "Bleeding",
    "Paralyze": "Paralysis",
    "Vibration": "Vibration",
    "Tremor": "Tremor",
}


def status_rule_for(status_key: str | None, name_en: str | None = None) -> dict[str, Any]:
    candidates = [status_key or "", name_en or ""]
    for candidate in candidates:
        key = ALIASES.get(candidate, candidate)
        if key in STATUS_RULES:
            return STATUS_RULES[key].as_dict()
    return {
        "key": status_key or name_en or "",
        "implementation": "display_only",
        "timing": [],
        "stack_fields": [],
        "summary": "Known in database/localization, but no simulator rule is mapped yet.",
        "notes": ["Use admin/expert review before this affects combat math."],
    }


def status_registry_summary() -> dict[str, Any]:
    counts: dict[str, int] = {}
    for rule in STATUS_RULES.values():
        counts[rule.implementation] = counts.get(rule.implementation, 0) + 1
    return {
        "rules": [rule.as_dict() for rule in STATUS_RULES.values()],
        "implementation_counts": counts,
    }
