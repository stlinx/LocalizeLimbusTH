from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "work" / "sample_data" / "localization_full"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_JSON = OUTPUT_DIR / "curated_identity_drafts.json"
OUTPUT_MD = OUTPUT_DIR / "curated_identity_drafts_summary.md"


SINNER_ORDER = {
    "101": 1,
    "102": 2,
    "103": 3,
    "104": 4,
    "105": 5,
    "106": 6,
    "107": 7,
    "108": 8,
    "109": 9,
    "110": 10,
    "111": 11,
    "112": 12,
}


def load_json(name: str) -> dict[str, Any]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8-sig"))


def data_list(name: str) -> list[dict[str, Any]]:
    data = load_json(name)
    rows = data.get("dataList", [])
    return rows if isinstance(rows, list) else []


def local_name_for(en_name: str) -> str:
    return en_name[3:] if en_name.startswith("EN_") else f"EN_{en_name}"


def load_pair(en_name: str) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    en_rows = data_list(en_name)
    local_path = DATA_DIR / local_name_for(en_name)
    local_rows = data_list(local_path.name) if local_path.exists() else []
    return (
        {str(row.get("id")): row for row in en_rows if isinstance(row, dict) and "id" in row},
        {str(row.get("id")): row for row in local_rows if isinstance(row, dict) and "id" in row},
    )


def get_text_pair(en_row: dict[str, Any] | None, local_row: dict[str, Any] | None, key: str) -> dict[str, Any]:
    return {
        "en": en_row.get(key) if en_row else None,
        "local": local_row.get(key) if local_row else None,
    }


def sinner_code_from_identity_id(identity_id: str) -> str:
    return identity_id[:3]


def identity_id_from_child_id(child_id: str) -> str | None:
    digits = "".join(ch for ch in child_id if ch.isdigit())
    if len(digits) < 5:
        return None
    return digits[:5]


def slot_from_skill_id(skill_id: str) -> str | None:
    digits = "".join(ch for ch in skill_id if ch.isdigit())
    if len(digits) < 7:
        return None
    suffix = digits[5:]
    slot_code = suffix[:2]
    return {
        "01": "skill_1",
        "02": "skill_2",
        "03": "skill_3",
        "04": "defense",
        "05": "skill_5_or_special",
        "06": "skill_6_or_special",
    }.get(slot_code, f"slot_{slot_code}")


def passive_type_from_id(passive_id: str) -> str:
    digits = "".join(ch for ch in passive_id if ch.isdigit())
    if len(digits) >= 7 and digits[5:7] == "21":
        return "support"
    return "combat"


def build_sinners(personalities_en: dict[str, dict[str, Any]], personalities_local: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    sinners: dict[str, dict[str, Any]] = {}
    for identity_id, en_row in personalities_en.items():
        code = sinner_code_from_identity_id(identity_id)
        if code not in SINNER_ORDER or code in sinners:
            continue
        local_row = personalities_local.get(identity_id)
        sinners[code] = {
            "id": code,
            "display_order": SINNER_ORDER[code],
            "name": get_text_pair(en_row, local_row, "name"),
        }
    return sorted(sinners.values(), key=lambda row: row["display_order"])


def build_skill_index() -> dict[str, list[dict[str, Any]]]:
    skill_files = [DATA_DIR / "EN_Skills.json"]
    skill_files.extend(sorted(DATA_DIR.glob("EN_Skills_personality*.json")))
    by_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in skill_files:
        en_rows, local_rows = load_pair(path.name)
        for skill_id, en_row in en_rows.items():
            identity_id = identity_id_from_child_id(skill_id)
            if not identity_id:
                continue
            local_row = local_rows.get(skill_id)
            levels = []
            en_levels = en_row.get("levelList", []) if isinstance(en_row, dict) else []
            local_levels = local_row.get("levelList", []) if isinstance(local_row, dict) else []
            local_by_level = {
                str(level.get("level")): level
                for level in local_levels
                if isinstance(level, dict) and "level" in level
            }
            for en_level in en_levels:
                if not isinstance(en_level, dict):
                    continue
                level_key = str(en_level.get("level"))
                local_level = local_by_level.get(level_key)
                coin_texts = []
                en_coins = en_level.get("coinlist", []) or []
                local_coins = (local_level or {}).get("coinlist", []) or []
                for index, en_coin in enumerate(en_coins, start=1):
                    if not isinstance(en_coin, dict):
                        continue
                    local_coin = local_coins[index - 1] if index - 1 < len(local_coins) and isinstance(local_coins[index - 1], dict) else {}
                    en_descs = en_coin.get("coindescs", []) or []
                    local_descs = local_coin.get("coindescs", []) or []
                    for desc_index, en_desc in enumerate(en_descs, start=1):
                        if not isinstance(en_desc, dict):
                            continue
                        local_desc = local_descs[desc_index - 1] if desc_index - 1 < len(local_descs) and isinstance(local_descs[desc_index - 1], dict) else {}
                        coin_texts.append(
                            {
                                "coin_index": index,
                                "effect_index": desc_index,
                                "desc": {
                                    "en": en_desc.get("desc"),
                                    "local": local_desc.get("desc"),
                                },
                                "parse_status": "raw_text_only",
                                "parsed_effect": None,
                            }
                        )
                levels.append(
                    {
                        "level": en_level.get("level"),
                        "name": {
                            "en": en_level.get("name"),
                            "local": (local_level or {}).get("name"),
                        },
                        "desc": {
                            "en": en_level.get("desc"),
                            "local": (local_level or {}).get("desc"),
                        },
                        "coin_texts": coin_texts,
                    }
                )
            by_identity[identity_id].append(
                {
                    "source_skill_text_id": skill_id,
                    "slot": slot_from_skill_id(skill_id),
                    "levels": levels,
                    "battle_fields": {
                        "sin_affinity": None,
                        "damage_type": None,
                        "base_power": None,
                        "coin_power": None,
                        "coin_type": None,
                        "coin_count": None,
                        "offense_level": None,
                        "attack_weight": None,
                    },
                    "curation_status": "draft",
                    "parse_status": "raw_text_only",
                }
            )
    for skills in by_identity.values():
        skills.sort(key=lambda row: (row["slot"] or "", row["source_skill_text_id"]))
    return by_identity


def build_passive_index() -> dict[str, list[dict[str, Any]]]:
    en_rows, local_rows = load_pair("EN_Passives.json")
    by_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for passive_id, en_row in en_rows.items():
        identity_id = identity_id_from_child_id(passive_id)
        if not identity_id:
            continue
        local_row = local_rows.get(passive_id)
        by_identity[identity_id].append(
            {
                "source_passive_text_id": passive_id,
                "passive_type": passive_type_from_id(passive_id),
                "name": get_text_pair(en_row, local_row, "name"),
                "desc": get_text_pair(en_row, local_row, "desc"),
                "summary": get_text_pair(en_row, local_row, "summary"),
                "battle_fields": {
                    "activation_requirement": None,
                    "parsed_effect": None,
                },
                "curation_status": "draft",
                "parse_status": "raw_text_only",
            }
        )
    for passives in by_identity.values():
        passives.sort(key=lambda row: row["source_passive_text_id"])
    return by_identity


def build_statuses() -> list[dict[str, Any]]:
    en_rows, local_rows = load_pair("EN_Bufs.json")
    statuses = []
    for status_id, en_row in sorted(en_rows.items()):
        local_row = local_rows.get(status_id)
        statuses.append(
            {
                "source_status_key": status_id,
                "name": get_text_pair(en_row, local_row, "name"),
                "desc": get_text_pair(en_row, local_row, "desc"),
                "summary": get_text_pair(en_row, local_row, "summary"),
                "simulator_handler_key": None,
                "category": None,
                "has_potency": None,
                "has_count": None,
                "curation_status": "draft",
                "parse_status": "raw_text_only",
            }
        )
    return statuses


def build_drafts() -> dict[str, Any]:
    personalities_en, personalities_local = load_pair("EN_Personalities.json")
    skills_by_identity = build_skill_index()
    passives_by_identity = build_passive_index()

    identities = []
    for identity_id, en_row in sorted(personalities_en.items()):
        code = sinner_code_from_identity_id(identity_id)
        if code not in SINNER_ORDER:
            continue
        local_row = personalities_local.get(identity_id)
        identities.append(
            {
                "source_personality_id": identity_id,
                "sinner_id": code,
                "title": get_text_pair(en_row, local_row, "title"),
                "name": get_text_pair(en_row, local_row, "name"),
                "name_with_title": get_text_pair(en_row, local_row, "nameWithTitle"),
                "desc": get_text_pair(en_row, local_row, "desc"),
                "skills": skills_by_identity.get(identity_id, []),
                "passives": passives_by_identity.get(identity_id, []),
                "battle_fields": {
                    "rarity": None,
                    "release_date": None,
                    "season": None,
                    "traits": [],
                    "hp": None,
                    "speed_min": None,
                    "speed_max": None,
                    "defense_level": None,
                    "stagger_thresholds": [],
                    "slash_resistance": None,
                    "pierce_resistance": None,
                    "blunt_resistance": None,
                    "panic_type": None,
                },
                "link_status": "auto_matched",
                "curation_status": "draft",
            }
        )

    return {
        "schema_version": 1,
        "source_dir": str(DATA_DIR),
        "notes": [
            "Draft data generated from localization/text files only.",
            "Battle fields are intentionally null until filled from wiki, game data, or admin verification.",
            "Skill and passive effects are raw text only until parsed into simulator logic.",
        ],
        "sinners": build_sinners(personalities_en, personalities_local),
        "identities": identities,
        "status_effects": build_statuses(),
    }


def write_summary(drafts: dict[str, Any]) -> None:
    identities = drafts["identities"]
    status_effects = drafts["status_effects"]
    skill_count = sum(len(identity["skills"]) for identity in identities)
    skill_level_count = sum(len(skill["levels"]) for identity in identities for skill in identity["skills"])
    coin_text_count = sum(
        len(level["coin_texts"])
        for identity in identities
        for skill in identity["skills"]
        for level in skill["levels"]
    )
    passive_count = sum(len(identity["passives"]) for identity in identities)
    no_skill = [identity for identity in identities if not identity["skills"]]
    no_passive = [identity for identity in identities if not identity["passives"]]

    lines = [
        "# Curated Identity Drafts Summary",
        "",
        f"Output JSON: `{OUTPUT_JSON}`",
        "",
        "## Counts",
        "",
        f"- Sinners: `{len(drafts['sinners'])}`",
        f"- Identities: `{len(identities)}`",
        f"- Draft skills linked to identities: `{skill_count}`",
        f"- Skill level text records: `{skill_level_count}`",
        f"- Coin effect text records: `{coin_text_count}`",
        f"- Draft passives linked to identities: `{passive_count}`",
        f"- Status effects/glossary entries: `{len(status_effects)}`",
        "",
        "## What This File Is",
        "",
        "This is the first bot-data draft: Sinner -> Identity -> localized skill/passive/status text.",
        "It is not simulator-ready yet because battle fields such as HP, speed, base power, coin power, damage type, and resistances still need curated values.",
        "",
        "## Missing Links To Review",
        "",
        f"- Identities with no linked skills: `{len(no_skill)}`",
        f"- Identities with no linked passives: `{len(no_passive)}`",
        "",
        "## Next Curation Step",
        "",
        "Pick one Identity and fill its `battle_fields` plus each skill's `battle_fields` from a trusted source such as the wiki page sample.",
        "After one Identity is complete, use it as the admin-panel form template.",
    ]

    if no_skill[:10]:
        lines.extend(["", "### First Identities With No Skills", ""])
        for identity in no_skill[:10]:
            lines.append(f"- `{identity['source_personality_id']}` {identity['title']['en']} {identity['name']['en']}")

    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    drafts = build_drafts()
    OUTPUT_JSON.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")
    write_summary(drafts)
    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_MD}")


if __name__ == "__main__":
    main()

