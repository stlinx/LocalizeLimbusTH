from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DECK_BY_SLOT = {"skill_1": 3, "skill_2": 2, "skill_3": 1}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_attack_weight(text: str | None, fallback: Any = None) -> int | None:
    if not text:
        return fallback
    # Prefer the skill header line, not later effect text such as "Atk Weight +1".
    match = re.search(r"\[img:Skill(?:Attack|Defense)\.png\][^\n]*Atk Weight\s*([^\n]*)", text)
    if not match:
        match = re.search(r"(?:SkillAttack|SkillDefense)\.png\][^\n]*Atk Weight\s*([^\n]*)", text)
    if not match:
        return fallback
    tail = match.group(1)
    squares = sum(tail.count(symbol) for symbol in ("\u2bc0", "\u25a0", "\u25ae", "?"))
    if squares:
        return squares
    number = re.search(r"\b(\d+)\b", tail)
    return int(number.group(1)) if number else fallback


def parse_deck_count(text: str | None, slot: str | None, fallback: Any = None) -> int | None:
    if text:
        match = re.search(r"Amt\.\s*x\s*(\d+)", text)
        if match:
            return int(match.group(1))
    return DECK_BY_SLOT.get(slot or "") or fallback


def patch_skill(skill: dict[str, Any]) -> bool:
    slot = skill.get("slot")
    desc = skill.get("english_description") or skill.get("raw_text") or ""
    old_weight = skill.get("attack_weight")
    deck_count = parse_deck_count(desc, slot, skill.get("deck_count"))
    new_weight = parse_attack_weight(desc, old_weight)
    if new_weight == old_weight and slot in DECK_BY_SLOT and old_weight == DECK_BY_SLOT[slot]:
        new_weight = 1
    changed = False
    if deck_count is not None and skill.get("deck_count") != deck_count:
        skill["deck_count"] = deck_count
        changed = True
    if new_weight != old_weight:
        skill["attack_weight"] = new_weight
        changed = True
    return changed


def patch_identity_file(path: Path) -> tuple[int, int]:
    data = read_json(path)
    skills = data.get("skills") or []
    changed = sum(1 for skill in skills if patch_skill(skill))
    if changed:
        write_json(path, data)
    return changed, len(skills)


def patch_batch(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    data = read_json(path)
    changed = 0
    total = 0
    for entry in data.get("files") or []:
        identity = entry.get("data") or {}
        for skill in identity.get("skills") or []:
            total += 1
            if patch_skill(skill):
                changed += 1
    if changed:
        write_json(path, data)
    return changed, total


def patch_sqlite(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(skills)")}
        if "deck_count" not in columns:
            conn.execute("ALTER TABLE skills ADD COLUMN deck_count INTEGER")
        rows = conn.execute("SELECT id, slot, attack_weight, description_en FROM skills").fetchall()
        changed = 0
        for row in rows:
            deck_count = parse_deck_count(row["description_en"], row["slot"], None)
            new_weight = parse_attack_weight(row["description_en"], row["attack_weight"])
            if new_weight == row["attack_weight"] and row["slot"] in DECK_BY_SLOT and row["attack_weight"] == DECK_BY_SLOT[row["slot"]]:
                new_weight = 1
            if new_weight != row["attack_weight"] or deck_count is not None:
                conn.execute(
                    "UPDATE skills SET attack_weight = ?, deck_count = ? WHERE id = ?",
                    (new_weight, deck_count, row["id"]),
                )
                changed += 1
        conn.commit()
        return changed
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Split deck count from attack weight in identity data.")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--batch", type=Path, default=ROOT / "inputs" / "limbus_identity_batch.json")
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "limbus.sqlite")
    args = parser.parse_args()

    file_changed = 0
    file_total = 0
    for path in sorted((args.data / "identities" / "en").glob("*.json")):
        changed, total = patch_identity_file(path)
        file_changed += changed
        file_total += total
    batch_changed, batch_total = patch_batch(args.batch)
    db_changed = patch_sqlite(args.db)
    print(f"EN skills patched: {file_changed}/{file_total}")
    print(f"Batch skills patched: {batch_changed}/{batch_total}")
    print(f"SQLite skill rows patched: {db_changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
