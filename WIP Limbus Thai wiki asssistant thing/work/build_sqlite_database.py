from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db import connect, init_db
from backend.services import norm


LOCALIZATION_FULL_DIR = ROOT / "work" / "sample_data" / "localization_full"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def data_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = load_json(path)
    rows = data.get("dataList") if isinstance(data, dict) else data
    return [row for row in rows or [] if isinstance(row, dict)]


def add_alias(conn: sqlite3.Connection, identity_id: str, alias: str | None, source: str) -> None:
    alias = " ".join(str(alias or "").replace("\n", " ").split()).strip()
    if not alias:
        return
    conn.execute(
        """
        INSERT OR IGNORE INTO identity_search_aliases(identity_id, alias, normalized, source)
        VALUES (?, ?, ?, ?)
        """,
        (identity_id, alias, norm(alias), source),
    )


def paired_rows(local_file: str, en_file: str) -> dict[str, dict[str, Any]]:
    local = {str(row.get("id")): row for row in data_list(LOCALIZATION_FULL_DIR / local_file)}
    en = {str(row.get("id")): row for row in data_list(LOCALIZATION_FULL_DIR / en_file)}
    keys = sorted(set(local) | set(en))
    return {key: {"local": local.get(key), "en": en.get(key)} for key in keys}


def load_personality_names() -> dict[str, dict[str, str]]:
    result = {}
    rows = paired_rows("Personalities.json", "EN_Personalities.json")
    for identity_id, pair in rows.items():
        local = pair.get("local") or {}
        en = pair.get("en") or {}
        result[identity_id] = {
            "localized_name": " ".join(str(local.get("nameWithTitle") or "").replace("\n", " ").split()).strip(),
            "english_name": " ".join(str(en.get("nameWithTitle") or "").replace("\n", " ").split()).strip(),
            "search": " ".join(
                str(value or "").replace("\n", " ")
                for value in [local.get("nameWithTitle"), local.get("title"), local.get("name")]
                if value
            ),
        }
    return result


def load_combat_by_id(data_dir: Path) -> dict[str, dict[str, Any]]:
    result = {}
    combat_dir = data_dir / "combat" / "identities"
    for path in combat_dir.glob("*.json"):
        try:
            data = load_json(path)
        except Exception:
            continue
        identity_id = (data.get("identity") or {}).get("id") or data.get("identity_id")
        if identity_id:
            result[str(identity_id)] = data
    return result


def localized_skill_map(th: dict[str, Any] | None) -> dict[tuple[Any, Any, Any], dict[str, Any]]:
    result = {}
    if not th:
        return result
    for skill in th.get("skills") or []:
        result[(skill.get("source_skill_text_id"), skill.get("slot"), skill.get("uptie"))] = skill
    return result


def combat_skill_map(combat: dict[str, Any] | None) -> dict[tuple[Any, Any, Any], dict[str, Any]]:
    result = {}
    if not combat:
        return result
    for skill in combat.get("skills") or []:
        result[(skill.get("source_skill_id"), skill.get("slot"), skill.get("uptie"))] = skill
    return result


def insert_identities(conn: sqlite3.Connection, data_dir: Path) -> int:
    personality_names = load_personality_names()
    combat_by_id = load_combat_by_id(data_dir)
    count = 0
    for en_path in sorted((data_dir / "identities" / "en").glob("*.json")):
        en = load_json(en_path)
        identity = en.get("identity") or {}
        identity_id = str(identity.get("id") or "")
        if not identity_id or not en.get("skills"):
            continue
        th_path = data_dir / "identities" / "locales" / "th" / en_path.name
        th = load_json(th_path) if th_path.exists() else None
        combat = combat_by_id.get(identity_id)
        stats = en.get("combat_stats") or {}
        res = stats.get("resistances") or {}
        localized_name = (personality_names.get(identity_id) or {}).get("localized_name")

        conn.execute(
            """
            INSERT OR REPLACE INTO identities(
              identity_id, english_name, localized_name, sinner, rarity, hp, defense_level,
              slash_resistance, pierce_resistance, blunt_resistance, speed_by_uptie_json,
              stagger_thresholds_json, panic_text, sanity_json,
              en_json, th_json, combat_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                identity_id,
                identity.get("english_name"),
                localized_name,
                identity.get("sinner"),
                identity.get("rarity"),
                stats.get("hp"),
                stats.get("defense_level"),
                res.get("slash"),
                res.get("pierce"),
                res.get("blunt"),
                dumps(stats.get("speed_by_uptie") or {}),
                dumps(stats.get("stagger_thresholds") or []),
                stats.get("panic"),
                dumps(stats.get("sanity") or {}),
                dumps(en),
                dumps(th) if th else None,
                dumps(combat) if combat else None,
            ),
        )
        add_alias(conn, identity_id, identity_id, "identity_id")
        add_alias(conn, identity_id, identity.get("english_name"), "english_name")
        add_alias(conn, identity_id, identity.get("sinner"), "sinner")
        person = personality_names.get(identity_id) or {}
        add_alias(conn, identity_id, person.get("localized_name"), "localized_identity")
        add_alias(conn, identity_id, person.get("search"), "localized_identity")

        th_skills = localized_skill_map(th)
        combat_skills = combat_skill_map(combat)
        for skill in en.get("skills") or []:
            key = (skill.get("source_skill_text_id"), skill.get("slot"), skill.get("uptie"))
            local = th_skills.get(key) or {}
            mechanics = combat_skills.get(key)
            attack_weight = skill.get("attack_weight")
            if mechanics and mechanics.get("target_num") is not None:
                attack_weight = mechanics.get("target_num")
            cursor = conn.execute(
                """
                INSERT INTO skills(
                  identity_id, source_skill_text_id, slot, uptie, name_en, name_th, affinity,
                  damage_type, skill_type, base_power, coin_power, coin_count, deck_count, attack_weight,
                  offense_level_json, description_en, description_th, mechanics_json, assets_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identity_id,
                    skill.get("source_skill_text_id"),
                    skill.get("slot"),
                    skill.get("uptie"),
                    (skill.get("name") or {}).get("en"),
                    local.get("name"),
                    skill.get("affinity"),
                    skill.get("damage_type"),
                    skill.get("skill_type"),
                    skill.get("base_power"),
                    skill.get("coin_power"),
                    skill.get("coin_count"),
                    skill.get("deck_count"),
                    attack_weight,
                    dumps(skill.get("offense_level") or {}),
                    skill.get("english_description"),
                    local.get("description"),
                    dumps(mechanics) if mechanics else None,
                    dumps({}),
                ),
            )
            skill_row_id = cursor.lastrowid
            add_alias(conn, identity_id, (skill.get("name") or {}).get("en"), "skill_name")
            add_alias(conn, identity_id, local.get("name"), "localized_skill_name")
            local_coin_lookup = {
                (row.get("coin_index"), row.get("effect_index")): row.get("text")
                for row in local.get("coin_texts") or []
            }
            for coin in skill.get("coin_texts") or []:
                conn.execute(
                    """
                    INSERT INTO coins(skill_row_id, coin_index, effect_index, text_en, text_th)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        skill_row_id,
                        coin.get("coin_index"),
                        coin.get("effect_index"),
                        coin.get("en"),
                        local_coin_lookup.get((coin.get("coin_index"), coin.get("effect_index"))),
                    ),
                )

        local_passives = (th or {}).get("passives") or {}
        for passive_type, rows in (en.get("passives") or {}).items():
            local_by_id = {
                str(row.get("source_passive_text_id")): row
                for row in local_passives.get(passive_type) or []
            }
            for passive in rows or []:
                source_id = str(passive.get("source_passive_text_id") or "")
                local = local_by_id.get(source_id) or {}
                conn.execute(
                    """
                    INSERT INTO passives(
                      identity_id, passive_type, source_passive_text_id, name_en, name_th,
                      requirement, description_en, description_th
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        identity_id,
                        passive_type,
                        source_id,
                        (passive.get("name") or {}).get("en"),
                        local.get("name"),
                        passive.get("requirement"),
                        passive.get("en"),
                        local.get("description"),
                    ),
                )
                add_alias(conn, identity_id, (passive.get("name") or {}).get("en"), "passive_name")
                add_alias(conn, identity_id, local.get("name"), "localized_passive_name")
        count += 1
    return count


def insert_status_effects(conn: sqlite3.Connection, data_dir: Path) -> int:
    manifest_path = data_dir / "assets" / "asset_manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    icons = ((manifest.get("database_token_asset_matches") or {}).get("matched") or {})
    pairs = {}
    for local_file, en_file, category in [
        ("Bufs.json", "EN_Bufs.json", "status"),
        ("BattleKeywords.json", "EN_BattleKeywords.json", "battle_keyword"),
    ]:
        for key, pair in paired_rows(local_file, en_file).items():
            current = pairs.setdefault(key, {"category": category})
            current.update(pair)
            current["category"] = category if current.get("category") != "status" else "status"

    for status_key, pair in pairs.items():
        local = pair.get("local") or {}
        en = pair.get("en") or {}
        conn.execute(
            """
            INSERT OR REPLACE INTO status_effects(
              status_key, name_en, name_th, desc_en, desc_th, summary_en, summary_th,
              icon_path, category, raw_en_json, raw_th_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                status_key,
                en.get("name"),
                local.get("name"),
                en.get("desc"),
                local.get("desc"),
                en.get("summary"),
                local.get("summary"),
                icons.get(status_key),
                pair.get("category"),
                dumps(en) if en else None,
                dumps(local) if local else None,
            ),
        )
        for lang, row in [("en", en), ("th", local)]:
            for field in ["name", "desc", "summary"]:
                if row.get(field):
                    conn.execute(
                        "INSERT INTO localization_entries(source_key, category, language, field_name, text, source_file) VALUES (?, ?, ?, ?, ?, ?)",
                        (status_key, pair.get("category"), lang, field, row.get(field), "localization_full"),
                    )
        if icons.get(status_key):
            conn.execute(
                "INSERT OR IGNORE INTO assets(asset_type, target_key, path, metadata_json) VALUES (?, ?, ?, ?)",
                ("status_icon", status_key, icons[status_key], "{}"),
            )
    return len(pairs)


def insert_panic_info(conn: sqlite3.Connection, panic_info_dir: Path | None) -> int:
    if not panic_info_dir or not panic_info_dir.exists():
        return 0

    local_by_id: dict[str, dict[str, Any]] = {}
    en_by_id: dict[str, dict[str, Any]] = {}
    source_by_id: dict[str, str] = {}

    for path in sorted(panic_info_dir.glob("*PanicInfo*.json")):
        is_en = path.name.startswith("EN_")
        target = en_by_id if is_en else local_by_id
        for row in data_list(path):
            panic_id = str(row.get("id") or "").strip()
            if not panic_id:
                continue
            target[panic_id] = row
            source_by_id.setdefault(panic_id, path.name.removeprefix("EN_"))

    count = 0
    for panic_id in sorted(set(local_by_id) | set(en_by_id), key=lambda value: (len(value), value)):
        local = local_by_id.get(panic_id) or {}
        en = en_by_id.get(panic_id) or {}
        conn.execute(
            """
            INSERT OR REPLACE INTO panic_info(
              panic_id, name_en, name_th, low_morale_en, low_morale_th,
              panic_en, panic_th, source_file, raw_en_json, raw_th_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                panic_id,
                en.get("panicName"),
                local.get("panicName"),
                en.get("lowMoraleDescription"),
                local.get("lowMoraleDescription"),
                en.get("panicDescription"),
                local.get("panicDescription"),
                source_by_id.get(panic_id),
                dumps(en) if en else None,
                dumps(local) if local else None,
            ),
        )
        for language, row in [("en", en), ("th", local)]:
            for field_name, text_value in [
                ("panicName", row.get("panicName")),
                ("lowMoraleDescription", row.get("lowMoraleDescription")),
                ("panicDescription", row.get("panicDescription")),
            ]:
                if text_value:
                    conn.execute(
                        "INSERT INTO localization_entries(source_key, category, language, field_name, text, source_file) VALUES (?, ?, ?, ?, ?, ?)",
                        (panic_id, "panic_info", language, field_name, text_value, source_by_id.get(panic_id)),
                    )
        count += 1
    return count

def insert_mental_conditions(conn: sqlite3.Connection, localization_dir: Path | None) -> int:
    if not localization_dir or not localization_dir.exists():
        return 0

    local_by_id: dict[str, dict[str, Any]] = {}
    en_by_id: dict[str, dict[str, Any]] = {}
    source_by_id: dict[str, str] = {}

    for path in sorted(localization_dir.glob("*MentalCondition*.json")):
        is_en = path.name.startswith("EN_")
        target = en_by_id if is_en else local_by_id
        for row in data_list(path):
            condition_id = str(row.get("id") or "").strip()
            if not condition_id:
                continue
            target[condition_id] = row
            source_by_id.setdefault(condition_id, path.name.removeprefix("EN_"))

    count = 0
    for condition_id in sorted(set(local_by_id) | set(en_by_id)):
        local = local_by_id.get(condition_id) or {}
        en = en_by_id.get(condition_id) or {}
        conn.execute(
            """
            INSERT OR REPLACE INTO mental_conditions(
              condition_id, add_en, add_th, min_en, min_th, source_file, raw_en_json, raw_th_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                condition_id,
                en.get("add"),
                local.get("add"),
                en.get("min"),
                local.get("min"),
                source_by_id.get(condition_id),
                dumps(en) if en else None,
                dumps(local) if local else None,
            ),
        )
        for language, row in [("en", en), ("th", local)]:
            for field_name, text_value in [("add", row.get("add")), ("min", row.get("min"))]:
                if text_value:
                    conn.execute(
                        "INSERT INTO localization_entries(source_key, category, language, field_name, text, source_file) VALUES (?, ?, ?, ?, ?, ?)",
                        (condition_id, "mental_condition", language, field_name, text_value, source_by_id.get(condition_id)),
                    )
        count += 1
    return count

def build_database(data_dir: Path, out: Path, clean: bool, panic_info_dir: Path | None = None) -> dict[str, int]:
    if clean and out.exists():
        out.unlink()
    with connect(out) as conn:
        init_db(conn)
        identity_count = insert_identities(conn, data_dir)
        status_count = insert_status_effects(conn, data_dir)
        panic_count = insert_panic_info(conn, panic_info_dir)
        mental_condition_count = insert_mental_conditions(conn, panic_info_dir)
        skill_count = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
        passive_count = conn.execute("SELECT COUNT(*) FROM passives").fetchone()[0]
        conn.execute(
            "INSERT INTO import_audit(source, kind, records, details_json) VALUES (?, ?, ?, ?)",
            (str(data_dir), "build_sqlite_database", identity_count, dumps({"statuses": status_count, "panic_info": panic_count, "mental_conditions": mental_condition_count})),
        )
        conn.commit()
    return {
        "identities": identity_count,
        "skills": skill_count,
        "passives": passive_count,
        "status_effects": status_count,
        "panic_info": panic_count,
        "mental_conditions": mental_condition_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the shared SQLite database from exported Limbus JSON data.")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "limbus.sqlite")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--panic-info-dir", type=Path, default=ROOT / "work" / "sample_data" / "localization_full")
    args = parser.parse_args()
    stats = build_database(args.data, args.out, args.clean, args.panic_info_dir)
    print("SQLite database built")
    print(f"  DB: {args.out}")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



