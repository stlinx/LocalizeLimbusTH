from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(path)


def is_missing(value: Any) -> bool:
    return value is None or value == ""


def validate_identity_pair(en_path: Path, th_path: Path, root: Path, errors: list[str], warnings: list[str], stats: Counter) -> None:
    en = load_json(en_path)
    th = load_json(th_path)
    stats["en_files"] += 1

    en_identity = en.get("identity") or {}
    if en.get("kind") != "limbus_identity":
        errors.append(f"{rel(en_path, root)}: kind must be limbus_identity")
    if th.get("kind") != "limbus_identity_locale":
        errors.append(f"{rel(th_path, root)}: kind must be limbus_identity_locale")
    if en_identity.get("id") != th.get("identity_id"):
        errors.append(f"{rel(en_path, root)}: identity id does not match locale file")
    if "localized_name" in en_identity:
        errors.append(f"{rel(en_path, root)}: English file should not contain identity.localized_name")

    th_skill_keys = Counter((s.get("source_skill_text_id"), s.get("slot"), s.get("uptie")) for s in th.get("skills") or [])
    th_passive_ids = Counter()
    for rows in (th.get("passives") or {}).values():
        for passive in rows or []:
            th_passive_ids[passive.get("source_passive_text_id")] += 1

    for skill in en.get("skills") or []:
        stats["skills"] += 1
        skill_key = (skill.get("source_skill_text_id"), skill.get("slot"), skill.get("uptie"))
        if not th_skill_keys[skill_key]:
            errors.append(f"{rel(en_path, root)}: missing TH skill link {skill_key}")
        if "localized_description" in skill:
            errors.append(f"{rel(en_path, root)}: English skill {skill_key} still has localized_description")
        if (skill.get("name") or {}).get("local") is not None:
            errors.append(f"{rel(en_path, root)}: English skill {skill_key} still has name.local")
        if is_missing(skill.get("english_description")):
            warnings.append(f"{rel(en_path, root)}: EN skill {skill_key} has no english_description")
        for coin in skill.get("coin_texts") or []:
            stats["coin_texts"] += 1
            if "local" in coin:
                errors.append(f"{rel(en_path, root)}: English coin text still has local field for {skill_key}")

    for skill in th.get("skills") or []:
        skill_key = (skill.get("source_skill_text_id"), skill.get("slot"), skill.get("uptie"))
        if is_missing(skill.get("name")):
            warnings.append(f"{rel(th_path, root)}: TH skill {skill_key} has no localized name")
        if is_missing(skill.get("description")):
            warnings.append(f"{rel(th_path, root)}: TH skill {skill_key} has no localized description")

    for passive_type, rows in (en.get("passives") or {}).items():
        for passive in rows or []:
            stats["passives"] += 1
            passive_id = passive.get("source_passive_text_id")
            if passive_id and not th_passive_ids[passive_id]:
                errors.append(f"{rel(en_path, root)}: missing TH passive link {passive_type}/{passive_id}")
            if (passive.get("name") or {}).get("local") is not None:
                errors.append(f"{rel(en_path, root)}: English passive {passive_id} still has name.local")
            if "local" in passive:
                errors.append(f"{rel(en_path, root)}: English passive {passive_id} still has local field")


def resolve_index_path(data_dir: Path, value: str) -> Path:
    raw = Path(value)
    parts = raw.parts
    if parts and parts[0] == "data":
        return data_dir.joinpath(*parts[1:])
    return data_dir / raw


def validate_index(data_dir: Path, errors: list[str], stats: Counter) -> None:
    index_path = data_dir / "indexes" / "identity_search_index.json"
    if not index_path.exists():
        errors.append("Missing data/indexes/identity_search_index.json")
        return
    index = load_json(index_path)
    items = index.get("items") or []
    stats["index_items"] = len(items)
    if index.get("count") != len(items):
        errors.append("Search index count does not match item length")
    for item in items:
        for key in ["file", "locale_file"]:
            path = resolve_index_path(data_dir, item.get(key, ""))
            if not path.exists():
                errors.append(f"Search index points to missing {key}: {item.get(key)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate split Limbus identity database files.")
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--max-warnings", type=int, default=80)
    args = parser.parse_args()

    data_dir = args.data
    en_dir = data_dir / "identities" / "en"
    th_dir = data_dir / "identities" / "locales" / "th"
    errors: list[str] = []
    warnings: list[str] = []
    stats: Counter = Counter()

    en_files = sorted(en_dir.glob("*.json"))
    th_files = {path.name: path for path in th_dir.glob("*.json")}
    if not en_files:
        errors.append(f"No English identity files found in {en_dir}")
    for en_path in en_files:
        th_path = th_files.get(en_path.name)
        if not th_path:
            errors.append(f"{rel(en_path, data_dir)}: missing matching TH locale file")
            continue
        validate_identity_pair(en_path, th_path, data_dir, errors, warnings, stats)

    extra_th = sorted(set(th_files) - {path.name for path in en_files})
    for filename in extra_th:
        errors.append(f"TH locale file has no English pair: {filename}")

    validate_index(data_dir, errors, stats)

    print("Identity database validation")
    print(f"  EN files: {stats['en_files']}")
    print(f"  Index items: {stats['index_items']}")
    print(f"  Skills: {stats['skills']}")
    print(f"  Coin text rows: {stats['coin_texts']}")
    print(f"  Passives: {stats['passives']}")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print("\nErrors")
        for item in errors[: args.max_warnings]:
            print(f"  - {item}")
        if len(errors) > args.max_warnings:
            print(f"  ... {len(errors) - args.max_warnings} more")
    if warnings:
        print("\nWarnings")
        for item in warnings[: args.max_warnings]:
            print(f"  - {item}")
        if len(warnings) > args.max_warnings:
            print(f"  ... {len(warnings) - args.max_warnings} more")

    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()

