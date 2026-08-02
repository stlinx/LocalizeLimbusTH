from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "work" / "sample_data" / "localization_full"
OUTPUT_DIR = ROOT / "outputs"
REPORT_JSON = OUTPUT_DIR / "localization_import_report.json"
REPORT_MD = OUTPUT_DIR / "localization_import_report.md"


ENCODINGS = ("utf-8-sig", "utf-8", "utf-16", "cp874", "cp1252")


@dataclass
class ParsedFile:
    path: Path
    encoding: str | None
    sha256: str
    parsed: bool
    data: dict[str, Any] | None
    error: str | None


def read_text_with_fallback(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    for encoding in ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8-replace"


def parse_file(path: Path) -> ParsedFile:
    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    try:
        text, encoding = read_text_with_fallback(path)
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("top-level JSON value is not an object")
        return ParsedFile(path, encoding, sha256, True, data, None)
    except Exception as exc:  # Keep import resilient; record exact file failure.
        return ParsedFile(path, None, sha256, False, None, f"{type(exc).__name__}: {exc}")


def language_for(name: str) -> str:
    return "en" if name.startswith("EN_") else "local"


def counterpart_name(name: str) -> str | None:
    if name.startswith("EN_"):
        return name[3:]
    return f"EN_{name}"


def category_for(name: str) -> str:
    base = name[3:] if name.startswith("EN_") else name
    stem = Path(base).stem
    if stem.startswith("Skills_Ego_Personality"):
        return "ego_personality_skills"
    if stem.startswith("Skills_personality"):
        return "identity_skills"
    if stem == "Skills_Ego":
        return "ego_skills"
    if stem == "Skills":
        return "generic_skills"
    if stem.startswith("Passive_Ego"):
        return "ego_passives"
    if stem.startswith("Passives_Assist"):
        return "assist_passives"
    if stem.startswith("Passive-"):
        return "special_passives"
    if stem == "Passives":
        return "identity_passives"
    if stem.startswith("Personalities"):
        return "identities"
    if stem == "Bufs":
        return "status_effects"
    if stem == "BuffAbilities":
        return "buff_abilities"
    if stem == "BattleKeywords":
        return "battle_keywords"
    return "unknown"


def data_list(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not data:
        return []
    value = data.get("dataList", [])
    return value if isinstance(value, list) else []


def id_set(parsed: ParsedFile) -> set[str]:
    ids: set[str] = set()
    for item in data_list(parsed.data):
        if isinstance(item, dict) and "id" in item:
            ids.add(str(item["id"]))
    return ids


def skill_level_count(parsed: ParsedFile) -> int:
    total = 0
    for item in data_list(parsed.data):
        if not isinstance(item, dict):
            continue
        levels = item.get("levelList", [])
        if isinstance(levels, list):
            total += len(levels)
    return total


def coin_text_count(parsed: ParsedFile) -> int:
    total = 0
    for item in data_list(parsed.data):
        if not isinstance(item, dict):
            continue
        for level in item.get("levelList", []) or []:
            if not isinstance(level, dict):
                continue
            for coin in level.get("coinlist", []) or []:
                if not isinstance(coin, dict):
                    continue
                total += len(coin.get("coindescs", []) or [])
    return total


def sample_records(parsed: ParsedFile, limit: int = 3) -> list[dict[str, Any]]:
    records = []
    for item in data_list(parsed.data)[:limit]:
        if not isinstance(item, dict):
            continue
        record: dict[str, Any] = {"id": item.get("id")}
        for key in ("name", "title", "nameWithTitle", "desc", "summary"):
            value = item.get(key)
            if isinstance(value, str):
                record[key] = value[:160]
        levels = item.get("levelList")
        if isinstance(levels, list) and levels:
            first_level = levels[0]
            if isinstance(first_level, dict):
                record["first_level"] = {
                    "level": first_level.get("level"),
                    "name": first_level.get("name"),
                    "desc": str(first_level.get("desc", ""))[:160],
                    "coin_count": len(first_level.get("coinlist", []) or []),
                }
        records.append(record)
    return records


def build_report() -> dict[str, Any]:
    files = sorted(DATA_DIR.glob("*.json"))
    parsed_files = [parse_file(path) for path in files]
    by_name = {item.path.name: item for item in parsed_files}

    file_rows = []
    category_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    parse_counts: Counter[str] = Counter()
    aggregate = defaultdict(int)

    for item in parsed_files:
        name = item.path.name
        category = category_for(name)
        language = language_for(name)
        rows = data_list(item.data)
        row = {
            "file": name,
            "language": language,
            "category": category,
            "bytes": item.path.stat().st_size,
            "sha256": item.sha256,
            "parse_status": "parsed" if item.parsed else "parse_failed",
            "encoding": item.encoding,
            "error": item.error,
            "data_list_count": len(rows),
            "id_count": len(id_set(item)) if item.parsed else 0,
            "skill_level_count": skill_level_count(item) if item.parsed else 0,
            "coin_text_count": coin_text_count(item) if item.parsed else 0,
            "samples": sample_records(item) if item.parsed else [],
        }
        file_rows.append(row)
        category_counts[category] += 1
        language_counts[language] += 1
        parse_counts[row["parse_status"]] += 1
        aggregate["data_list_count"] += row["data_list_count"]
        aggregate["skill_level_count"] += row["skill_level_count"]
        aggregate["coin_text_count"] += row["coin_text_count"]

    pair_rows = []
    seen_pairs: set[tuple[str, str]] = set()
    for item in parsed_files:
        name = item.path.name
        other_name = counterpart_name(name)
        if not other_name or other_name not in by_name:
            continue
        pair_key = tuple(sorted((name, other_name)))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        left = by_name[pair_key[0]]
        right = by_name[pair_key[1]]
        left_ids = id_set(left) if left.parsed else set()
        right_ids = id_set(right) if right.parsed else set()
        pair_rows.append(
            {
                "files": list(pair_key),
                "both_parsed": left.parsed and right.parsed,
                "left_count": len(data_list(left.data)),
                "right_count": len(data_list(right.data)),
                "shared_ids": len(left_ids & right_ids),
                "left_only_ids": len(left_ids - right_ids),
                "right_only_ids": len(right_ids - left_ids),
            }
        )

    return {
        "source_dir": str(DATA_DIR),
        "file_count": len(files),
        "parse_counts": dict(parse_counts),
        "language_counts": dict(language_counts),
        "category_counts": dict(category_counts),
        "aggregate_counts": dict(aggregate),
        "files": file_rows,
        "pairs": pair_rows,
    }


def markdown_table(rows: list[list[Any]], headers: list[str]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("\n", " ") for cell in row) + " |")
    return "\n".join(lines)


def write_markdown(report: dict[str, Any]) -> None:
    parse_counts = report["parse_counts"]
    aggregate = report["aggregate_counts"]
    failed = [row for row in report["files"] if row["parse_status"] != "parsed"]
    parsed = [row for row in report["files"] if row["parse_status"] == "parsed"]
    pairs = report["pairs"]

    category_rows = sorted(report["category_counts"].items())
    top_files = sorted(parsed, key=lambda row: row["data_list_count"], reverse=True)[:15]
    pair_problem_rows = [
        pair for pair in pairs
        if not pair["both_parsed"] or pair["left_only_ids"] or pair["right_only_ids"]
    ]

    content = [
        "# Localization Import Report",
        "",
        f"Source directory: `{report['source_dir']}`",
        "",
        "## Summary",
        "",
        f"- Files scanned: `{report['file_count']}`",
        f"- Parsed: `{parse_counts.get('parsed', 0)}`",
        f"- Parse failed: `{parse_counts.get('parse_failed', 0)}`",
        f"- Total `dataList` records: `{aggregate.get('data_list_count', 0)}`",
        f"- Total skill level records: `{aggregate.get('skill_level_count', 0)}`",
        f"- Total coin text records: `{aggregate.get('coin_text_count', 0)}`",
        f"- EN/local file pairs found: `{len(pairs)}`",
        "",
        "## Categories",
        "",
        markdown_table([[name, count] for name, count in category_rows], ["Category", "Files"]),
        "",
        "## Largest Parsed Files",
        "",
        markdown_table(
            [
                [
                    row["file"],
                    row["language"],
                    row["category"],
                    row["data_list_count"],
                    row["skill_level_count"],
                    row["coin_text_count"],
                ]
                for row in top_files
            ],
            ["File", "Lang", "Category", "Records", "Skill Levels", "Coin Texts"],
        ),
        "",
        "## Pair Problems",
        "",
    ]

    if pair_problem_rows:
        content.append(
            markdown_table(
                [
                    [
                        " / ".join(pair["files"]),
                        pair["both_parsed"],
                        pair["shared_ids"],
                        pair["left_only_ids"],
                        pair["right_only_ids"],
                    ]
                    for pair in pair_problem_rows
                ],
                ["Pair", "Both Parsed", "Shared IDs", "Left Only", "Right Only"],
            )
        )
    else:
        content.append("No ID mismatches found among parsed EN/local pairs.")

    content.extend(["", "## Parse Failures", ""])
    if failed:
        content.append(
            markdown_table(
                [[row["file"], row["category"], row["error"]] for row in failed],
                ["File", "Category", "Error"],
            )
        )
    else:
        content.append("No parse failures.")

    content.extend(["", "## Recommended Next Step", ""])
    content.extend(
        [
            "Use this report to build the raw import database tables next:",
            "",
            "- `source_files` from every row in the file table.",
            "- `raw_identity_text` from `identities` files.",
            "- `raw_skill_text` and `raw_coin_text` from skill files.",
            "- `raw_passive_text` from passive files.",
            "- `raw_status_text` from status/buff files.",
            "- `import_errors` from parse failures.",
            "",
            "Do not publish simulator data directly from these files. They are source text and curation input.",
        ]
    )

    REPORT_MD.write_text("\n".join(content) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report)
    print(f"Scanned {report['file_count']} files")
    print(f"Parsed {report['parse_counts'].get('parsed', 0)} files")
    print(f"Failed {report['parse_counts'].get('parse_failed', 0)} files")
    print(f"Wrote {REPORT_JSON}")
    print(f"Wrote {REPORT_MD}")


if __name__ == "__main__":
    main()
