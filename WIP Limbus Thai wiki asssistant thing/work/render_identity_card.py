from __future__ import annotations

import re
import textwrap
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFont

from build_identity_profile import build_payload


ROOT = Path(__file__).resolve().parents[1]
CARD_WIDTH = 1800
PAD = 42
BG = (36, 38, 43)
PANEL = (30, 31, 35)
PANEL_2 = (24, 25, 28)
BORDER = (72, 76, 86)
TEXT = (235, 238, 242)
MUTED = (180, 186, 196)
GOLD = (184, 144, 84)
THAI = (246, 218, 181)
BLUE = (39, 206, 254)
GREEN = (147, 240, 63)
RED = (254, 92, 92)
ORANGE = (249, 126, 0)
TOKEN_FALLBACK_COLORS = {
    "trigger": GREEN,
    "icon": (248, 194, 0),
    "missing": THAI,
}


SKILL_TAGS = {
    "WinDuel": ("Clash Win", "#f95e00"),
    "WhenUse": ("On Use", "#27cefe"),
    "EndCoin": ("After Current Coin Attack", "#93f03f"),
    "EndSkill": ("After Attack", "#93f03f"),
    "AllyKill": ("On Ally Kill", "#93f03f"),
    "CantDuel": ("Unclashable", "#fe0000"),
    "EndBattle": ("Turn End", "#93f03f"),
    "BeforeHit": ("Before Getting Hit", "#93f03f"),
    "EnemyKill": ("On Kill", "#93f03f"),
    "DuelGuard": ("Clashable Guard", "#93f03f"),
    "BeforeUse": ("Before Use", "#93f03f"),
    "DefeatDuel": ("Hit after Clash Lose", "#fe0000"),
    "TargetKill": ("On Target Kill", "#93f03f"),
    "DuelCounter": ("Clashable Counter", "#f95e00"),
    "StartBattle": ("Combat Start", "#93f03f"),
    "EndSkillTail": ("Tails Attack End", "#c90080"),
    "EndSkillHead": ("Heads Attack End", "#fe59c0"),
    "BeforeAttack": ("Before Attack", "#93f03f"),
    "CanDuelGuard": ("Clashable Guard", "#9f6a3a"),
    "AllyKillFail": ("On Ally Kill Fail", "#93f03f"),
    "CantIdentify": ("Indiscriminate", "#fe0000"),
    "WinDuelAttack": ("Hit after Clash Win", "#93f03f"),
    "EnemyKillFail": ("Failed Kill", "#93f03f"),
    "OnDefeatEvade": ("Failed Evade", "#fe0000"),
    "OnSucceedEvade": ("On Evade", "#93f03f"),
    "OnSucceedAttack": ("On Hit", "#93f03f"),
    "TurnStartBattle": ("Turn Start", "#93f03f"),
    "CantChangeTarget": ("Target Fixed", "#93f03f"),
    "DefeatDuelAttack": ("Hit after Clash Lose", "#93f03f"),
    "WinDuelAttackHead": ("Heads Hit after Clash Win", "#93f03f"),
    "CriticalActivated": ("On Crit", "#93f03f"),
    "StartBattle_Force": ("Combat Start", "#93f13e"),
    "OnSucceedAttackTail": ("Tails Hit", "#93f03f"),
    "OnSucceedAttackHead": ("Heads Hit", "#c6fe94"),
    "CriticalOnSucceedAttack": ("On Crit", "#93f03f"),
    "CriticalEnemyTargetKill": ("On Crit Kill Against Enemy", "#93f03f"),
    "ReUseOnSucceedAttackHead": ("Reuse - Heads Hit", "#93f03f"),
    "CriticalEnemyTargetKillFail": ("On Crit Kill Fail Against Enemy", "#93f03f"),
    "UnBrokenCoinOnSucceedAttack": ("On Hit without Cracking", "#93f03f"),
}
SKILL_TAGS_BY_LABEL = {label: (label, color) for label, color in SKILL_TAGS.values()}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path(r"C:\Windows\Fonts\LeelawUIB.ttf" if bold else r"C:\Windows\Fonts\LeelawUI.ttf"),
        Path(r"C:\Windows\Fonts\tahomabd.ttf" if bold else r"C:\Windows\Fonts\tahoma.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.RAQM)
            except Exception:
                return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT_TITLE = font(52, True)
FONT_SUB = font(30)
FONT_LABEL = font(30, True)
FONT_TEXT = font(30)
FONT_SMALL = font(25)
FONT_COIN = font(28, True)


def is_cjk(char: str) -> bool:
    code = ord(char)
    return (
        0x3040 <= code <= 0x30FF
        or 0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        or 0xFF00 <= code <= 0xFFEF
    )


@lru_cache(maxsize=128)
def script_font(size: int, bold: bool, script: str) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if script == "cjk":
        candidates = [
            Path(r"C:\Windows\Fonts\meiryob.ttc" if bold else r"C:\Windows\Fonts\meiryo.ttc"),
            Path(r"C:\Windows\Fonts\YuGothB.ttc" if bold else r"C:\Windows\Fonts\YuGothR.ttc"),
            Path(r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc"),
            Path(r"C:\Windows\Fonts\msgothic.ttc"),
        ]
    else:
        candidates = [
            Path(r"C:\Windows\Fonts\LeelawUIB.ttf" if bold else r"C:\Windows\Fonts\LeelawUI.ttf"),
            Path(r"C:\Windows\Fonts\tahomabd.ttf" if bold else r"C:\Windows\Fonts\tahoma.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
        ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.RAQM)
            except Exception:
                return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def text_script(char: str, current: str = "latin") -> str:
    if unicodedata.category(char).startswith("M"):
        return current
    return "cjk" if is_cjk(char) else "latin"


def shaped_runs(value: str) -> list[tuple[str, str]]:
    runs: list[tuple[str, str]] = []
    current_script = "latin"
    buffer: list[str] = []
    for char in str(value):
        script = text_script(char, current_script)
        if buffer and script != current_script:
            runs.append((current_script, "".join(buffer)))
            buffer = []
        buffer.append(char)
        current_script = script
    if buffer:
        runs.append((current_script, "".join(buffer)))
    return runs


def draw_text_mixed(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int, bold: bool, fill: tuple[int, int, int]) -> int:
    x, y = xy
    cursor = x
    for script, run in shaped_runs(str(value)):
        used_font = script_font(size, bold, script)
        draw.text((cursor, y), run, font=used_font, fill=fill)
        cursor += text_size(draw, run, used_font)[0]
    return cursor - x


def mixed_text_width(draw: ImageDraw.ImageDraw, value: str, size: int, bold: bool) -> int:
    width = 0
    for script, run in shaped_runs(str(value)):
        used_font = script_font(size, bold, script)
        width += text_size(draw, run, used_font)[0]
    return width


def clean_text(value: str | None) -> str:
    value = (value or "-").replace('<style="highlight">', "").replace("</style>", "")
    value = re.sub(r"<[^>]+>", "", value)
    for src, (dst, _color) in SKILL_TAGS.items():
        value = value.replace(f"[{src}]", f"[{dst}]")
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def text_size(draw: ImageDraw.ImageDraw, text: str, used_font: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=used_font)
    return box[2] - box[0], box[3] - box[1]


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int], outline: tuple[int, int, int] | None = None, radius: int = 8) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline)


def fit_image(path: str | None, size: int) -> Image.Image | None:
    if not path:
        return None
    source = Path(path)
    if not source.exists():
        return None
    try:
        image = Image.open(source).convert("RGBA")
    except Exception:
        return None
    image.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
    return canvas


def skill_clip_mask(layers: dict[str, Any], size: int) -> Image.Image | None:
    for key in ("background", "rim"):
        layer = layers.get(key) or {}
        image = fit_image(layer.get("absolute_path"), size)
        if image:
            alpha = image.getchannel("A")
            if alpha.getbbox():
                return alpha
    return None


def skill_icon(skill: dict[str, Any], size: int = 124) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    layers = (skill.get("assets") or {}).get("layers") or {}

    background = fit_image((layers.get("background") or {}).get("absolute_path"), size)
    rim = fit_image((layers.get("rim") or {}).get("absolute_path"), size)
    if background:
        canvas.alpha_composite(background, (0, 0))

    art_size = int(size * 0.62)
    art = fit_image((layers.get("art") or {}).get("absolute_path"), art_size)
    if art:
        art_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        art_layer.alpha_composite(art, ((size - art_size) // 2, (size - art_size) // 2))
        mask = skill_clip_mask(layers, size)
        if mask:
            clipped_alpha = ImageChops.multiply(art_layer.getchannel("A"), mask)
            art_layer.putalpha(clipped_alpha)
        canvas.alpha_composite(art_layer, (0, 0))

    if rim:
        canvas.alpha_composite(rim, (0, 0))
    return canvas


def wrap_plain(text: str, width: int = 86, max_lines: int | None = 8) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            lines.append("")
            continue
        wrapped = textwrap.wrap(raw, width=width, break_long_words=False, replace_whitespace=False)
        lines.extend(wrapped or [raw])
    return lines if max_lines is None else lines[:max_lines]


def coin_powers(skill: dict[str, Any]) -> list[int]:
    mechanics = skill.get("combat_mechanics") or {}
    coins = mechanics.get("coins") or []
    powers = [coin.get("power") for coin in coins if coin.get("power") is not None]
    if powers:
        return powers
    return [skill.get("coin_power")] * int(skill.get("coin_count") or 0)


def format_coin_power(power: Any) -> str:
    if power is None:
        return "-"
    if isinstance(power, str):
        value = power.strip()
        if not value:
            return "-"
        if value.startswith(("+", "-")):
            return value
        return f"+{value}" if value.lstrip("-").isdigit() else value
    try:
        return f"{int(power):+}"
    except (TypeError, ValueError):
        return str(power)

def draw_pill(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, fill: tuple[int, int, int] = PANEL_2) -> int:
    w, h = text_size(draw, label, FONT_SMALL)
    box = (x, y, x + w + 34, y + 45)
    rounded(draw, box, fill, BORDER, 8)
    draw.text((x + 17, y + 8), label, font=FONT_SMALL, fill=MUTED)
    return box[2] + 12


def offense_label(skill: dict[str, Any]) -> str:
    level = skill.get("offense_level") or {}
    total = level.get("total")
    if total is None and level.get("correction") is None:
        return "Off -"
    base = level.get("base", "-")
    correction = level.get("correction") or 0
    sign = "+" if isinstance(correction, (int, float)) and correction >= 0 else ""
    return f"Off {total or '-'} ({base}{sign}{correction})"


def draw_coin_line(draw: ImageDraw.ImageDraw, x: int, y: int, skill: dict[str, Any]) -> int:
    if skill.get("deck_count") is not None:
        x = draw_pill(draw, x, y, f"Deck x{skill.get('deck_count')}")
    x = draw_pill(draw, x, y, f"Atk Wt {skill.get('attack_weight')}")
    x = draw_pill(draw, x, y, offense_label(skill))
    base = f"base {skill.get('base_power')}"
    x = draw_pill(draw, x, y, base)
    for power in coin_powers(skill):
        label = format_coin_power(power)
        w, _ = text_size(draw, label, FONT_COIN)
        rounded(draw, (x, y, x + max(52, w + 28), y + 45), (17, 18, 20), BORDER, 7)
        draw.text((x + 14, y + 7), label, font=FONT_COIN, fill=TEXT)
        x += max(52, w + 28) + 9
    return x


def token_icon(token_assets: dict[str, Any], token: str) -> Image.Image | None:
    asset = token_assets.get(token) or {}
    path = asset.get("path")
    return fit_image(path, 34) if path else None


def token_label(token_assets: dict[str, Any], token: str, lang: str) -> str:
    if token in SKILL_TAGS:
        return f"[{SKILL_TAGS[token][0]}]"
    if token in SKILL_TAGS_BY_LABEL:
        return f"[{token}]"
    asset = token_assets.get(token) or {}
    labels = asset.get("label") or {}
    if lang == "th" and labels.get("th"):
        return labels["th"]
    if labels.get("en"):
        return labels["en"]
    return token


def token_color(token_assets: dict[str, Any], token: str) -> tuple[int, int, int]:
    tag = SKILL_TAGS.get(token) or SKILL_TAGS_BY_LABEL.get(token)
    if tag:
        raw = tag[1].lstrip("#")
        return tuple(int(raw[i:i + 2], 16) for i in (0, 2, 4))
    asset = token_assets.get(token) or {}
    if asset.get("color"):
        raw = str(asset["color"]).lstrip("#")
        if len(raw) == 6:
            return tuple(int(raw[i:i + 2], 16) for i in (0, 2, 4))
    return TOKEN_FALLBACK_COLORS.get(asset.get("kind"), THAI)



def coin_effect_icons(payload: dict[str, Any]) -> dict[int, str]:
    folders: list[Path] = []
    for skill in payload.get("skills") or []:
        for layer in ((skill.get("assets") or {}).get("layers") or {}).values():
            path = Path(layer.get("absolute_path") or "")
            if path.exists():
                folders.append(path.parent)
    for image_path in (payload.get("images") or {}).values():
        path = Path(image_path or "")
        if path.exists():
            folders.append(path.parent)

    result: dict[int, str] = {}
    for folder in dict.fromkeys(folders):
        for index in range(1, 12):
            if index in result:
                continue
            matches = sorted(folder.glob(f"*CoinEffect{index}.png"))
            if matches:
                result[index] = str(matches[0].resolve())
    return result

def draw_rich_line(draw: ImageDraw.ImageDraw, image: Image.Image, x: int, y: int, line: str, token_assets: dict[str, Any], color: tuple[int, int, int], lang: str = "th", coin_icons: dict[int, str] | None = None) -> int:
    coin_match = re.fullmatch(r"\[Coin\s+(\d+)\]", line.strip())
    if coin_match:
        coin_index = int(coin_match.group(1))
        icon = fit_image((coin_icons or {}).get(coin_index), 40)
        if icon:
            image.alpha_composite(icon, (x, y + 1))
            return y + 44
        draw.text((x, y), f"Coin {coin_index}", font=FONT_SMALL, fill=GOLD)
        return y + 42

    cursor = x
    parts = re.split(r"(\[[^\]]+\])", line)
    for part in parts:
        if not part:
            continue
        token_match = re.fullmatch(r"\[([^\]]+)\]", part)
        if token_match:
            token = token_match.group(1)
            icon = token_icon(token_assets, token)
            if icon:
                image.alpha_composite(icon, (cursor, y + 2))
                cursor += 38
            label = token_label(token_assets, token, lang)
            used_font = FONT_TEXT
            used_color = token_color(token_assets, token)
            cursor += draw_text_mixed(draw, (cursor, y), label, 30, False, used_color) + 9
            continue
        cursor += draw_text_mixed(draw, (cursor, y), part, 30, False, color)
    return y + 42


def passive_entries(payload: dict[str, Any], lang: str) -> list[dict[str, str]]:
    english = payload.get("passives") or {}
    local = payload.get("localized_passives") or {}
    result: list[dict[str, str]] = []
    for kind, title in [("combat", "Passive"), ("support", "Support Passive")]:
        local_by_id = {str(row.get("source_passive_text_id")): row for row in local.get(kind) or []}
        for row in english.get(kind) or []:
            local_row = local_by_id.get(str(row.get("source_passive_text_id"))) or {}
            en_name = (row.get("name") or {}).get("en") or "-"
            name = local_row.get("name") if lang == "th" and local_row.get("name") else en_name
            desc = local_row.get("description") if lang == "th" and local_row.get("description") else row.get("en")
            result.append({"kind": title, "name": name or "-", "desc": desc or "-"})
    return result


def passive_height(entry: dict[str, str]) -> int:
    return 120 + 42 * len(wrap_plain(clean_text(entry.get("desc")), width=92, max_lines=None))


def skill_display_text(skill: dict[str, Any], lang: str) -> str:
    desc = clean_text(skill.get("localized_description") if lang == "th" else skill.get("english_description"))
    coin_rows = skill.get("localized_coin_texts") if lang == "th" else skill.get("coin_texts")
    coin_lines: list[str] = []
    last_coin: Any = None
    for row in coin_rows or []:
        coin_index = row.get("coin_index")
        text = row.get("text") if lang == "th" else row.get("en")
        text = clean_text(text)
        if not text or text == "-":
            continue
        if coin_index != last_coin:
            coin_lines.append(f"[Coin {coin_index}]")
            last_coin = coin_index
        coin_lines.append(text)
    if coin_lines:
        return desc + "\n" + "\n".join(coin_lines)
    return desc

def render_identity_card(query: str, data_dir: Path | None = None, uptie: int = 4, lang: str = "th", out_dir: Path | None = None) -> Path:
    data_dir = data_dir or ROOT / "data"
    out_dir = out_dir or ROOT / "outputs" / "discord_cards"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = build_payload(query, data_dir, uptie, lang)
    identity = payload.get("identity") or {}
    stats = payload.get("combat_stats") or {}
    res = stats.get("resistances") or {}
    skills = payload.get("skills") or []
    token_assets = payload.get("token_assets") or {}
    coin_icons = coin_effect_icons(payload)
    passives = passive_entries(payload, lang)

    skill_heights = []
    for skill in skills:
        desc = skill_display_text(skill, lang)
        skill_heights.append(180 + 42 * len(wrap_plain(desc, width=92, max_lines=None)))
    passive_heights = [passive_height(entry) for entry in passives]
    height = 320 + sum(skill_heights) + sum(passive_heights) + 100
    card = Image.new("RGBA", (CARD_WIDTH, height), BG + (255,))
    draw = ImageDraw.Draw(card)

    rounded(draw, (24, 24, CARD_WIDTH - 24, height - 24), PANEL, BORDER, 14)
    draw.rectangle((24, 24, 34, height - 24), fill=GOLD)
    title = identity.get("english_name") or query
    local_title = (payload.get("localized_personality") or {}).get("th") if lang == "th" else None
    draw_text_mixed(draw, (PAD + 24, 45), title, 52, True, TEXT)
    subtitle = f"{identity.get('sinner')} | Rarity {identity.get('rarity')} | UT{uptie}"
    if local_title:
        subtitle = f"{local_title} | {subtitle}"
    draw_text_mixed(draw, (PAD + 24, 112), subtitle, 30, False, MUTED)

    thumb = fit_image((payload.get("images") or {}).get("thumbnail"), 160)
    if thumb:
        card.alpha_composite(thumb, (CARD_WIDTH - 218, 45))

    x, y = PAD + 24, 180
    for label in (
        f"HP {stats.get('hp')}",
        f"DEF {stats.get('defense_level')}",
        f"Slash {res.get('slash')}",
        f"Pierce {res.get('pierce')}",
        f"Blunt {res.get('blunt')}",
    ):
        x = draw_pill(draw, x, y, label)

    y = 255
    for index, skill in enumerate(skills):
        block_h = skill_heights[index]
        rounded(draw, (PAD + 15, y, CARD_WIDTH - PAD - 15, y + block_h - 18), (40, 42, 48), (58, 62, 72), 12)
        card.alpha_composite(skill_icon(skill), (PAD + 42, y + 34))

        sx = PAD + 210
        slot = (skill.get("slot") or "").replace("_", " ").title()
        en_name = (skill.get("name") or {}).get("en") or "-"
        th_name = skill.get("localized_name") or en_name
        name = th_name if lang == "th" else en_name
        draw_text_mixed(draw, (sx, y + 30), f"{slot}: {name}", 30, True, TEXT)
        draw.text((sx, y + 78), f"{skill.get('affinity')} {skill.get('damage_type')}", font=FONT_SMALL, fill=MUTED)
        draw_coin_line(draw, sx + 340, y + 68, skill)

        desc = skill_display_text(skill, lang)
        ty = y + 132
        for line in wrap_plain(desc, width=92, max_lines=None):
            ty = draw_rich_line(draw, card, sx, ty, line, token_assets, THAI if lang == "th" else TEXT, lang, coin_icons)
        y += block_h

    for index, passive in enumerate(passives):
        block_h = passive_heights[index]
        rounded(draw, (PAD + 15, y, CARD_WIDTH - PAD - 15, y + block_h - 18), (34, 38, 45), (77, 70, 48), 12)
        sx = PAD + 48
        draw.text((sx, y + 24), passive.get("kind") or "Passive", font=FONT_SMALL, fill=GOLD)
        draw_text_mixed(draw, (sx + 220, y + 20), passive.get("name") or "-", 30, True, TEXT)
        ty = y + 78
        for line in wrap_plain(clean_text(passive.get("desc")), width=104, max_lines=None):
            ty = draw_rich_line(draw, card, sx, ty, line, token_assets, THAI if lang == "th" else TEXT, lang, coin_icons)
        y += block_h

    safe_name = re.sub(r"[^0-9A-Za-z._-]+", "_", title).strip("_") or "identity"
    out_path = out_dir / f"{safe_name}_UT{uptie}_{lang}.png"
    card.convert("RGB").save(out_path, quality=94)
    return out_path


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--uptie", type=int, default=4)
    parser.add_argument("--lang", choices=["en", "th"], default="th")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "discord_cards")
    args = parser.parse_args()
    path = render_identity_card(args.query, args.data, args.uptie, args.lang, args.out_dir)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())















