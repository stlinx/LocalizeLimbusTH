from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


SINNER_NAMES = [
    "Don Quixote",
    "Yi Sang",
    "Meursault",
    "Heathcliff",
    "Ishmael",
    "Sinclair",
    "Hong Lu",
    "Gregor",
    "Rodion",
    "Ryoshu",
    "Ry\u014dsh\u016b",
    "Faust",
    "Outis",
]

AFFINITIES = ["Wrath", "Lust", "Sloth", "Gluttony", "Gloom", "Pride", "Envy"]
DAMAGE_OR_DEFENSE_TYPES = ["Slash", "Pierce", "Blunt", "Guard", "Evade", "Counter"]


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "img":
            alt = attrs_dict.get("alt")
            if alt:
                self.parts.append(f" [img:{alt}] ")
        elif tag in {"p", "div", "tr", "table", "ul"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "tr", "table", "ul"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return clean_text("".join(self.parts))


def html_to_text(fragment: str) -> str:
    parser = TextExtractor()
    parser.feed(fragment)
    return parser.text()


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def first_match(pattern: str, text: str, flags: int = 0) -> str | None:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"-?\d+", value)
    return int(match.group(0)) if match else None


def page_title(raw_html: str) -> str:
    h1 = first_match(r'<h1[^>]*id="firstHeading"[^>]*>(.*?)</h1>', raw_html, re.S | re.I)
    if h1:
        return html_to_text(h1)
    title = first_match(r"<title[^>]*>(.*?)</title>", raw_html, re.S | re.I) or "Unknown"
    return re.sub(r"\s*-\s*Limbus Company Wiki.*$", "", html_to_text(title)).strip()


def split_identity_and_sinner(title: str) -> tuple[str, str | None]:
    normalized_title = title.replace("_", " ").strip()
    for sinner in sorted(SINNER_NAMES, key=len, reverse=True):
        if normalized_title.endswith(f" {sinner}"):
            return normalized_title[: -(len(sinner) + 1)].strip(), sinner
    return normalized_title, None


def parse_speed_by_uptie(raw_html: str) -> dict[str, str]:
    speeds: dict[str, str] = {}
    status_match = re.search(r"<b>Status</b>(?P<body>.*?)<b>Stagger Thresholds</b>", raw_html, re.S | re.I)
    if not status_match:
        return speeds
    body = status_match.group("body")
    for uptie, speed in re.findall(
        r'id="mw-customcollapsible-ut(\d+)".{0,1800}?<div class="mw-collapsible-content"[^>]*>(\d+\s*[~\-]\s*\d+)</div>',
        body,
        re.S | re.I,
    ):
        speeds[f"uptie_{uptie}"] = speed.replace(" ", "").replace("-", "~")
    return dict(sorted(speeds.items()))


def parse_sanity_info(raw_html: str) -> dict[str, Any]:
    match = re.search(r'id="Sanity-0".*?</article>', raw_html, re.S | re.I)
    if not match:
        return {}
    text = html_to_text(match.group(0))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result: dict[str, Any] = {"raw_text": text}

    panic_icon_index = next((index for index, line in enumerate(lines) if "General Panic" in line), None)
    if panic_icon_index is not None:
        panic_name = lines[panic_icon_index + 1] if panic_icon_index + 1 < len(lines) else None
        low_morale = lines[panic_icon_index + 2] if panic_icon_index + 2 < len(lines) else None
        panic_effect = lines[panic_icon_index + 3] if panic_icon_index + 3 < len(lines) else None
        result["panic_type"] = {
            "name": panic_name,
            "low_morale": None if low_morale == "-" else low_morale,
            "panic": None if panic_effect == "-" else panic_effect,
        }

    increasing: list[str] = []
    decreasing: list[str] = []
    current: list[str] | None = None
    for line in lines:
        if line == "Base factors increasing Sanity":
            current = increasing
            continue
        if line == "Base factors decreasing Sanity":
            current = decreasing
            continue
        if current is not None and line.startswith("-"):
            current.append(line.removeprefix("-").strip())
        elif current is not None and current and line.startswith("("):
            current[-1] = f"{current[-1]} {line}"
    result["factors"] = {"increase": increasing, "decrease": decreasing}
    return result

def parse_basic_info(raw_html: str, text: str) -> dict[str, Any]:
    rarity = parse_int(first_match(r"IDNumber(\d+)\.png", raw_html))
    release = first_match(r"Release\s+(\d{4}\.\d{2}\.\d{2})", text)
    if release:
        release = release.replace(".", "-")

    traits = sorted(
        set(
            clean_text(t)
            for t in re.findall(r'title="Category:([^"]+?) Identities"', raw_html)
            if t and not t.startswith("Season ")
        )
    )

    hp = None
    defense_level = None
    status = re.search(r"\[img:HP\.png\]\s*(\d+).*?\[img:Defense\.png\]\s*(\d+)", text, re.S)
    if status:
        hp = int(status.group(1))
        defense_level = int(status.group(2))

    stagger_thresholds = [
        {"percent": int(percent), "hp": int(hp_value)}
        for percent, hp_value in re.findall(r"(\d+)%\s*\((\d+)\s*\[img:HP\.png\]", text)
    ]

    resistance_matches = re.search(
        r"\[img:Slash\.png\].*?\[img:Pierce\.png\].*?\[img:Blunt\.png\](?P<body>.*?)(?:Panic Type|Uptie:)",
        text,
        re.S,
    )
    resistances: dict[str, dict[str, Any]] = {}
    if resistance_matches:
        labels = re.findall(r"(Ineff\.|Normal|Fatal|Weak|Resist)\s*\[x([0-9.]+)\]", resistance_matches.group("body"))
        for damage_type, pair in zip(["slash", "pierce", "blunt"], labels):
            label, multiplier = pair
            resistances[damage_type] = {"label": label, "multiplier": float(multiplier)}

    sanity = parse_sanity_info(raw_html)
    panic = ((sanity.get("panic_type") or {}).get("panic") if sanity else None) or first_match(
        r"Panic Type.*?Low Morale\s+Panic\s+.*?-\s+(.*?)\s+Factors Affecting Sanity",
        text,
        re.S,
    )

    return {
        "rarity": rarity,
        "release_date": release,
        "traits": traits,
        "stats": {
            "hp": hp,
            "speed_by_uptie": parse_speed_by_uptie(raw_html),
            "defense_level": defense_level,
            "stagger_thresholds": stagger_thresholds,
            "resistances": resistances,
            "panic": panic,
            "sanity": sanity,
        },
    }


def nearest_preceding(pattern: str, text: str, end: int, default: str | None = None) -> str | None:
    found = None
    for match in re.finditer(pattern, text[:end], re.S | re.I):
        found = match.group(1)
    return found if found is not None else default


def skill_slot_from_panel(panel_id: str | None) -> str | None:
    if not panel_id:
        return None
    if panel_id.startswith("Skill_1"):
        return "skill_1"
    if panel_id.startswith("Skill_2"):
        return "skill_2"
    if panel_id.startswith("Skill_3"):
        return "skill_3"
    if panel_id.startswith("Defense"):
        return "defense"
    return None


def parse_skill_block(raw_block: str) -> dict[str, Any]:
    block_text = html_to_text(raw_block)
    alts = re.findall(r'alt="([^"]+)"', raw_block)

    name_candidates = re.findall(r'<div style="margin-right:20px">(.*?)</div>', raw_block, re.S | re.I)
    name = html_to_text(name_candidates[0]) if name_candidates else None

    affinity = None
    rank = None
    for alt in alts:
        for candidate in AFFINITIES:
            match = re.fullmatch(rf"{candidate}(\d+)\.png", alt)
            if match:
                affinity = candidate
                rank = int(match.group(1))
                break
        if affinity:
            break

    skill_type = None
    damage_type = None
    for alt in alts:
        clean_alt = alt.removesuffix(".png")
        if clean_alt in {"SkillAttack", "SkillDefense"}:
            skill_type = "attack" if clean_alt == "SkillAttack" else "defense"
        if clean_alt in DAMAGE_OR_DEFENSE_TYPES:
            if clean_alt in {"Guard", "Evade", "Counter"}:
                skill_type = clean_alt.lower()
            else:
                damage_type = clean_alt.lower()

    power_match = re.search(
        r"<b>\s*(-?\d+)\s*</b>\s*<img[^>]+alt=\"(?:Slash|Pierce|Blunt|Guard|Evade|Counter)\.png\"[^>]*>\s*<b>\s*([+-])\s*(\d+)\s*</b>",
        raw_block,
        re.S | re.I,
    )
    base_power = int(power_match.group(1)) if power_match else None
    coin_power = f"{power_match.group(2)}{power_match.group(3)}" if power_match else None

    level_match = re.search(r"\[img:Skill(?:Attack|Defense)\.png\]\s*(\d+)\s*\((\d+)\s*([+-])\s*(\d+)\)", block_text)
    level = None
    if level_match:
        level = {
            "total": int(level_match.group(1)),
            "base": int(level_match.group(2)),
            "correction": int(f"{level_match.group(3)}{level_match.group(4)}"),
        }

    coin_count = len(re.findall(r'alt="Coin(?: - [^"]+)?\.png"', raw_block))
    deck_count = parse_int(first_match(r"Amt\.\s*x(\d+)", block_text))
    weight_match = re.search(r"\[img:Skill(?:Attack|Defense)\.png\][^\n]*Atk Weight\s*([^\n]*)", block_text)
    attack_weight = weight_match.group(1).count("?") if weight_match else None
    icon_alt = next((alt for alt in alts if " Icon.png" in alt or " Def Icon.png" in alt), None)

    effects = block_text
    if name:
        index = effects.find(name)
        if index != -1:
            effects = effects[index + len(name) :].strip()

    return {
        "name": name,
        "affinity": affinity,
        "rank": rank,
        "skill_type": skill_type,
        "damage_type": damage_type,
        "base_power": base_power,
        "coin_power": coin_power,
        "coin_count": coin_count,
        "deck_count": deck_count,
        "level": level,
        "attack_weight": attack_weight,
        "icon_alt": icon_alt,
        "effects_text": clean_text(effects),
        "raw_text": block_text,
    }


def parse_skills(raw_html: str) -> list[dict[str, Any]]:
    skills: list[dict[str, Any]] = []
    block_pattern = re.compile(
        r'(<td style="vertical-align:top; text-align:center"><div class="skillIcon".*?</td></tr></tbody></table>)',
        re.S | re.I,
    )
    seen: set[tuple[str | None, str | None, int | None, str | None]] = set()
    for match in block_pattern.finditer(raw_html):
        start = match.start()
        block = match.group(1)
        panel_id = nearest_preceding(r'<article class="tabber__panel"[^>]+id="([^"]+)"', raw_html, start)
        uptie = nearest_preceding(r'id="mw-customcollapsible-ut(\d+)"', raw_html, start)
        parsed = parse_skill_block(block)
        slot = skill_slot_from_panel(panel_id)
        key = (slot, parsed["name"], parsed["base_power"], uptie)
        if key in seen:
            continue
        seen.add(key)
        parsed.update(
            {
                "slot": slot,
                "wiki_panel_id": panel_id,
                "uptie": int(uptie) if uptie else None,
                "confidence": "medium" if parsed["name"] and parsed["base_power"] is not None else "low",
            }
        )
        skills.append(parsed)
    return skills


def extract_named_text_blocks(section_html: str) -> list[dict[str, Any]]:
    blocks = []
    pattern = re.compile(
        r'<div style="padding:10px"><div style="width: fit-content".*?<div style="margin-right:20px">(?P<name>.*?)</div>.*?</div></div></div>(?P<body>.*?)(?=<div style="padding:10px"><div style="width: fit-content"|<div style="background:#810000|</div>\s*</div>\s*</div>)',
        re.S | re.I,
    )
    seen_names: set[str] = set()
    for match in pattern.finditer(section_html):
        name = clean_text(match.group("name"))
        if name in seen_names:
            continue
        body = clean_text(html_to_text(match.group("body")))
        if body and "Locked until Tier" not in body:
            blocks.append({"name": name, "text": body})
            seen_names.add(name)
    return blocks


def parse_passives(raw_html: str) -> dict[str, list[dict[str, Any]]]:
    combat_html = first_match(r"<b>Combat Passives?</b></div>(.*?)(?:<b>Support Passive</b></div>|</body>)", raw_html, re.S | re.I) or ""
    support_html = first_match(r"<b>Support Passive</b></div>(.*?)(?:<h2|</body>)", raw_html, re.S | re.I) or ""
    return {
        "combat": extract_named_text_blocks(combat_html),
        "support": extract_named_text_blocks(support_html),
    }


def import_identity_html(path: Path) -> dict[str, Any]:
    raw_html = path.read_text(encoding="utf-8", errors="ignore")
    text = html_to_text(raw_html)
    title = page_title(raw_html)
    identity_name, sinner = split_identity_and_sinner(title)
    data = parse_basic_info(raw_html, text)
    if sinner is None:
        fallback_title = re.sub(r"\s*-\s*Limbus Company Wiki$", "", path.stem).strip()
        identity_name, sinner = split_identity_and_sinner(fallback_title)
    data.update(
        {
            "source": {"type": "wiki_html", "path": str(path)},
            "wiki_title": title,
            "identity_name": identity_name,
            "sinner": sinner,
            "skills": parse_skills(raw_html),
            "passives": parse_passives(raw_html),
            "import_notes": [
                "HTML import is intended as an admin-curation draft.",
                "Skill/passive effects are kept as cleaned raw text until we add deeper effect parsing.",
            ],
        }
    )
    return data


def iter_html_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    return sorted([*input_path.glob("*.html"), *input_path.glob("*.htm")])


def write_summary(imports: list[dict[str, Any]], out_path: Path) -> None:
    lines = [
        "# Wiki HTML Import Summary",
        "",
        f"Imported files: {len(imports)}",
        "",
        "| Identity | Sinner | Rarity | HP | Skills | Combat Passives | Support Passives |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in imports:
        stats = item.get("stats", {})
        passives = item.get("passives", {})
        lines.append(
            "| {identity} | {sinner} | {rarity} | {hp} | {skills} | {combat} | {support} |".format(
                identity=item.get("identity_name") or "",
                sinner=item.get("sinner") or "",
                rarity=item.get("rarity") or "",
                hp=stats.get("hp") or "",
                skills=len(item.get("skills", [])),
                combat=len(passives.get("combat", [])),
                support=len(passives.get("support", [])),
            )
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import saved Limbus Company wiki identity HTML pages.")
    parser.add_argument("input", type=Path, help="HTML file or folder containing saved wiki HTML files.")
    parser.add_argument("--out", type=Path, default=Path("outputs/wiki_identity_imports.json"))
    parser.add_argument("--summary", type=Path, default=Path("outputs/wiki_identity_imports_summary.md"))
    args = parser.parse_args()

    html_files = iter_html_files(args.input)
    imports = [import_identity_html(path) for path in html_files]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"identities": imports}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_summary(imports, args.summary)

    print(f"Imported {len(imports)} HTML file(s)")
    print(f"Wrote {args.out}")
    print(f"Wrote {args.summary}")


if __name__ == "__main__":
    main()






