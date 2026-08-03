from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILLS_DATA = Path(
    "C:/Users/kimoj/Downloads/LC.Localization.Interface.1.4.2/"
    "LC Localization Interface 1.4\u02d02/"
    "[\u21f2] Assets Directory/"
    "Limbus Images/"
    "Skills/"
    "Skills Data"
)

ATTRIBUTE_TO_AFFINITY = {
    "CRIMSON": "Wrath",
    "SCARLET": "Lust",
    "AMBER": "Sloth",
    "SHAMROCK": "Gluttony",
    "AZURE": "Gloom",
    "INDIGO": "Pride",
    "VIOLET": "Envy",
    "NEUTRAL": None,
}

ATTACK_TYPE = {
    "SLASH": "slash",
    "PENETRATE": "pierce",
    "HIT": "blunt",
    "NONE": None,
}

DEF_TYPE = {
    "ATTACK": "attack",
    "GUARD": "guard",
    "EVADE": "evade",
    "COUNTER": "counter",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dict(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def compact_script(script: dict[str, Any]) -> dict[str, Any]:
    result = {"script_name": script.get("scriptName")}
    for key, value in script.items():
        if key == "scriptName":
            continue
        result[key] = value
    return result


def signed_coin_power(coin: dict[str, Any]) -> Any:
    scale = coin.get("scale")
    if scale is None:
        return None
    if coin.get("operatorType") in {"SUB", "SUBTRACT"}:
        return -scale
    return scale


def normalize_coin(index: int, coin: dict[str, Any]) -> dict[str, Any]:
    return {
        "coin_index": index,
        "operator": coin.get("operatorType"),
        "power": signed_coin_power(coin),
        "raw_scale": coin.get("scale"),
        "reuse_count": coin.get("reuseCount"),
        "scripts": [compact_script(script) for script in coin.get("abilityScriptList") or []],
    }


def normalize_skill_data(raw_skill: dict[str, Any], skill_data: dict[str, Any]) -> dict[str, Any]:
    attribute = skill_data.get("attributeType")
    attack_type = skill_data.get("atkType")
    def_type = skill_data.get("defType")
    coins = skill_data.get("coinList") or []
    return {
        "source_skill_id": str(raw_skill.get("id")),
        "skill_type": raw_skill.get("skillType"),
        "skill_tier": raw_skill.get("skillTier"),
        "uptie": skill_data.get("gaksungLevel"),
        "affinity": ATTRIBUTE_TO_AFFINITY.get(attribute, attribute),
        "attribute_type": attribute,
        "damage_type": ATTACK_TYPE.get(attack_type, attack_type.lower() if isinstance(attack_type, str) else attack_type),
        "attack_type": attack_type,
        "defense_type": DEF_TYPE.get(def_type, def_type.lower() if isinstance(def_type, str) else def_type),
        "raw_defense_type": def_type,
        "base_power": skill_data.get("defaultValue"),
        "offense_level_correction": skill_data.get("skillLevelCorrection"),
        "target_num": skill_data.get("targetNum"),
        "mp_usage": skill_data.get("mpUsage"),
        "can_duel": skill_data.get("canDuel"),
        "can_change_target": skill_data.get("canChangeTarget"),
        "can_team_kill": skill_data.get("canTeamKill"),
        "skill_motion": skill_data.get("skillMotion"),
        "view_type": skill_data.get("viewType"),
        "parrying_close_type": skill_data.get("parryingCloseType"),
        "target_type": skill_data.get("skillTargetType"),
        "scripts": [compact_script(script) for script in skill_data.get("abilityScriptList") or []],
        "coins": [normalize_coin(index, coin) for index, coin in enumerate(coins, start=1)],
    }


def normalized_skill_data_by_uptie(raw_skill: dict[str, Any]) -> dict[int, dict[str, Any]]:
    inherited: dict[str, Any] = {}
    result: dict[int, dict[str, Any]] = {}
    for row in raw_skill.get("skillData") or []:
        if not isinstance(row, dict):
            continue
        inherited = merge_dict(inherited, row)
        uptie = inherited.get("gaksungLevel") or row.get("gaksungLevel")
        if uptie is None:
            continue
        result[int(uptie)] = normalize_skill_data(raw_skill, inherited)
    if result:
        last: dict[str, Any] | None = None
        for uptie in range(1, 5):
            if uptie in result:
                last = result[uptie]
            elif last is not None:
                cloned = deepcopy(last)
                cloned["uptie"] = uptie
                cloned["inherited_from_uptie"] = last.get("uptie")
                result[uptie] = cloned
    return result


def load_raw_skill_data(skills_dir: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    by_id: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    for path in sorted(skills_dir.glob("*.json")):
        try:
            data = load_json(path)
        except Exception as exc:
            warnings.append(f"{path.name}: skipped invalid JSON ({exc})")
            continue
        rows = data if isinstance(data, list) else data.get("list") or data.get("data") or []
        if not isinstance(rows, list):
            warnings.append(f"{path.name}: skipped unsupported shape")
            continue
        for row in rows:
            if not isinstance(row, dict) or row.get("id") is None:
                continue
            skill_id = str(row.get("id"))
            by_id[skill_id] = {
                "source_file": str(path.resolve()),
                "raw": row,
                "by_uptie": normalized_skill_data_by_uptie(row),
            }
    return by_id, warnings


def identity_slug(path: Path) -> str:
    return path.stem


def safe_filename(value: str) -> str:
    for char in '<>:"/\\|?*':
        value = value.replace(char, "_")
    value = value.strip().rstrip(".")
    return value or "identity"


def compare_imported_to_identity(imported: dict[str, Any], identity_skill: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    checks = [
        ("base_power", imported.get("base_power"), identity_skill.get("base_power")),
        ("coin_count", len(imported.get("coins") or []), identity_skill.get("coin_count")),
        ("affinity", imported.get("affinity"), identity_skill.get("affinity")),
        ("damage_type", imported.get("damage_type"), identity_skill.get("damage_type")),
    ]
    imported_coin_powers = [coin.get("power") for coin in imported.get("coins") or []]
    identity_coin_power = identity_skill.get("coin_power")
    if imported_coin_powers and identity_coin_power is not None and any(power != identity_coin_power for power in imported_coin_powers if power is not None):
        warnings.append(f"coin_power mismatch imported={imported_coin_powers} identity={identity_coin_power}")
    for name, imported_value, identity_value in checks:
        if imported_value is None or identity_value is None:
            continue
        if str(imported_value).lower() != str(identity_value).lower():
            warnings.append(f"{name} mismatch imported={imported_value} identity={identity_value}")
    return warnings


def build_combat_database(data_dir: Path, raw_skills: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    identity_dir = data_dir / "identities" / "en"
    identities: dict[str, Any] = {}
    index_items: list[dict[str, Any]] = []
    stats: Counter = Counter()
    warnings: list[str] = []

    for path in sorted(identity_dir.glob("*.json")):
        identity_data = load_json(path)
        identity = identity_data.get("identity") or {}
        identity_id = str(identity.get("id") or "")
        slug = identity_slug(path)
        identity_key = identity_id or f"file:{slug}"
        output_filename = f"{safe_filename(identity.get('english_name') or slug)}.json"
        skill_rows: list[dict[str, Any]] = []

        for identity_skill in identity_data.get("skills") or []:
            stats["identity_skill_rows"] += 1
            skill_id = str(identity_skill.get("source_skill_text_id") or "")
            raw_entry = raw_skills.get(skill_id)
            if not raw_entry:
                stats["missing_raw_skill"] += 1
                warnings.append(f"{slug}: missing raw skill data for {skill_id} {identity_skill.get('slot')} UT{identity_skill.get('uptie')}")
                continue
            by_uptie = raw_entry["by_uptie"]
            uptie = identity_skill.get("uptie")
            imported = by_uptie.get(int(uptie)) if uptie is not None else None
            if not imported:
                stats["missing_uptie"] += 1
                warnings.append(f"{slug}: missing raw uptie {uptie} for skill {skill_id}")
                continue

            compare_warnings = compare_imported_to_identity(imported, identity_skill)
            for warning in compare_warnings:
                warnings.append(f"{slug}: {skill_id} {identity_skill.get('slot')} UT{uptie}: {warning}")
                stats["comparison_warning"] += 1

            skill_record = {
                **imported,
                "identity_id": identity_id,
                "identity_name": identity.get("english_name"),
                "sinner": identity.get("sinner"),
                "slot": identity_skill.get("slot"),
                "name": identity_skill.get("name"),
                "source_file": raw_entry["source_file"],
                "text_summary": {
                    "english_description": identity_skill.get("english_description"),
                    "coin_texts": identity_skill.get("coin_texts") or [],
                },
            }
            skill_rows.append(skill_record)
            stats["imported_skill_rows"] += 1

        identities[identity_key] = {
            "identity_key": identity_key,
            "identity": identity,
            "combat_stats": identity_data.get("combat_stats") or {},
            "skills": skill_rows,
        }
        index_items.append(
            {
                "identity_id": identity_id,
                "english_name": identity.get("english_name"),
                "sinner": identity.get("sinner"),
                "file": f"data/combat/identities/{output_filename}",
                "skill_ids": sorted({skill.get("source_skill_id") for skill in skill_rows if skill.get("source_skill_id")}),
            }
        )

    database = {
        "schema_version": 1,
        "kind": "limbus_identity_combat_database",
        "count": len(index_items),
        "identities": identities,
        "stats": dict(stats),
    }
    index = {
        "schema_version": 1,
        "kind": "limbus_identity_combat_index",
        "count": len(index_items),
        "items": index_items,
        "warnings": warnings,
        "stats": dict(stats),
    }
    return database, index


def write_split_outputs(out_dir: Path, database: dict[str, Any], index: dict[str, Any]) -> None:
    identities_dir = out_dir / "identities"
    identities_dir.mkdir(parents=True, exist_ok=True)
    for item in database["identities"].values():
        name = item["identity"].get("english_name") or item["identity"].get("id")
        write_json(identities_dir / f"{safe_filename(name)}.json", {"schema_version": 1, "kind": "limbus_identity_combat", **item})
    compact_db = {key: value for key, value in database.items() if key != "identities"}
    write_json(out_dir / "identity_combat_database.json", compact_db)
    write_json(out_dir / "identity_combat_index.json", index)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Limbus gameplay skill data and link it to exported Identity records.")
    parser.add_argument("--skills-data", type=Path, default=DEFAULT_SKILLS_DATA, help="Limbus Localization UI Skills Data directory.")
    parser.add_argument("--data", type=Path, default=ROOT / "data", help="Exported database root.")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "combat", help="Output combat database directory.")
    parser.add_argument("--max-warnings", type=int, default=40)
    args = parser.parse_args()

    raw_skills, load_warnings = load_raw_skill_data(args.skills_data)
    database, index = build_combat_database(args.data, raw_skills)
    index["warnings"] = load_warnings + index["warnings"]
    write_split_outputs(args.out, database, index)

    stats = Counter(index.get("stats") or {})
    print("Limbus combat skill import")
    print(f"  Raw skill rows: {len(raw_skills)}")
    print(f"  Identities: {database['count']}")
    print(f"  Identity skill rows: {stats['identity_skill_rows']}")
    print(f"  Imported skill rows: {stats['imported_skill_rows']}")
    print(f"  Missing raw skills: {stats['missing_raw_skill']}")
    print(f"  Missing uptie rows: {stats['missing_uptie']}")
    print(f"  Comparison warnings: {stats['comparison_warning']}")
    print(f"  Warnings: {len(index['warnings'])}")
    print(f"  Output: {args.out}")
    if index["warnings"]:
        print("\nWarnings")
        for warning in index["warnings"][: args.max_warnings]:
            print(f"  - {warning}")
        if len(index["warnings"]) > args.max_warnings:
            print(f"  ... {len(index['warnings']) - args.max_warnings} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())




