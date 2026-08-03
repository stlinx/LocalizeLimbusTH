from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def text(value: Any, fallback: Any = None) -> Any:
    if value is None or value == "":
        return fallback
    return value


def pair_local(pair: dict[str, Any] | None) -> str | None:
    return text((pair or {}).get("local"))


def pair_en(pair: dict[str, Any] | None) -> str | None:
    return text((pair or {}).get("en"))


def read_number(value: Any) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        number = float(str(value))
    except ValueError:
        return value
    return int(number) if number.is_integer() else number


def slugify(value: str | None, fallback: str) -> str:
    value = value or fallback
    value = re.sub(r"[<>:\"/\\|?*]+", "_", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or fallback


def canon_value(target: dict[str, Any], key: str, fallback: Any = None) -> Any:
    edits = target.get("admin_edit") or {}
    value = edits.get(key)
    if value is not None and value != "":
        return value
    return fallback


def identity_name(item: dict[str, Any]) -> str:
    wiki = item.get("wiki_identity") or {}
    fallback = f"{text(wiki.get('identity_name'), '')} {text(wiki.get('sinner'), '')}".strip()
    return str(canon_value(item, "english_name", fallback))


def finalize_from_review_item(item: dict[str, Any]) -> dict[str, Any]:
    wiki = item.get("wiki_identity") or {}
    ident = item.get("localization_identity_match") or {}
    stats = wiki.get("stats") or {}
    resistances = stats.get("resistances") or {}
    name = identity_name(item)

    def resistance(kind: str) -> Any:
        source = resistances.get(kind) or {}
        return read_number(canon_value(item, f"res_{kind}", source.get("multiplier")))

    return {
        "schema_version": 1,
        "kind": "limbus_identity",
        "identity": {
            "id": text(ident.get("source_personality_id")),
            "english_name": name,
            "localized_name": f"{pair_local(ident.get('title')) or ''} {pair_local(ident.get('name')) or ''}".strip(),
            "sinner": canon_value(item, "sinner", wiki.get("sinner")),
            "rarity": read_number(canon_value(item, "rarity", wiki.get("rarity"))),
        },
        "combat_stats": {
            "hp": read_number(canon_value(item, "hp", stats.get("hp"))),
            "speed_by_uptie": stats.get("speed_by_uptie") or {},
            "defense_level": read_number(canon_value(item, "defense_level", stats.get("defense_level"))),
            "stagger_thresholds": stats.get("stagger_thresholds") or [],
            "panic": stats.get("panic"),
            "sanity": stats.get("sanity") or {},
            "resistances": {
                "slash": resistance("slash"),
                "pierce": resistance("pierce"),
                "blunt": resistance("blunt"),
            },
        },
        "skills": [finalize_skill(row) for row in item.get("skills") or []],
        "passives": {
            passive_type: [finalize_passive(row) for row in rows or []]
            for passive_type, rows in (item.get("passives") or {}).items()
        },
        "admin_strategy_notes": {
            "playstyle_summary": "",
            "important_conditions": [],
            "recommended_teams": [],
            "boss_notes": [],
            "rotation_notes": "",
        },
        "import_review": {
            "status": "reviewed_export",
            "source_html": wiki.get("source"),
        },
    }


def finalize_skill(row: dict[str, Any]) -> dict[str, Any]:
    wiki = row.get("wiki") or {}
    match = row.get("localization_match") or {}
    level = wiki.get("level") or {}
    return {
        "slot": wiki.get("slot") or match.get("slot"),
        "uptie": wiki.get("uptie"),
        "source_skill_text_id": match.get("source_skill_text_id"),
        "name": {
            "en": canon_value(row, "english_name", pair_en(match.get("name")) or wiki.get("name")),
            "local": pair_local(match.get("name")),
        },
        "affinity": canon_value(row, "affinity", wiki.get("affinity")),
        "damage_type": canon_value(row, "damage_type", wiki.get("damage_type")),
        "skill_type": wiki.get("skill_type"),
        "base_power": read_number(canon_value(row, "base_power", wiki.get("base_power"))),
        "coin_power": canon_value(row, "coin_power", wiki.get("coin_power")),
        "coin_count": read_number(canon_value(row, "coin_count", wiki.get("coin_count"))),
        "deck_count": read_number(canon_value(row, "deck_count", wiki.get("deck_count"))),
        "attack_weight": read_number(canon_value(row, "attack_weight", wiki.get("attack_weight"))),
        "offense_level": {
            **level,
            "total": read_number(canon_value(row, "offense_total", level.get("total"))),
        },
        "english_description": canon_value(row, "english_description", pair_en(match.get("desc")) or wiki.get("effects_text")),
        "localized_description": pair_local(match.get("desc")),
        "coin_texts": [
            {
                "coin_index": coin.get("coin_index"),
                "effect_index": coin.get("effect_index"),
                "en": pair_en(coin.get("desc")),
                "local": pair_local(coin.get("desc")),
            }
            for coin in match.get("coin_texts") or []
        ],
    }


def finalize_passive(row: dict[str, Any]) -> dict[str, Any]:
    wiki = row.get("wiki") or {}
    match = row.get("localization_match") or {}
    return {
        "source_passive_text_id": match.get("source_passive_text_id"),
        "name": {
            "en": canon_value(row, "english_name", pair_en(match.get("name")) or wiki.get("name")),
            "local": pair_local(match.get("name")),
        },
        "requirement": canon_value(row, "requirement", wiki.get("requirement")),
        "en": canon_value(row, "english_description", pair_en(match.get("desc")) or wiki.get("text") or wiki.get("description")),
        "local": pair_local(match.get("desc")),
    }


def load_identities(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("kind") == "limbus_identity_batch":
        return [entry["data"] for entry in data.get("files") or [] if entry.get("data")]
    if "identities" in data:
        return [finalize_from_review_item(item) for item in data.get("identities") or []]
    if data.get("kind") == "limbus_identity":
        return [data]
    raise ValueError(f"Unsupported input format: {path}")


def localized_identity(identity: dict[str, Any]) -> dict[str, Any]:
    base = identity.get("identity") or {}
    return {
        "schema_version": 1,
        "kind": "limbus_identity_locale",
        "identity_id": base.get("id"),
        "english_name": base.get("english_name"),
        "skills": [
            {
                "source_skill_text_id": skill.get("source_skill_text_id"),
                "slot": skill.get("slot"),
                "uptie": skill.get("uptie"),
                "name": (skill.get("name") or {}).get("local"),
                "description": skill.get("localized_description"),
                "coin_texts": [
                    {
                        "coin_index": coin.get("coin_index"),
                        "effect_index": coin.get("effect_index"),
                        "text": coin.get("local"),
                    }
                    for coin in skill.get("coin_texts") or []
                    if coin.get("local")
                ],
            }
            for skill in identity.get("skills") or []
        ],
        "passives": {
            passive_type: [
                {
                    "source_passive_text_id": passive.get("source_passive_text_id"),
                    "name": (passive.get("name") or {}).get("local"),
                    "description": passive.get("local"),
                }
                for passive in rows or []
            ]
            for passive_type, rows in (identity.get("passives") or {}).items()
        },
    }


def english_identity(identity: dict[str, Any]) -> dict[str, Any]:
    clean = json.loads(json.dumps(identity, ensure_ascii=False))
    if clean.get("identity"):
        clean["identity"].pop("localized_name", None)
    for skill in clean.get("skills") or []:
        skill.pop("localized_description", None)
        if skill.get("name"):
            skill["name"].pop("local", None)
        for coin in skill.get("coin_texts") or []:
            coin.pop("local", None)
    for rows in (clean.get("passives") or {}).values():
        for passive in rows or []:
            passive.pop("local", None)
            if passive.get("name"):
                passive["name"].pop("local", None)
    return clean


def search_doc(identity: dict[str, Any], filename: str) -> dict[str, Any]:
    base = identity.get("identity") or {}
    skills = identity.get("skills") or []
    passives = identity.get("passives") or {}
    tags = sorted(
        {
            str(value).lower()
            for skill in skills
            for value in [skill.get("affinity"), skill.get("damage_type")]
            if value
        }
    )
    return {
        "identity_id": base.get("id"),
        "english_name": base.get("english_name"),
        "sinner": base.get("sinner"),
        "rarity": base.get("rarity"),
        "file": f"data/identities/en/{filename}",
        "locale_file": f"data/identities/locales/th/{filename}",
        "skill_names": [(skill.get("name") or {}).get("en") for skill in skills],
        "passive_names": [
            (passive.get("name") or {}).get("en")
            for rows in passives.values()
            for passive in rows or []
        ],
        "tags": tags,
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Split reviewed Limbus identity data into bot database files.")
    parser.add_argument("--input", type=Path, default=Path("outputs/wiki_identity_localized_review.json"))
    parser.add_argument("--out", type=Path, default=Path("data"))
    parser.add_argument("--clean", action="store_true", help="Remove old identity output folders before writing.")
    args = parser.parse_args()

    output = args.out
    en_dir = output / "identities" / "en"
    th_dir = output / "identities" / "locales" / "th"
    index_dir = output / "indexes"
    if args.clean:
        for folder in [en_dir, th_dir, index_dir]:
            if folder.exists():
                shutil.rmtree(folder)

    identities = load_identities(args.input)
    index = []
    for identity in identities:
        base = identity.get("identity") or {}
        filename = slugify(base.get("english_name"), base.get("id") or "identity") + ".json"
        write_json(en_dir / filename, english_identity(identity))
        write_json(th_dir / filename, localized_identity(identity))
        index.append(search_doc(identity, filename))

    write_json(
        index_dir / "identity_search_index.json",
        {
            "schema_version": 1,
            "kind": "limbus_identity_search_index",
            "count": len(index),
            "items": index,
        },
    )
    print(f"Wrote {len(index)} identities")
    print(f"English: {en_dir}")
    print(f"Thai: {th_dir}")
    print(f"Index: {index_dir / 'identity_search_index.json'}")


if __name__ == "__main__":
    main()






