from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.db import connect
from backend.services import DEFAULT_DB

from .clash import ClashInput, SkillSpec, result_to_dict, simulate_clash, simulate_clash_sequence


def _loads(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return fallback
    return json.loads(value)


def _coin_powers_from_row(row: Any) -> tuple[tuple[int, ...], str, list[str]]:
    warnings: list[str] = []
    mechanics = _loads(row["mechanics_json"], {}) or {}
    raw_coins = mechanics.get("coins") or []
    if raw_coins:
        operators = [str(coin.get("operator") or "ADD") for coin in raw_coins]
        powers = tuple(int(coin.get("power") or 0) for coin in raw_coins)
        operator = "MIXED" if len(set(operators)) > 1 else operators[0]
        if any((coin.get("scripts") or []) for coin in raw_coins):
            warnings.append(f"{row['name_en']} has coin scripts that are ignored in this basic simulator.")
        return powers, operator, warnings

    coin_count = int(row["coin_count"] or 0)
    coin_power = int(row["coin_power"] or 0)
    if coin_count <= 0:
        warnings.append(f"{row['name_en']} has no usable coin data; treating it as base power only.")
        return (), "NONE", warnings
    return tuple(coin_power for _ in range(coin_count)), "ADD" if coin_power >= 0 else "SUB", warnings


def load_skill_spec(
    identity_id: str,
    skill: str,
    db_path: Path = DEFAULT_DB,
    uptie: int = 4,
) -> SkillSpec:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM skills
            WHERE identity_id = ? AND uptie = ?
            ORDER BY slot, source_skill_text_id
            """,
            (str(identity_id), int(uptie)),
        ).fetchall()
    if not rows:
        raise ValueError(f"No skills found for identity {identity_id} at uptie {uptie}")

    needle = str(skill).strip().lower()
    matches = [
        row
        for row in rows
        if needle
        in {
            str(row["source_skill_text_id"] or "").lower(),
            str(row["slot"] or "").lower(),
            str(row["name_en"] or "").lower(),
        }
    ]
    if not matches:
        matches = [row for row in rows if needle in str(row["name_en"] or "").lower()]
    if not matches:
        raise ValueError(f"No skill found for identity {identity_id}: {skill}")

    row = matches[0]
    coins, operator, warnings = _coin_powers_from_row(row)
    if row["mechanics_json"]:
        mechanics = _loads(row["mechanics_json"], {}) or {}
        if mechanics.get("can_duel") is False:
            warnings.append(f"{row['name_en']} is marked as unable to clash/can_duel=false in raw data.")
    return SkillSpec(
        id=str(row["source_skill_text_id"] or ""),
        identity_id=str(row["identity_id"] or ""),
        slot=row["slot"],
        uptie=int(row["uptie"] or uptie),
        name=row["name_en"] or str(row["source_skill_text_id"] or skill),
        base_power=int(row["base_power"] or 0),
        coins=coins,
        coin_operator=operator,
        warnings=tuple(warnings),
    )


def manual_skill_spec(data: dict[str, Any], label: str = "Manual Skill") -> SkillSpec:
    coins = data.get("coins")
    if coins is None:
        coin_count = int(data.get("coin_count") or 0)
        coin_power = int(data.get("coin_power") or 0)
        coins = [coin_power for _ in range(coin_count)]
    return SkillSpec(
        id=str(data.get("skill_id") or "") or None,
        identity_id=str(data.get("identity_id") or "") or None,
        slot=data.get("slot"),
        uptie=data.get("uptie"),
        name=str(data.get("name") or label),
        base_power=int(data.get("base_power") or 0),
        coins=tuple(int(power) for power in coins),
        coin_operator=str(data.get("coin_operator") or "ADD"),
        warnings=("Manual skill input has no status/passive script data.",),
    )


def clash_input_from_payload(data: dict[str, Any], side: str, db_path: Path = DEFAULT_DB) -> ClashInput:
    section = data.get(side) or {}
    if not isinstance(section, dict):
        raise ValueError(f"{side} must be an object")
    sp = int(section.get("sp") or 0)
    modifier = int(section.get("final_power_modifier") or 0)
    label = str(section.get("label") or side.title())
    if "manual_skill" in section:
        skill = manual_skill_spec(section["manual_skill"], label)
    else:
        identity_id = section.get("identity_id")
        skill_key = section.get("skill") or section.get("skill_id") or section.get("slot")
        if not identity_id or not skill_key:
            raise ValueError(f"{side} needs identity_id and skill, or manual_skill")
        skill = load_skill_spec(str(identity_id), str(skill_key), db_path, int(section.get("uptie") or data.get("uptie") or 4))
    return ClashInput(skill=skill, sp=sp, final_power_modifier=modifier, label=label)


def simulate_clash_payload(payload: dict[str, Any], db_path: Path = DEFAULT_DB) -> dict[str, Any]:
    attacker = clash_input_from_payload(payload, "attacker", db_path)
    defender = clash_input_from_payload(payload, "defender", db_path)
    if str(payload.get("mode") or "").lower() in {"sequence", "deterministic_sequence"}:
        fixed = payload.get("fixed_results") or {}
        return simulate_clash_sequence(attacker, defender, fixed.get("attacker"), fixed.get("defender"))
    return result_to_dict(simulate_clash(attacker, defender))
