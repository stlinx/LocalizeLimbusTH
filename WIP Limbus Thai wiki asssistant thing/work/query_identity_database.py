from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def norm(value: str | None) -> str:
    value = value or ""
    value = value.lower()
    value = re.sub(r"[^0-9a-z]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def score_item(query: str, item: dict[str, Any]) -> int:
    q = norm(query)
    if not q:
        return 0
    fields = [
        item.get("english_name"),
        item.get("sinner"),
        str(item.get("identity_id") or ""),
        " ".join(item.get("skill_names") or []),
        " ".join(item.get("passive_names") or []),
        " ".join(item.get("tags") or []),
    ]
    hay = norm(" ".join(field for field in fields if field))
    if q == norm(item.get("english_name")):
        return 1000
    if q in hay:
        return 500 + len(q)
    parts = q.split()
    return sum(40 for part in parts if part in hay)


def resolve_data_path(data_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.parts and path.parts[0] == "data":
        return data_dir.joinpath(*path.parts[1:])
    return data_dir / path


def compact(text: str | None, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def print_identity(en: dict[str, Any], th: dict[str, Any] | None, show_locale: bool, uptie: int | None) -> None:
    identity = en.get("identity") or {}
    stats = en.get("combat_stats") or {}
    res = stats.get("resistances") or {}
    print(f"{identity.get('english_name')} [{identity.get('id')}]")
    print(f"Sinner: {identity.get('sinner')} | Rarity: {identity.get('rarity')}")
    print(f"HP: {stats.get('hp')} | Defense: {stats.get('defense_level')} | Speed: {stats.get('speed_by_uptie')}")
    print(f"Resist: Slash {res.get('slash')} / Pierce {res.get('pierce')} / Blunt {res.get('blunt')}")

    locale_by_key = {}
    if th:
        for skill in th.get("skills") or []:
            locale_by_key[(skill.get("source_skill_text_id"), skill.get("slot"), skill.get("uptie"))] = skill

    print("\nSkills")
    for skill in en.get("skills") or []:
        if uptie is not None and skill.get("uptie") != uptie:
            continue
        name = (skill.get("name") or {}).get("en")
        key = (skill.get("source_skill_text_id"), skill.get("slot"), skill.get("uptie"))
        print(
            f"- UT{skill.get('uptie')} {skill.get('slot')}: {name} | "
            f"{skill.get('affinity')} {skill.get('damage_type')} | "
            f"{skill.get('base_power')} {skill.get('coin_power')} x{skill.get('coin_count')} | "
            f"AtkWt {skill.get('attack_weight')}"
        )
        print(f"  EN: {compact(skill.get('english_description'))}")
        if show_locale and key in locale_by_key:
            print(f"  TH: {compact(locale_by_key[key].get('description'))}")

    print("\nPassives")
    for passive_type, rows in (en.get("passives") or {}).items():
        for passive in rows or []:
            name = (passive.get("name") or {}).get("en")
            print(f"- {passive_type}: {name}")
            print(f"  EN: {compact(passive.get('en'))}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Query the split Limbus identity database.")
    parser.add_argument("query", help="Identity name, sinner, ID, skill, or tag to search.")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--locale", default="th")
    parser.add_argument("--lang", choices=["en", "th", "both"], default=None, help="Shortcut for locale display.")
    parser.add_argument("--uptie", type=int, default=None, help="Only print skills for one uptie level.")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--show-locale", action="store_true")
    args = parser.parse_args()
    if args.lang in {"th", "both"}:
        args.show_locale = True

    data_dir = args.data.resolve()
    index_path = data_dir / "indexes" / "identity_search_index.json"
    index = load_json(index_path)
    matches = [
        (score_item(args.query, item), item)
        for item in index.get("items") or []
    ]
    matches = [(score, item) for score, item in matches if score > 0]
    matches.sort(key=lambda row: row[0], reverse=True)
    if not matches:
        print(f"No identity found for: {args.query}")
        raise SystemExit(1)

    best_score, best = matches[0]
    en_path = resolve_data_path(data_dir, best["file"])
    th_path = resolve_data_path(data_dir, best.get("locale_file", ""))
    en = load_json(en_path)
    th = load_json(th_path) if th_path.exists() else None
    print_identity(en, th, args.show_locale, args.uptie)

    if len(matches) > 1:
        print("\nOther matches")
        for score, item in matches[1 : args.top]:
            print(f"- {item.get('english_name')} [{item.get('identity_id')}] score={score}")


if __name__ == "__main__":
    main()


