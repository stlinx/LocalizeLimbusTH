from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs" / "boss_imports"

DAMAGE_TYPES = ["Slash", "Pierce", "Blunt"]
AFFINITIES = ["Wrath", "Lust", "Sloth", "Gluttony", "Gloom", "Pride", "Envy"]
SECTION_STOP_LINES = {"Passives", "Behavior", "Battle Tips", "Dialogue", "Mirror Dungeon", "Rewards", "Strategy", "Skills"}
CARD_MARKER = '<div style="position:absolute;top:13.3px'


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
                self.parts.append(f" [{alt}] ")
        elif tag in {"p", "div", "tr", "table", "ul", "td", "th"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "tr", "table", "ul", "td", "th"}:
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


def clean_line(value: str) -> str:
    value = html.unescape(value).replace("\xa0", " ")
    value = re.sub(r"\.(?:png|jpg|jpeg|webp|gif)$", "", value, flags=re.I)
    value = re.sub(r"\[\d+px-([^\]]+)\]", r"[\1]", value)
    value = re.sub(r"\[([^\]]+?)\.(?:png|jpg|jpeg|webp|gif)\]", r"[\1]", value, flags=re.I)
    value = re.sub(
        r"\[(?:SkillAttack|Coin|Coin - Unbreakable|Abno Part Body|HP|Sanity|Offense|Defense|"
        r"Wrath\d(?:BG)?|Lust\d(?:BG)?|Sloth\d(?:BG)?|Gluttony\d(?:BG)?|Gloom\d(?:BG)?|Pride\d(?:BG)?|Envy\d(?:BG)?)\]",
        "",
        value,
    )
    value = value.replace("??", "?")
    value = re.sub(r"\[([^\]]{2,90})\]\s+\1\b", r"[\1]", value, flags=re.I)
    value = re.sub(r"\[([^\]]+?)\s+([^\]]+?)\]\s+\1\s+\[\2\]", r"[\1 \2]", value, flags=re.I)
    value = re.sub(r"\[(Unlock(?: - [IVX]+)?)\]\s+Unlock\b", r"[\1]", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def slugify(value: str, fallback: str = "boss") -> str:
    value = re.sub(r"[^0-9A-Za-z]+", "_", value).strip("_").lower()
    return value or fallback


def boss_id_from_title(title: str) -> str:
    base = re.sub(r"\s*-\s*Limbus Company Wiki.*$", "", title).strip()
    base = re.sub(r"/Enemy$", "", base).strip()
    return f"wiki_{slugify(base)}_draft"


def page_title(raw_html: str) -> str:
    h1 = re.search(r'<h1[^>]*id="firstHeading"[^>]*>(.*?)</h1>', raw_html, re.S | re.I)
    if h1:
        return html_to_text(h1.group(1))
    title = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.S | re.I)
    if title:
        return re.sub(r"\s*-\s*Limbus Company Wiki.*$", "", html_to_text(title.group(1))).strip()
    return "Unknown Boss"


def asset_dir_for_html(html_path: Path) -> Path | None:
    candidates = [html_path.with_name(html_path.stem + "_files")]
    # Saved pages sometimes replace ':' with '_' in the companion folder.
    candidates.append(html_path.parent / (html_path.stem.replace(":", "_") + "_files"))
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    folders = sorted(html_path.parent.glob("*_files"))
    return folders[0] if folders else None


def resolve_src(html_path: Path, src: str | None) -> str | None:
    if not src:
        return None
    src = html.unescape(src)
    if src.startswith("./"):
        return str((html_path.parent / src[2:]).resolve())
    if re.match(r"^[A-Za-z]:[\\/]", src):
        return str(Path(src).resolve())
    if src.startswith("http"):
        return src
    return str((html_path.parent / src).resolve())


def find_asset(asset_dir: Path | None, patterns: list[str]) -> str | None:
    if not asset_dir:
        return None
    files = list(asset_dir.iterdir())
    for pattern in patterns:
        regex = re.compile(pattern, re.I)
        for item in files:
            if item.is_file() and regex.search(item.name):
                return str(item.resolve())
    return None


def parse_int(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"-?\d+", value)
    return int(match.group(0)) if match else None


def parse_stats(raw_html: str) -> dict[str, Any]:
    level = parse_int(first_table_value(raw_html, "Level"))
    hp_match = re.search(r"Core\s*<img[^>]+alt=\"HP\.png\".*?<span[^>]*>(\d+)</span>", raw_html, re.S | re.I)
    hp = int(hp_match.group(1)) if hp_match else None
    defense_match = re.search(r"alt=\"Defense\.png\".*?<span[^>]*>(\d+)</span>", raw_html, re.S | re.I)
    defense = int(defense_match.group(1)) if defense_match else None
    stagger: list[dict[str, int]] = []
    for percent, hp_value in re.findall(r"(\d+)%\s*\((\d+)\s*<img[^>]+alt=\"HP\.png\"", raw_html, re.S | re.I):
        item = {"percent": int(percent), "hp": int(hp_value)}
        if item not in stagger:
            stagger.append(item)
    return {"level": level, "hp": hp, "defense_level": defense, "stagger_thresholds": stagger}


def first_table_value(raw_html: str, label: str) -> str | None:
    match = re.search(rf">\s*{re.escape(label)}\s*</td>\s*<td[^>]*>(.*?)</td>", raw_html, re.S | re.I)
    return html_to_text(match.group(1)) if match else None


def clean_skill_lines(fragment: str) -> list[str]:
    text = html_to_text(fragment)
    lines: list[str] = []
    for raw in text.splitlines():
        line = clean_line(raw)
        if not line or line in {"+", "|", "Body"}:
            continue
        if "data-file" in line or "decoding=" in line or "<" in line or ">" in line:
            continue
        if re.search(r"Rien\]$", line) and len(line) < 90:
            continue
        if len(line) > 260:
            continue
        lines.append(line)
    return lines


def visible_skill_cards(raw_html: str) -> list[tuple[int, int, int, str]]:
    cards: list[tuple[int, int, int, str]] = []
    starts = [match.start() for match in re.finditer(re.escape(CARD_MARKER), raw_html)]
    for index, card_start in enumerate(starts):
        next_start = starts[index + 1] if index + 1 < len(starts) else len(raw_html)
        segment = raw_html[card_start:next_start]
        attack_match = re.search(r'<img[^>]+alt=\"SkillAttack\.png\"', segment, re.I)
        if not attack_match:
            continue
        title_match = re.search(r'<div[^>]*style=\"[^\"]*margin-right:20px[^\"]*\"[^>]*>(.*?)</div>', segment[: attack_match.start()], re.S | re.I)
        if not title_match:
            continue
        title = clean_line(html_to_text(title_match.group(1)))
        if not title or title in {"Body", "Skill Effects"}:
            continue
        cards.append((card_start, card_start + title_match.start(1), card_start + attack_match.end(), title))
    # Deduplicate exact repeated cards that can appear in tooltip/collapsible copies,
    # but keep distinct skill variants such as "Double Slash" and "Double Slash - Blast".
    seen: set[tuple[str, int]] = set()
    result: list[tuple[int, int, int, str]] = []
    for card in cards:
        key = (card[3].lower(), card[0] // 1000)
        if key in seen:
            continue
        seen.add(key)
        result.append(card)
    return result


def skill_id(name: str, boss_name: str) -> str:
    suffix = slugify(boss_name.split("-")[-1].strip() or boss_name)
    return f"{suffix}_{slugify(name)}"


def skill_icon_path(html_path: Path, card_fragment: str, name: str, asset_dir: Path | None) -> str | None:
    candidate_names = [name]
    base_name = re.split(r"\s+-\s+", name, maxsplit=1)[0].strip()
    if base_name and base_name not in candidate_names:
        candidate_names.append(base_name)
    bracketless = re.sub(r"\s*\[[^\]]+\]", "", name).strip()
    if bracketless and bracketless not in candidate_names:
        candidate_names.append(bracketless)

    imgs = re.findall(r"<img\b[^>]*alt=\"([^\"]+)\"[^>]*src=\"([^\"]+)\"", card_fragment, re.I)
    for alt, src in imgs:
        alt_clean = html.unescape(alt)
        if "SkillAttack" in alt_clean or alt_clean.startswith("Coin"):
            continue
        if any(candidate.lower() in alt_clean.lower() for candidate in candidate_names):
            return resolve_src(html_path, src)
    patterns = []
    for candidate in candidate_names:
        normalized = re.sub(r"[^0-9A-Za-z]+", ".*", candidate)
        patterns.append(rf"74px-{normalized}.*\.(?:png|webp)$")
    return find_asset(asset_dir, patterns)


def parse_skill_numbers(lines: list[str]) -> tuple[int | None, int | None, int | None, str | None, str | None, str | None]:
    joined = " ".join(lines)
    attack_line = next((line for line in lines if re.search(r"\b\d+ \(\d+[+-]\d+\).*Atk Weight", line)), None)
    if not attack_line:
        attack_line = next((line for line in lines if "Atk Weight" in line and not re.search(r"\bgain\s+Atk Weight", line, re.I)), None)
    base = coin = coin_count = None
    damage = next((kind for kind in DAMAGE_TYPES if re.search(rf"\b{kind}\b", joined)), None)
    affinity = next((kind for kind in AFFINITIES if re.search(rf"\b{kind}\b", joined)), None)
    header = " ".join(lines[:8])
    match = re.search(r"\b(\d+)\s*(?:\[[^\]]+\])?\s*\+\s*(\d+)\b", header)
    if match:
        base = int(match.group(1))
        coin = int(match.group(2))
    coin_count = len(re.findall(r"\[CoinEffect\d+\]", "\n".join(lines))) or None
    return base, coin, coin_count, damage, affinity, attack_line


def split_skill_text(lines: list[str], title: str) -> tuple[str | None, list[str], list[str]]:
    useful = [line for line in lines if line.lower() != title.lower()]
    attack = next((line for line in useful if re.search(r"\b\d+ \(\d+[+-]\d+\).*Atk Weight", line)), None)
    if not attack:
        attack = next((line for line in useful if "Atk Weight" in line and not re.search(r"\bgain\s+Atk Weight", line, re.I)), None)
    if attack:
        useful = [line for line in useful if line != attack]
    # Remove pre-title/header leftovers.
    useful = [line for line in useful if not re.fullmatch(r"\d+", line) and not re.fullmatch(r"\+ ?\d+", line)]
    desc: list[str] = []
    coins: list[str] = []
    current_coin: list[str] | None = None
    for line in useful:
        if line in SECTION_STOP_LINES or re.match(r"^Phase\s+\d+$", line):
            break
        if line.startswith("[Hint ") or line.startswith("Collapse ") or line.startswith("Expand "):
            break
        if line.startswith("[CoinEffect"):
            if current_coin:
                coins.append(" ".join(current_coin))
            current_coin = [line]
            continue
        if current_coin is not None:
            if line in SECTION_STOP_LINES or line.startswith("[Hint ") or re.match(r"^Phase\s+\d+$", line):
                break
            current_coin.append(line)
            continue
        desc.append(line)
    if current_coin:
        coins.append(" ".join(current_coin))
    return attack, join_wrapped_lines(desc[:28]), [clean_line(row) for row in coins]


def join_wrapped_lines(lines: list[str]) -> list[str]:
    result: list[str] = []
    for line in lines:
        value = clean_line(line)
        if not value:
            continue
        if result and re.match(r"^(Count|stage \(|,|next turn|this turn)$", value, re.I):
            result[-1] = clean_line(result[-1] + " " + value)
        else:
            result.append(value)
    return result


def parse_skills(raw_html: str, html_path: Path, asset_dir: Path | None, boss_name: str) -> list[dict[str, Any]]:
    cards = visible_skill_cards(raw_html)
    skills: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for index, (card_start, _title_start, after_title, title) in enumerate(cards):
        if title.lower() in seen_names:
            continue
        seen_names.add(title.lower())
        end = cards[index + 1][0] if index + 1 < len(cards) else after_title + 9000
        card_fragment = raw_html[card_start:end]
        text_fragment = raw_html[after_title:end]
        full_lines = clean_skill_lines(card_fragment)
        lines = clean_skill_lines(text_fragment)
        attack, desc, coins = split_skill_text(lines, title)
        base, coin, coin_count, damage, affinity, header_attack = parse_skill_numbers(full_lines)
        attack = attack or header_attack
        skill = {
            "skill_id": skill_id(title, boss_name),
            "name_en": title,
            "slot": "boss_skill",
            "base_power": base,
            "coin_power": coin,
            "coin_count": coin_count,
            "damage_type_hint": damage,
            "affinity": affinity if affinity in AFFINITIES else None,
            "asset_path": skill_icon_path(html_path, card_fragment, title, asset_dir),
            "attack_level_text": attack,
            "description_lines": desc,
            "coin_effect_lines": coins,
        }
        skills.append({key: value for key, value in skill.items() if value not in (None, [], "")})
    return skills


def parse_unique_statuses(raw_html: str, html_path: Path) -> list[dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for alt, src in re.findall(r"<img\b[^>]*alt=\"([^\"]+)\"[^>]*src=\"([^\"]+)\"", raw_html, re.I):
        name = clean_line(alt)
        if not name or name.startswith(("SkillAttack", "CoinEffect")):
            continue
        if name in {"HP", "Sanity", "Defense", "Offense", "Coin", "SkillAttack", "Slash", "Pierce", "Blunt"}:
            continue
        if re.search(r"(?:Sprite|Icon|Logo|BG)$", name, re.I):
            continue
        if len(name) > 80:
            continue
        if name not in statuses:
            statuses[name] = {"status_key": name, "source_name": name, "icon_path": resolve_src(html_path, src)}
    # Keep likely combat statuses first and avoid filling page with every UI image.
    likely = []
    for item in statuses.values():
        name = item["source_name"]
        if re.search(r"Poise|Sinking|Bleed|Burn|Unlock|Prescript|Procuration|Mask|Karmic|Oracle|Fragility|Power|Bind|Paralysis|Rupture|Tremor|Charge", name, re.I):
            likely.append(item)
    return likely[:40]



def parse_passives(raw_html: str) -> list[dict[str, Any]]:
    behavior_index = raw_html.find('id="Behavior"')
    search_html = raw_html[:behavior_index] if behavior_index >= 0 else raw_html
    pattern = re.compile(
        r'<div style="text-shadow:[^>]+#9f693a.*?<div style="margin-right:20px">(.*?)</div>',
        re.S | re.I,
    )
    matches = list(pattern.finditer(search_html))
    passives: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, match in enumerate(matches):
        title = clean_line(html_to_text(match.group(1)))
        if not title or title.lower() in seen:
            continue
        card_start = search_html.rfind('<div style="padding:10px"', 0, match.start())
        if card_start < 0:
            card_start = match.start()
        next_start = len(search_html)
        if index + 1 < len(matches):
            next_start = search_html.rfind('<div style="padding:10px"', 0, matches[index + 1].start())
            if next_start < 0 or next_start <= card_start:
                next_start = matches[index + 1].start()
        fragment = search_html[match.end():next_start]
        lines: list[str] = []
        for raw in html_to_text(fragment).splitlines():
            line = clean_line(raw)
            if not line or line.lower() == title.lower():
                continue
            if line in SECTION_STOP_LINES or line.startswith("Collapse") or line.startswith("Expand"):
                break
            lines.append(line)
        lines = join_wrapped_lines(lines)
        if not lines:
            continue
        seen.add(title.lower())
        passives.append({
            "passive_id": slugify(title, "passive"),
            "name_en": title,
            "description_lines": lines,
            "source": "wiki_passive_card",
        })
    return passives

def parse_rotation_from_existing_notes(raw_html: str, skills: list[dict[str, Any]]) -> dict[str, Any] | None:
    # Generic pages do not expose one stable rotation table shape. Capture behavior text for admin review.
    behavior = re.search(r'id="Behavior".*?(?=<h2|id="Strategy"|id="Rewards"|$)', raw_html, re.S | re.I)
    if not behavior:
        return None
    text = html_to_text(behavior.group(0))
    lines = [clean_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line and line.lower() != "behavior"]
    return {
        "source": "wiki_behavior_section_draft",
        "raw_lines": lines[:120],
        "review_status": "needs_admin_rotation_structuring",
        "open_questions": [
            "Convert raw behavior text into phase rotation rows before simulator use.",
            "Verify whether row order maps to turns, speed slots, or conditional pattern selection.",
        ],
    }


def resolve_input_html(input_path: Path) -> Path:
    if input_path.is_file():
        return input_path
    if input_path.is_dir():
        html_files = sorted(input_path.glob("*.html"))
        if html_files:
            return html_files[0]
    raise FileNotFoundError(f"No saved wiki HTML file found at: {input_path}")


def parse_boss(html_path: Path, boss_id_override: str | None = None, name_override: str | None = None) -> dict[str, Any]:
    html_path = resolve_input_html(html_path)
    raw_html = html_path.read_text(encoding="utf-8", errors="ignore")
    title = name_override or page_title(raw_html)
    asset_dir = asset_dir_for_html(html_path)
    stats = parse_stats(raw_html)
    skills = parse_skills(raw_html, html_path, asset_dir, title)
    statuses = parse_unique_statuses(raw_html, html_path)
    passives = parse_passives(raw_html)
    boss_id = boss_id_override or boss_id_from_title(title)
    body_part = {
        "part_id": "body",
        "name_en": "Body",
        "hp": stats.get("hp"),
        "defense_level": stats.get("defense_level"),
        "stagger_thresholds": stats.get("stagger_thresholds") or [],
    }
    rotation = parse_rotation_from_existing_notes(raw_html, skills)
    payload = {
        "boss_id": boss_id,
        "name_en": title.replace("/Enemy", "").strip(),
        "name_th": None,
        "source": "wiki_html_import_draft",
        "source_html": str(html_path.resolve()),
        "level": stats.get("level"),
        "hp": stats.get("hp"),
        "defense_level": stats.get("defense_level"),
        "body_parts": [body_part],
        "skills": skills,
        "passives": passives,
        "unique_statuses": statuses,
        "assets": {
            "idle_sprite": find_asset(asset_dir, [r"Idle_Sprite\.(?:png|webp)$"]),
            "moving_sprite": find_asset(asset_dir, [r"Moving_Sprite\.(?:png|webp)$"]),
            "idle_animation": find_asset(asset_dir, [r"Idle_Animation\.(?:gif|png|webp)$"]),
        },
        "skill_rotation": rotation,
        "review_status": "wiki_html_import_draft_needs_review",
        "warnings": [
            "Imported from saved wiki HTML with heuristic parsing; admin review is required.",
            "Skill rotation is raw/draft unless manually structured into phase rows.",
            "Stats and resistance mapping need validation before simulator use.",
        ],
    }
    return drop_empty(payload)


def drop_empty(value: Any) -> Any:
    if isinstance(value, dict):
        result = {key: drop_empty(item) for key, item in value.items()}
        return {key: item for key, item in result.items() if item not in (None, [], {}, "")}
    if isinstance(value, list):
        return [drop_empty(item) for item in value if item not in (None, [], {}, "")]
    return value


def write_output(payload: dict[str, Any], out: Path) -> Path:
    if out.suffix.lower() == ".json":
        out_path = out
    else:
        out.mkdir(parents=True, exist_ok=True)
        out_path = out / f"{payload['boss_id']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a draft boss fixture from a saved Limbus wiki HTML page.")
    parser.add_argument("--input", "-i", required=True, type=Path, help="Saved wiki HTML file or folder containing one")
    parser.add_argument("--out", "-o", type=Path, default=DEFAULT_OUT, help="Output JSON file or directory")
    parser.add_argument("--boss-id", help="Override generated boss_id, useful when refreshing an existing fixture")
    parser.add_argument("--name-en", help="Override imported English boss name")
    args = parser.parse_args()
    payload = parse_boss(args.input, boss_id_override=args.boss_id, name_override=args.name_en)
    out_path = write_output(payload, args.out)
    print(json.dumps({
        "boss_id": payload.get("boss_id"),
        "name_en": payload.get("name_en"),
        "skills": len(payload.get("skills", [])),
        "passives": len(payload.get("passives", [])),
        "statuses": len(payload.get("unique_statuses", [])),
        "out": str(out_path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
