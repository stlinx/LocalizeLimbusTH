from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .db import connect
from simulator.statuses import status_registry_summary, status_rule_for


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "limbus.sqlite"
BOSS_FIXTURE_PATH = ROOT / "data" / "bosses" / "manual_bosses.json"
BOSS_REVIEWED_DIR = ROOT / "data" / "bosses" / "reviewed"
IDENTITY_BATCH = ROOT / "inputs" / "limbus_identity_batch.json"
_LOCALIZED_IDENTITY_CACHE: dict[str, str] | None = None
NORMALIZE_ALIASES = {
    "yisang": "yi sang",
    "donquixote": "don quixote",
    "honglu": "hong lu",
    "ryoshu": "ryoshu",
    "ryoushu": "ryoshu",
    "rodya": "rodion",
}


def norm(value: str | None) -> str:
    value = value or ""
    value = re.sub(r"\.(json|png|jpg|jpeg|webp|gif|html)$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^\d+px-", "", value)
    for src, dst in NORMALIZE_ALIASES.items():
        value = re.sub(src, dst, value, flags=re.IGNORECASE)
    value = value.replace("??????????", "??????????????")
    value = value.replace("\u0e1a\u0e49\u0e32\u0e19\u0e41\u0e21\u0e07\u0e21\u0e38\u0e21", "\u0e1a\u0e49\u0e32\u0e19\u0e41\u0e2b\u0e48\u0e07\u0e41\u0e21\u0e07\u0e21\u0e38\u0e21")
    for phrase in (
        "\u0e1a\u0e49\u0e32\u0e19\u0e41\u0e2b\u0e48\u0e07\u0e41\u0e21\u0e07\u0e21\u0e38\u0e21",
        "\u0e1e\u0e48\u0e2d\u0e17\u0e39\u0e19\u0e2b\u0e31\u0e27",
        "\u0e25\u0e39\u0e01\u0e28\u0e34\u0e29\u0e22\u0e4c",
        "\u0e19\u0e34\u0e49\u0e27\u0e0a\u0e35\u0e49",
        "\u0e19\u0e34\u0e49\u0e27\u0e01\u0e25\u0e32\u0e07",
        "\u0e19\u0e34\u0e49\u0e27\u0e19\u0e32\u0e07",
        "\u0e19\u0e34\u0e49\u0e27\u0e01\u0e49\u0e2d\u0e22",
        "\u0e19\u0e34\u0e49\u0e27\u0e42\u0e1b\u0e49\u0e07",
    ):
        value = value.replace(phrase, f" {phrase} ")
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"[^\w\u0E00-\u0E7F]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip().lower()



def strip_game_markup(value: str | None) -> str:
    value = value or ""
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\u2019", "'").replace("\u2018", "'")
    value = value.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", value).strip()


def normalize_condition_text(value: str | None) -> str:
    value = strip_game_markup(value).lower()
    value = value.replace("higher than or equal", "greater than or equal")
    value = value.replace("higher or equal", "greater than or equal")
    value = value.replace("unit's", "unit's")
    value = re.sub(r"[^a-z0-9%+.'-]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def fill_template(template: str | None, values: list[str]) -> str | None:
    if not template:
        return None
    result = strip_game_markup(template)
    for index, value in enumerate(values):
        result = result.replace("{" + str(index) + "}", value)
    return result


def template_match_values(template: str | None, text_value: str) -> list[str] | None:
    if not template:
        return None
    template_norm = normalize_condition_text(template)
    text_norm = normalize_condition_text(text_value)
    parts: list[str] = []
    pattern = ""
    cursor = 0
    for match in re.finditer(r"\{(\d+)\}", template_norm):
        pattern += re.escape(template_norm[cursor:match.start()])
        pattern += r"([0-9]+(?:\.[0-9]+)?|[+-]?[0-9]+%?)"
        parts.append(match.group(1))
        cursor = match.end()
    pattern += re.escape(template_norm[cursor:])
    pattern = pattern.replace(r"\ ", r"\s+")
    found = re.search(pattern, text_norm)
    if not found:
        return None
    values_by_index: dict[int, str] = {}
    for index_text, value in zip(parts, found.groups()):
        values_by_index.setdefault(int(index_text), value)
    if not values_by_index:
        return []
    return [values_by_index.get(index, "") for index in range(max(values_by_index) + 1)]


def manual_mental_condition_match(text_value: str, direction: str, rows: list[sqlite3.Row]) -> dict[str, Any] | None:
    norm_text = normalize_condition_text(text_value)
    candidates: list[tuple[str, list[str]]] = []
    if "winning a clash" in norm_text and "base value is" in norm_text:
        nums = re.findall(r"\d+", norm_text)
        if len(nums) >= 2:
            candidates.append(("OnWinDuelAsParryingCountMultiplyAndPlusPercent", [nums[0], nums[1]]))
    if "this unit defeats an enemy" in norm_text and "greater than or equal" in norm_text:
        nums = re.findall(r"\d+", norm_text)
        if nums:
            candidates.append(("OnKillEnemyAsLevelRatioMultiply", [nums[0]]))
    if "ally defeats an enemy" in norm_text and "greater than or equal" in norm_text:
        nums = re.findall(r"\d+", norm_text)
        if nums:
            candidates.append(("OnKillEnemyByOtherAllyAsLevelRatioMultiply", [nums[0]]))
    if "defeated ally" in norm_text and "level difference" in norm_text:
        nums = re.findall(r"\d+", norm_text)
        if nums:
            candidates.append(("OnDieAllyAsLevelRatio", [nums[0]]))
    if "blade lineage ally is defeated" in norm_text:
        nums = re.findall(r"\d+", norm_text)
        if nums:
            candidates.append(("OnDieBladeLineageAlly", [nums[0]]))
    by_id = {row["condition_id"]: row for row in rows}
    for condition_id, values in candidates:
        row = by_id.get(condition_id)
        if row:
            target = row["add_th"] if direction == "increase" else row["min_th"]
            return {
                "condition_id": condition_id,
                "text": fill_template(target, values) or text_value,
                "values": values,
                "matched_by": "manual",
            }
    return None


def localize_mental_factor(text_value: str, direction: str, rows: list[sqlite3.Row]) -> dict[str, Any]:
    source_field = "add_en" if direction == "increase" else "min_en"
    target_field = "add_th" if direction == "increase" else "min_th"
    for row in rows:
        values = template_match_values(row[source_field], text_value)
        if values is not None:
            return {
                "condition_id": row["condition_id"],
                "text": fill_template(row[target_field], values) or text_value,
                "values": values,
                "matched_by": "template",
            }
    manual = manual_mental_condition_match(text_value, direction, rows)
    if manual:
        return manual
    return {"condition_id": None, "text": text_value, "values": [], "matched_by": "none"}


def localize_sanity_factors(sanity: dict[str, Any], mental_rows: list[sqlite3.Row]) -> dict[str, list[dict[str, Any]]]:
    factors = sanity.get("factors") or {}
    return {
        "increase": [localize_mental_factor(text_value, "increase", mental_rows) for text_value in factors.get("increase") or []],
        "decrease": [localize_mental_factor(text_value, "decrease", mental_rows) for text_value in factors.get("decrease") or []],
    }

def clean_game_text(value: str | None) -> str:
    value = value or ""
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\[img:[^\]]+\]", " ", value)
    value = re.sub(r"[\[\]]", " ", value)
    value = value.replace(".", " ")
    return re.sub(r"\s+", " ", value).strip().lower()


def format_panic_row(row: sqlite3.Row, lang: str = "th") -> dict[str, Any]:
    use_th = lang == "th" and row["name_th"]
    return {
        "panic_id": row["panic_id"],
        "name": row["name_th"] if use_th else row["name_en"],
        "name_en": row["name_en"],
        "name_th": row["name_th"],
        "low_morale": row["low_morale_th"] if use_th and row["low_morale_th"] else row["low_morale_en"],
        "low_morale_en": row["low_morale_en"],
        "low_morale_th": row["low_morale_th"],
        "panic": row["panic_th"] if use_th and row["panic_th"] else row["panic_en"],
        "panic_en": row["panic_en"],
        "panic_th": row["panic_th"],
        "source_file": row["source_file"],
        "language": "th" if use_th else "en",
    }


def match_panic_info(sanity: dict[str, Any], rows: list[sqlite3.Row]) -> sqlite3.Row | None:
    panic_type = sanity.get("panic_type") or {}
    name = clean_game_text(panic_type.get("name"))
    panic_text = clean_game_text(panic_type.get("panic"))
    best: tuple[int, sqlite3.Row] | None = None
    for row in rows:
        score = 0
        if name and name == clean_game_text(row["name_en"]):
            score += 100
        if panic_text and panic_text == clean_game_text(row["panic_en"]):
            score += 80
        if name == "panic" and row["panic_id"] == "9999":
            score += 50
        if score and (best is None or score > best[0]):
            best = (score, row)
    return best[1] if best else None
def loads(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return fallback
    return json.loads(value)


def localized_identity_names() -> dict[str, str]:
    global _LOCALIZED_IDENTITY_CACHE
    if _LOCALIZED_IDENTITY_CACHE is not None:
        return _LOCALIZED_IDENTITY_CACHE
    result: dict[str, str] = {}
    if IDENTITY_BATCH.exists():
        data = json.loads(IDENTITY_BATCH.read_text(encoding="utf-8"))
        for item in data.get("files", []):
            identity = (item.get("data") or {}).get("identity") or {}
            identity_id = str(identity.get("id") or "")
            localized_name = identity.get("localized_name")
            if identity_id and localized_name:
                result[identity_id] = re.sub(r"\s+", " ", str(localized_name)).strip()
    _LOCALIZED_IDENTITY_CACHE = result
    return result


def localized_identity_name(identity_id: str, fallback: str | None = None) -> str | None:
    return localized_identity_names().get(str(identity_id)) or fallback


def compact_norm(value: str | None) -> str:
    return norm(value).replace(" ", "")


def score_alias(query: str, alias: str, source: str) -> int:
    q = norm(query)
    a = norm(alias)
    if not q or not a:
        return 0
    if q == a:
        return 5000 if source in {"english_name", "identity_id"} else 4300
    if q in a:
        return 4100 + len(q)
    cq = q.replace(" ", "")
    ca = a.replace(" ", "")
    if cq and cq in ca:
        return 4050 + len(cq)
    q_tokens = q.split()
    a_tokens = set(a.split())
    hits = sum(1 for token in q_tokens if token in a_tokens)
    compact_hits = sum(1 for token in q_tokens if token and token in ca and token not in a_tokens)
    weighted_hits = hits + compact_hits
    if weighted_hits == len(q_tokens):
        return 3000 + weighted_hits * 100
    return weighted_hits * 350


def search_identity(query: str, db_path: Path = DEFAULT_DB, limit: int = 8) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT a.identity_id, a.alias, a.source, i.english_name, i.localized_name, i.sinner, i.rarity
            FROM identity_search_aliases a
            JOIN identities i ON i.identity_id = a.identity_id
            """
        ).fetchall()

    full_local_names = localized_identity_names()
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        full_local_name = full_local_names.get(str(row["identity_id"]))
        score = max(
            score_alias(query, row["alias"], row["source"]),
            score_alias(query, full_local_name or "", "localized_identity_name"),
        )
        if row["source"] == "sinner" and norm(query) == norm(row["alias"]) and norm(row["english_name"]) == norm(f"LCB Sinner {row['alias']}"):
            score += 500
        if score <= 0:
            continue
        current = best.get(row["identity_id"])
        if not current or score > current["score"]:
            best[row["identity_id"]] = {
                "identity_id": row["identity_id"],
                "english_name": row["english_name"],
                "localized_name": full_local_name or row["localized_name"],
                "localized_identity_name": full_local_name,
                "localized_sinner_name": row["localized_name"],
                "sinner": row["sinner"],
                "rarity": row["rarity"],
                "matched_alias": row["alias"],
                "match_source": row["source"],
                "score": score,
            }

    return sorted(best.values(), key=lambda item: item["score"], reverse=True)[:limit]



def skill_sort_key(skill: dict[str, Any]) -> tuple[int, str]:
    slot = str(skill.get("slot") or "")
    match = re.search(r"(\d+)$", slot)
    if slot.startswith("skill_") and match:
        return (int(match.group(1)), slot)
    if slot == "defense":
        return (99, slot)
    return (50, slot)

def get_identity_profile(identity_id: str, db_path: Path = DEFAULT_DB, uptie: int = 4, lang: str = "th") -> dict[str, Any]:
    with connect(db_path) as conn:
        identity = conn.execute("SELECT * FROM identities WHERE identity_id = ?", (identity_id,)).fetchone()
        if not identity:
            raise ValueError(f"No identity found for id: {identity_id}")
        skill_rows = conn.execute(
            "SELECT * FROM skills WHERE identity_id = ? AND uptie = ? ORDER BY slot, source_skill_text_id",
            (identity_id, uptie),
        ).fetchall()
        skill_row_ids = [row["id"] for row in skill_rows]
        coin_rows_by_skill: dict[int, list[sqlite3.Row]] = {}
        if skill_row_ids:
            placeholders = ",".join("?" for _ in skill_row_ids)
            coin_rows = conn.execute(
                f"SELECT * FROM coins WHERE skill_row_id IN ({placeholders}) ORDER BY coin_index, effect_index",
                skill_row_ids,
            ).fetchall()
            for coin_row in coin_rows:
                coin_rows_by_skill.setdefault(coin_row["skill_row_id"], []).append(coin_row)
        passive_rows = conn.execute(
            "SELECT * FROM passives WHERE identity_id = ? ORDER BY passive_type, id",
            (identity_id,),
        ).fetchall()
        panic_rows = conn.execute("SELECT * FROM panic_info").fetchall()
        mental_rows = conn.execute("SELECT * FROM mental_conditions").fetchall()

    skills = []
    for row in skill_rows:
        skills.append(
            {
                "slot": row["slot"],
                "uptie": row["uptie"],
                "source_skill_text_id": row["source_skill_text_id"],
                "name": {"en": row["name_en"]},
                "localized_name": row["name_th"],
                "affinity": row["affinity"],
                "damage_type": row["damage_type"],
                "skill_type": row["skill_type"],
                "base_power": row["base_power"],
                "coin_power": row["coin_power"],
                "coin_count": row["coin_count"],
                "deck_count": row["deck_count"] if "deck_count" in row.keys() else None,
                "attack_weight": row["attack_weight"],
                "offense_level": loads(row["offense_level_json"], {}),
                "english_description": row["description_en"],
                "localized_description": row["description_th"],
                "coin_texts": [
                    {
                        "coin_index": coin["coin_index"],
                        "effect_index": coin["effect_index"],
                        "en": coin["text_en"],
                    }
                    for coin in coin_rows_by_skill.get(row["id"], [])
                    if coin["text_en"]
                ],
                "localized_coin_texts": [
                    {
                        "coin_index": coin["coin_index"],
                        "effect_index": coin["effect_index"],
                        "text": coin["text_th"],
                    }
                    for coin in coin_rows_by_skill.get(row["id"], [])
                    if coin["text_th"]
                ],
                "combat_mechanics": loads(row["mechanics_json"], None),
                "assets": loads(row["assets_json"], {}),
            }
        )

    skills.sort(key=skill_sort_key)

    passives: dict[str, list[dict[str, Any]]] = {}
    localized_passives: dict[str, list[dict[str, Any]]] = {}
    for row in passive_rows:
        passive_type = row["passive_type"] or "combat"
        passives.setdefault(passive_type, []).append(
            {
                "source_passive_text_id": row["source_passive_text_id"],
                "name": {"en": row["name_en"]},
                "requirement": row["requirement"],
                "en": row["description_en"],
            }
        )
        localized_passives.setdefault(passive_type, []).append(
            {
                "source_passive_text_id": row["source_passive_text_id"],
                "name": row["name_th"],
                "description": row["description_th"],
            }
        )

    sanity = loads(identity["sanity_json"], {})
    matched_panic = match_panic_info(sanity, panic_rows)
    localized_sanity = {
        "panic_info": format_panic_row(matched_panic, lang) if matched_panic else None,
        "factors": localize_sanity_factors(sanity, mental_rows) if lang == "th" else None,
    }

    return {
        "schema_version": 1,
        "kind": "limbus_identity_profile",
        "query": identity["english_name"],
        "lang": lang,
        "uptie": uptie,
        "identity": {
            "id": identity["identity_id"],
            "english_name": identity["english_name"],
            "sinner": identity["sinner"],
            "rarity": identity["rarity"],
        },
        "localized_identity_name": {"th": localized_identity_name(identity["identity_id"])},
        "localized_personality": {"th": identity["localized_name"]},
        "combat_stats": {
            "hp": identity["hp"],
            "defense_level": identity["defense_level"],
            "speed_by_uptie": loads(identity["speed_by_uptie_json"], {}),
            "stagger_thresholds": loads(identity["stagger_thresholds_json"], []),
            "panic": identity["panic_text"],
            "sanity": sanity,
            "localized_sanity": localized_sanity,
            "resistances": {
                "slash": identity["slash_resistance"],
                "pierce": identity["pierce_resistance"],
                "blunt": identity["blunt_resistance"],
            },
        },
        "skills": skills,
        "passives": passives,
        "localized_passives": localized_passives,
        "combat_available": identity["combat_json"] is not None,
        "db_source": str(db_path),
    }


def get_identity_profile_by_query(query: str, db_path: Path = DEFAULT_DB, uptie: int = 4, lang: str = "th") -> dict[str, Any]:
    matches = search_identity(query, db_path=db_path, limit=1)
    if not matches:
        raise ValueError(f"No identity found for: {query}")
    profile = get_identity_profile(matches[0]["identity_id"], db_path=db_path, uptie=uptie, lang=lang)
    profile["match"] = matches[0]
    return profile


def get_status_effect(query: str, db_path: Path = DEFAULT_DB, lang: str = "th") -> dict[str, Any]:
    q = norm(query)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM status_effects").fetchall()
    scored = []
    for row in rows:
        aliases = [row["status_key"], row["name_en"], row["name_th"]]
        score = max(score_alias(q, alias or "", "status") for alias in aliases)
        if score > 0:
            scored.append((score, row))
    if not scored:
        raise ValueError(f"No status effect found for: {query}")
    scored.sort(key=lambda item: item[0], reverse=True)
    row = scored[0][1]
    return {
        "status_key": row["status_key"],
        "name": row["name_th"] if lang == "th" and row["name_th"] else row["name_en"],
        "name_en": row["name_en"],
        "name_th": row["name_th"],
        "description": row["desc_th"] if lang == "th" and row["desc_th"] else row["desc_en"],
        "summary": row["summary_th"] if lang == "th" and row["summary_th"] else row["summary_en"],
        "icon_path": row["icon_path"],
        "category": row["category"],
        "combat_rule": status_rule_for(row["status_key"], row["name_en"]),
    }


def list_status_effects(db_path: Path = DEFAULT_DB, lang: str = "th", limit: int = 1000) -> dict[str, Any]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM status_effects ORDER BY category, name_en, status_key LIMIT ?", (int(limit),)).fetchall()
    items = []
    counts: dict[str, int] = {}
    for row in rows:
        rule = status_rule_for(row["status_key"], row["name_en"])
        implementation = rule.get("implementation") or "display_only"
        counts[implementation] = counts.get(implementation, 0) + 1
        items.append(
            {
                "status_key": row["status_key"],
                "name": row["name_th"] if lang == "th" and row["name_th"] else row["name_en"],
                "name_en": row["name_en"],
                "name_th": row["name_th"],
                "category": row["category"],
                "icon_path": row["icon_path"],
                "combat_rule": rule,
            }
        )
    return {
        "items": items,
        "count": len(items),
        "implementation_counts": counts,
        "registry": status_registry_summary(),
    }


def load_manual_bosses(path: Path = BOSS_FIXTURE_PATH) -> dict[str, Any]:
    if not path.exists():
        payload = {"schema_version": 1, "source": "manual_fixture", "bosses": []}
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
    bosses = list(payload.get("bosses") or [])
    if BOSS_REVIEWED_DIR.exists():
        by_id = {str(boss.get("boss_id")): boss for boss in bosses if boss.get("boss_id")}
        for reviewed_path in sorted(BOSS_REVIEWED_DIR.glob("*.json")):
            try:
                reviewed = json.loads(reviewed_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            boss_id = str(reviewed.get("boss_id") or reviewed_path.stem)
            if not boss_id:
                continue
            reviewed.setdefault("boss_id", boss_id)
            reviewed["source"] = reviewed.get("source") or "reviewed_fixture"
            reviewed["reviewed_override"] = True
            by_id[boss_id] = reviewed
        bosses = list(by_id.values())
    payload = dict(payload)
    payload["bosses"] = bosses
    return payload


def _boss_search_text(boss: dict[str, Any]) -> list[str]:
    values = [boss.get("boss_id"), boss.get("name_en"), boss.get("name_th")]
    for part in boss.get("body_parts") or []:
        values.extend([part.get("part_id"), part.get("name_en"), part.get("name_th")])
    for skill in boss.get("skills") or []:
        values.extend([skill.get("skill_id"), skill.get("name_en"), skill.get("name_th")])
    return [str(value) for value in values if value]


def search_bosses(query: str = "", limit: int = 8) -> dict[str, Any]:
    payload = load_manual_bosses()
    bosses = payload.get("bosses") or []
    if not query:
        matches = bosses[:limit]
    else:
        q = norm(query)
        scored = []
        for boss in bosses:
            score = max((score_alias(q, alias, "boss") for alias in _boss_search_text(boss)), default=0)
            if score > 0:
                scored.append((score, boss))
        scored.sort(key=lambda item: item[0], reverse=True)
        matches = [boss for _, boss in scored[:limit]]
    return {
        "source": payload.get("source", "manual_fixture"),
        "schema_version": payload.get("schema_version"),
        "items": matches,
        "count": len(matches),
    }


def get_boss_profile(boss_id: str) -> dict[str, Any]:
    payload = load_manual_bosses()
    target = norm(boss_id)
    for boss in payload.get("bosses") or []:
        aliases = _boss_search_text(boss)
        if any(norm(alias) == target for alias in aliases):
            result = dict(boss)
            result["source"] = payload.get("source", "manual_fixture")
            result["fixture_warning"] = "Manual test fixture, not full official enemy import."
            return result
    raise ValueError(f"No boss fixture found for: {boss_id}")


def boss_condition_matches(condition: dict[str, Any] | None, turn: int, hp_percent: float) -> bool:
    if not condition:
        return True
    if condition.get("all"):
        return all(boss_condition_matches(item, turn, hp_percent) for item in condition["all"])
    if condition.get("any"):
        return any(boss_condition_matches(item, turn, hp_percent) for item in condition["any"])
    if "turn_eq" in condition and turn != int(condition["turn_eq"]):
        return False
    if "turn_lte" in condition and turn > int(condition["turn_lte"]):
        return False
    if "turn_gte" in condition and turn < int(condition["turn_gte"]):
        return False
    if "hp_lte" in condition and hp_percent > float(condition["hp_lte"]):
        return False
    if "hp_lt" in condition and hp_percent >= float(condition["hp_lt"]):
        return False
    if "hp_gte" in condition and hp_percent < float(condition["hp_gte"]):
        return False
    if "hp_gt" in condition and hp_percent <= float(condition["hp_gt"]):
        return False
    return True


def boss_skill_by_id(boss: dict[str, Any], skill_id: str | None) -> dict[str, Any] | None:
    if not skill_id:
        return None
    target = str(skill_id)
    for skill in boss.get("skills") or []:
        if str(skill.get("skill_id") or "") == target:
            return skill
    needle = norm(target)
    for skill in boss.get("skills") or []:
        if norm(skill.get("name_en")) == needle:
            return skill
    return None


def pick_boss_behavior_pattern(boss: dict[str, Any], turn: int, hp_percent: float) -> dict[str, Any] | None:
    behavior = boss.get("boss_behavior") or {}
    patterns = sorted(behavior.get("patterns") or [], key=lambda item: int(item.get("priority") or 0), reverse=True)
    for pattern in patterns:
        if boss_condition_matches(pattern.get("active_when"), turn, hp_percent):
            return pattern
    return None


def pick_boss_behavior_row(pattern: dict[str, Any] | None, turn: int) -> dict[str, Any] | None:
    rows = (pattern or {}).get("rows") or []
    if not rows:
        return None
    if pattern and pattern.get("row_mode") == "cycle":
        start_turn = int(pattern.get("cycle_start_turn") or 1)
        return rows[((turn - start_turn) % len(rows) + len(rows)) % len(rows)]
    return rows[0]


def _raw_rotation_rows(boss: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in ((boss.get("skill_rotation") or {}).get("raw_lines") or []):
        if not isinstance(line, str) or not line.startswith("- "):
            continue
        values = [part.strip() for part in line[2:].split(",") if part.strip()]
        if values:
            rows.append(values)
    return rows


def get_boss_turn_intent(boss_id: str, turn: int = 1, hp_percent: float = 100.0) -> dict[str, Any]:
    boss = get_boss_profile(boss_id)
    turn = max(1, int(turn))
    hp_percent = max(1.0, min(100.0, float(hp_percent)))
    behavior = boss.get("boss_behavior") or {}
    pattern = pick_boss_behavior_pattern(boss, turn, hp_percent)
    row = pick_boss_behavior_row(pattern, turn)
    source = behavior.get("source") or "raw_skill_rotation_fallback"
    notes: list[str] = []
    skill_ids: list[str] = []
    boss_sp = 0
    speed_bonus = 0

    if pattern and row:
        skill_ids = [str(item) for item in row.get("skills") or []]
        boss_sp = int(row.get("boss_sp", pattern.get("boss_sp", 0)) or 0)
        speed_bonus = int(row.get("speed_bonus", pattern.get("speed_bonus", 0)) or 0)
        notes.extend(behavior.get("notes") or [])
        notes.extend(pattern.get("notes") or [])
        notes.extend(row.get("notes") or [])
    else:
        rows = _raw_rotation_rows(boss)
        source = "raw_skill_rotation_fallback"
        if not rows:
            skill_ids = [str(skill.get("skill_id") or skill.get("name_en") or "") for skill in (boss.get("skills") or [])[:3]]
            notes.append("No structured boss_behavior or raw rotation rows were found.")
        elif turn <= 2 and hp_percent > 90:
            skill_ids = rows[0]
            notes.append("Fallback from raw wiki behavior text.")
        elif (hp_percent <= 90 or turn >= 3) and hp_percent > 80:
            skill_ids = rows[1] if len(rows) > 1 else rows[0]
            boss_sp = 10
            notes.append("Fallback from raw wiki behavior text.")
        else:
            cycle = rows[2:5] or rows[1:2] or rows[:1]
            skill_ids = cycle[((turn - 5) % len(cycle) + len(cycle)) % len(cycle)]
            boss_sp = 30 if hp_percent <= 40 else 20
            notes.append("Fallback from raw wiki behavior text.")

    speed_range = boss.get("speed_range") or ((boss.get("body_parts") or [{}])[0].get("speed_range")) or "1~8"
    slots = []
    for index, skill_ref in enumerate(skill_ids, start=1):
        skill = boss_skill_by_id(boss, skill_ref) or {}
        slots.append(
            {
                "slot_index": index,
                "skill_ref": skill_ref,
                "skill_id": skill.get("skill_id") or skill_ref,
                "name_en": skill.get("name_en") or skill_ref,
                "name_th": skill.get("name_th"),
            }
        )

    return {
        "boss_id": boss.get("boss_id"),
        "turn": turn,
        "hp_percent": hp_percent,
        "source": source,
        "review_status": behavior.get("review_status"),
        "pattern": pattern,
        "row": row,
        "boss_sp": boss_sp,
        "speed_bonus": speed_bonus,
        "speed_range": speed_range,
        "slots": slots,
        "notes": notes,
        "warnings": [
            "Boss intent uses structured behavior when available, but status/passive execution is still partial.",
        ],
    }

def get_panic_info(query: str, db_path: Path = DEFAULT_DB, lang: str = "th") -> dict[str, Any]:
    q = norm(query)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM panic_info").fetchall()
    scored = []
    for row in rows:
        aliases = [row["panic_id"], row["name_en"], row["name_th"], row["low_morale_en"], row["low_morale_th"], row["panic_en"], row["panic_th"]]
        score = max(score_alias(q, alias or "", "panic_info") for alias in aliases)
        if score > 0:
            scored.append((score, row))
    if not scored:
        raise ValueError(f"No panic info found for: {query}")
    scored.sort(key=lambda item: item[0], reverse=True)
    row = scored[0][1]
    return format_panic_row(row, lang)
