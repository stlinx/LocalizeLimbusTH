from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DRAFTS_JSON = ROOT / "outputs" / "curated_identity_drafts.json"
OUTPUT_JSON = ROOT / "outputs" / "completed_identity_sample_faust_10215.json"
OUTPUT_MD = ROOT / "outputs" / "completed_identity_sample_faust_10215_summary.md"


SOURCE = {
    "source_type": "wiki_html_sample",
    "source_url": "https://limbuscompany.wiki.gg/wiki/The_House_of_Spiders:_The_Ring_Apprentice_Faust",
    "source_file": r"C:\Users\kimoj\Downloads\The House of Spiders_ The Ring Apprentice Faust - Limbus Company Wiki.html",
}


IDENTITY_BATTLE_FIELDS = {
    "rarity": 3,
    "release_date": "2026-04-02",
    "season": "Season 7 - Kumo no ito / oti on akA",
    "world": "World of the House of Spiders",
    "traits": [
        "The Fingers",
        "The House of Spiders",
        "The Ring",
        "School of Corporism",
        "Mechanical Amalgam",
    ],
    "hp": 283,
    "speed_by_uptie": {
        "1": {"min": 3, "max": 4},
        "2": {"min": 3, "max": 5},
        "3": {"min": 3, "max": 6},
        "4": {"min": 3, "max": 6},
    },
    "speed_min": 3,
    "speed_max": 6,
    "defense_level": 62,
    "stagger_thresholds": [
        {"percent": 50, "hp": 142},
        {"percent": 30, "hp": 85},
    ],
    "slash_resistance": 0.5,
    "pierce_resistance": 1.0,
    "blunt_resistance": 2.0,
    "panic_type": {
        "name": "Panic",
        "low_morale": None,
        "panic": "Does not act for this turn.",
    },
}


SKILL_BATTLE_FIELDS: dict[str, dict[str, Any]] = {
    "1021501": {
        "sin_affinity": "Gluttony",
        "damage_type": "Slash",
        "base_power": 3,
        "base_power_by_uptie": {"1": 2, "2": 2, "3": 3, "4": 3},
        "coin_power": 4,
        "coin_type": "plus",
        "coin_count": 2,
        "offense_level": 61,
        "offense_level_base": 60,
        "offense_level_modifier": 1,
        "attack_weight": 3,
        "skill_kind": "attack",
        "variant_key": "iron_maiden",
        "unlock_condition": "Iron Maiden exclusive Skill",
        "curation_status": "needs_review",
    },
    "1021502": {
        "sin_affinity": "Envy",
        "damage_type": "Slash",
        "base_power": 4,
        "coin_power": 4,
        "coin_type": "plus",
        "coin_count": 3,
        "offense_level": 62,
        "offense_level_base": 60,
        "offense_level_modifier": 2,
        "attack_weight": 2,
        "skill_kind": "attack",
        "variant_key": "iron_maiden",
        "unlock_condition": "Iron Maiden exclusive Skill",
        "curation_status": "needs_review",
    },
    "1021503": {
        "sin_affinity": "Lust",
        "damage_type": "Slash",
        "base_power": 4,
        "base_power_by_uptie": {"3": 3, "4": 4},
        "coin_power": 3,
        "coin_type": "plus",
        "coin_count": 4,
        "offense_level": 63,
        "offense_level_base": 60,
        "offense_level_modifier": 3,
        "attack_weight": 1,
        "skill_kind": "attack",
        "variant_key": "iron_maiden",
        "unlock_condition": "Iron Maiden exclusive Skill",
        "curation_status": "needs_review",
    },
    "1021504": {
        "sin_affinity": None,
        "damage_type": None,
        "base_power": None,
        "coin_power": None,
        "coin_type": None,
        "coin_count": 1,
        "offense_level": 65,
        "offense_level_base": 60,
        "offense_level_modifier": 5,
        "attack_weight": 1,
        "skill_kind": "clashable_guard",
        "variant_key": "iron_maiden",
        "unlock_condition": "Iron Maiden exclusive Skill",
        "curation_status": "needs_review",
    },
    "1021505": {
        "sin_affinity": "Gluttony",
        "damage_type": "Slash",
        "base_power": 3,
        "coin_power": 4,
        "coin_type": "plus",
        "coin_count": 2,
        "offense_level": 61,
        "offense_level_base": 60,
        "offense_level_modifier": 1,
        "attack_weight": 3,
        "skill_kind": "attack",
        "variant_key": "the_self_unbound_flow_state",
        "unlock_condition": "The Self Unbound - Flow State exclusive Skill",
        "curation_status": "needs_review",
    },
    "1021506": {
        "sin_affinity": "Envy",
        "damage_type": "Slash",
        "base_power": 4,
        "coin_power": 4,
        "coin_type": "plus",
        "coin_count": 3,
        "offense_level": 62,
        "offense_level_base": 60,
        "offense_level_modifier": 2,
        "attack_weight": 2,
        "skill_kind": "attack",
        "variant_key": "the_self_unbound_flow_state",
        "unlock_condition": "The Self Unbound - Flow State exclusive Skill",
        "curation_status": "needs_review",
    },
    "1021507": {
        "sin_affinity": "Lust",
        "damage_type": "Slash",
        "base_power": 4,
        "coin_power": 3,
        "coin_type": "plus",
        "coin_count": 4,
        "offense_level": 63,
        "offense_level_base": 60,
        "offense_level_modifier": 3,
        "attack_weight": None,
        "skill_kind": "attack",
        "variant_key": "the_self_unbound_flow_state",
        "unlock_condition": "The Self Unbound - Flow State exclusive Skill",
        "curation_status": "needs_review",
        "review_note": "Attack weight needs verification from full wiki table.",
    },
    "1021508": {
        "sin_affinity": None,
        "damage_type": None,
        "base_power": None,
        "coin_power": None,
        "coin_type": None,
        "coin_count": 0,
        "offense_level": 62,
        "offense_level_base": 60,
        "offense_level_modifier": 2,
        "attack_weight": 1,
        "skill_kind": "evade_or_defense",
        "variant_key": "the_self_unbound_flow_state",
        "unlock_condition": "The Self Unbound - Flow State exclusive Skill",
        "curation_status": "needs_review",
        "review_note": "Defense subtype should be confirmed as evade/guard/counter from game data.",
    },
    "1021509": {
        "sin_affinity": None,
        "damage_type": "Slash",
        "base_power": None,
        "coin_power": None,
        "coin_type": "plus",
        "coin_count": 2,
        "offense_level": 62,
        "offense_level_base": 60,
        "offense_level_modifier": 2,
        "attack_weight": 1,
        "skill_kind": "clashable_counter",
        "variant_key": "assist_defense",
        "unlock_condition": "Assist Defense exclusive Skill",
        "curation_status": "needs_review",
        "review_note": "Base power and coin power need verification from full wiki table.",
    },
}


def main() -> None:
    drafts = json.loads(DRAFTS_JSON.read_text(encoding="utf-8"))
    identity = next(
        item for item in drafts["identities"]
        if item["source_personality_id"] == "10215"
    )
    sample = copy.deepcopy(identity)
    sample["source"] = SOURCE
    sample["battle_fields"].update(IDENTITY_BATTLE_FIELDS)
    sample["curation_status"] = "needs_review"
    sample["admin_workflow"] = {
        "import_status": "imported",
        "link_status": "auto_matched",
        "curation_status": "needs_review",
        "parse_status": "raw_text_only",
        "next_action": "Admin verifies battle fields and converts raw effect text into parsed simulator effects.",
    }

    for skill in sample["skills"]:
        values = SKILL_BATTLE_FIELDS.get(skill["source_skill_text_id"])
        if not values:
            skill["curation_status"] = "draft"
            continue
        skill["battle_fields"].update(values)
        skill["source"] = SOURCE
        skill["curation_status"] = values.get("curation_status", "needs_review")

    status_keys = {
        "Laceration": "Bleed",
        "Binding": "Bind",
        "DefenseDown": "Defense Level Down",
        "DefenseUp": "Defense Level Up",
        "AttackDmgDown": "Damage Down",
        "Agility": "Haste",
        "ChargeBodyArt": "Corpus Ingredient",
        "IronMaidenPersonality": "Iron Maiden",
        "SilverOpportunity": "The Self Unbound - Flow State",
        "SupportProtect": "Assist Defense",
    }
    sample["known_status_key_links"] = status_keys
    sample["missing_for_simulator_ready"] = [
        "Verify every skill battle field against game data or wiki tables.",
        "Parse raw skill/passive text into structured effect JSON.",
        "Confirm defense skill subtypes and power formulas.",
        "Add exact uptie version data for every skill variant.",
        "Map unique status handlers for Iron Maiden, Corpus Ingredient, Artwork: Fascia, Flow State, and Assist Defense.",
    ]

    OUTPUT_JSON.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Completed Identity Sample: Faust 10215",
        "",
        f"Output JSON: `{OUTPUT_JSON}`",
        "",
        "## Identity",
        "",
        f"- ID: `{sample['source_personality_id']}`",
        f"- Title: `{sample['title']['en']}`",
        f"- Sinner: `{sample['name']['en']}`",
        f"- HP: `{sample['battle_fields']['hp']}`",
        f"- Speed UT4: `{sample['battle_fields']['speed_by_uptie']['4']['min']}~{sample['battle_fields']['speed_by_uptie']['4']['max']}`",
        f"- Defense level: `{sample['battle_fields']['defense_level']}`",
        f"- Resistances: Slash `{sample['battle_fields']['slash_resistance']}`, Pierce `{sample['battle_fields']['pierce_resistance']}`, Blunt `{sample['battle_fields']['blunt_resistance']}`",
        "",
        "## Filled Skill Shells",
        "",
        "| Skill ID | Slot | Name | Sin | Type | Base | Coin | Coins | Offense | Kind |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for skill in sample["skills"]:
        fields = skill["battle_fields"]
        name = skill["levels"][-1]["name"]["en"] if skill["levels"] else ""
        lines.append(
            "| "
            + " | ".join(
                [
                    skill["source_skill_text_id"],
                    str(skill["slot"]),
                    str(name),
                    str(fields.get("sin_affinity")),
                    str(fields.get("damage_type")),
                    str(fields.get("base_power")),
                    str(fields.get("coin_power")),
                    str(fields.get("coin_count")),
                    str(fields.get("offense_level")),
                    str(fields.get("skill_kind")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Important",
            "",
            "This is the admin-panel template record. It is linked and partially filled, but still marked `needs_review` because raw effects are not parsed into simulator logic yet.",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_MD}")


if __name__ == "__main__":
    main()
