from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCALIZATION_FULL_DIR = ROOT / "work" / "sample_data" / "localization_full"
_LOCALIZATION_CACHE: dict[str, Any] | None = None
NORMALIZE_ALIASES = {
    "yisang": "yi sang",
    "donquixote": "don quixote",
    "honglu": "hong lu",
    "ryoshu": "ryoshu",
    "ryoushu": "ryoshu",
    "rodion": "rodion",
    "rodya": "rodion",
}
TRIGGER_COLORS = {
    "WhenUse": "#27cefe",
    "BeforeUse": "#93f03f",
    "BeforeAttack": "#93f03f",
    "StartBattle": "#93f03f",
    "TurnStartBattle": "#93f03f",
    "EndSkill": "#93f03f",
    "EndBattle": "#93f03f",
    "WinDuel": "#f95e00",
    "DefeatDuel": "#fe0000",
    "OnSucceedAttack": "#93f03f",
    "OnSucceedAttackHead": "#c6fe94",
    "OnSucceedAttackTail": "#93f03f",
    "CriticalOnSucceedAttack": "#93f03f",
    "CriticalActivated": "#93f03f",
    "CantDuel": "#fe0000",
    "DuelCounter": "#f95e00",
    "OnSucceedEvade": "#93f03f",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def data_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = load_json(path)
    rows = data.get("dataList") if isinstance(data, dict) else data
    return [row for row in rows or [] if isinstance(row, dict)]


def localization_tables() -> dict[str, Any]:
    global _LOCALIZATION_CACHE
    if _LOCALIZATION_CACHE is not None:
        return _LOCALIZATION_CACHE

    token_labels: dict[str, dict[str, str]] = {}
    for local_file, en_file in [("Bufs.json", "EN_Bufs.json"), ("BattleKeywords.json", "EN_BattleKeywords.json")]:
        local_rows = {str(row.get("id")): row for row in data_list(LOCALIZATION_FULL_DIR / local_file)}
        en_rows = {str(row.get("id")): row for row in data_list(LOCALIZATION_FULL_DIR / en_file)}
        for token, row in local_rows.items():
            label = str(row.get("name") or "").strip()
            if not label:
                continue
            token_labels.setdefault(token, {})["th"] = label
            en_label = str((en_rows.get(token) or {}).get("name") or "").strip()
            if en_label:
                token_labels.setdefault(token, {})["en"] = en_label

    personality_names: dict[str, dict[str, str]] = {}
    local_people = {str(row.get("id")): row for row in data_list(LOCALIZATION_FULL_DIR / "Personalities.json")}
    en_people = {str(row.get("id")): row for row in data_list(LOCALIZATION_FULL_DIR / "EN_Personalities.json")}
    for identity_id, row in local_people.items():
        names = [row.get("nameWithTitle"), row.get("title"), row.get("name")]
        local_name = " ".join(str(row.get("nameWithTitle") or "").replace("\\n", " ").split()).strip()
        en_row = en_people.get(identity_id) or {}
        en_name = " ".join(str(en_row.get("nameWithTitle") or "").replace("\n", " ").split()).strip()
        personality_names[identity_id] = {
            "th": local_name,
            "en": en_name,
            "search": " ".join(str(item or "").replace("\n", " ") for item in names if item),
        }

    _LOCALIZATION_CACHE = {"token_labels": token_labels, "personality_names": personality_names}
    return _LOCALIZATION_CACHE


def norm(value: str | None) -> str:
    value = value or ""
    value = re.sub(r"\.(json|png|jpg|jpeg|webp|gif|html)$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^\d+px-", "", value)
    for src, dst in NORMALIZE_ALIASES.items():
        value = re.sub(src, dst, value, flags=re.IGNORECASE)
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"[^\w\u0E00-\u0E7F]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip().lower()


def file_url(path: str | None) -> str | None:
    if not path:
        return None
    return Path(path).resolve().as_uri()


def resolve_data_path(data_dir: Path, value: str | None) -> Path | None:
    if not value:
        return None
    raw = Path(value)
    if raw.parts and raw.parts[0] == "data":
        return data_dir.joinpath(*raw.parts[1:])
    return data_dir / raw


def score_item(query: str, item: dict[str, Any]) -> int:
    if not item.get("identity_id") or not item.get("skill_names"):
        return 0
    q = norm(query)
    if not q:
        return 0

    name = norm(item.get("english_name"))
    sinner = norm(item.get("sinner"))
    identity_id = norm(str(item.get("identity_id") or ""))
    skills = norm(" ".join(item.get("skill_names") or []))
    extra_values = [str(value or "") for value in item.get("_search_extra") or []]
    extra_exact = {norm(value) for value in extra_values if norm(value)}
    extra = norm(" ".join(extra_values))
    query_tokens = q.split()
    name_tokens = set(name.split())

    if q == name:
        return 5000
    if q == identity_id:
        return 4800
    if q == sinner or q in extra_exact:
        if name == f"lcb sinner {sinner}":
            return 4700
        return 100
    if q in name:
        return 4200 + len(q)
    if extra and q in extra:
        return 3600 + len(q)

    score = 0
    name_hits = sum(1 for token in query_tokens if token in name_tokens)
    if name_hits == len(query_tokens):
        score += 3000 + (name_hits * 100)
    else:
        score += name_hits * 500

    if sinner and sinner in query_tokens:
        score += 180
    if identity_id and identity_id in query_tokens:
        score += 300
    score += sum(30 for token in query_tokens if token in skills)
    return score

def find_identity(query: str, data_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    index = load_json(data_dir / "indexes" / "identity_search_index.json")
    people = localization_tables().get("personality_names") or {}
    locale_dir = data_dir / "identities" / "locales" / "th"
    searchable_items = []
    for item in index.get("items") or []:
        row = dict(item)
        extra = []
        person = people.get(str(row.get("identity_id") or "")) or {}
        extra.extend([person.get("th"), person.get("en"), person.get("search")])
        locale_path = resolve_data_path(data_dir, row.get("locale_file")) or (locale_dir / Path(row.get("file", "")).name)
        if locale_path.exists():
            try:
                locale = load_json(locale_path)
                extra.extend(skill.get("name") for skill in locale.get("skills") or [])
                extra.extend(passive.get("name") for rows in (locale.get("passives") or {}).values() for passive in rows or [])
            except Exception:
                pass
        row["_search_extra"] = [value for value in extra if value]
        searchable_items.append(row)
    matches = [(score_item(query, item), item) for item in searchable_items]
    matches = [(score, item) for score, item in matches if score > 0]
    matches.sort(key=lambda row: row[0], reverse=True)
    if not matches:
        raise ValueError(f"No identity found for: {query}")

    item = matches[0][1]
    en_path = resolve_data_path(data_dir, item.get("file"))
    th_path = resolve_data_path(data_dir, item.get("locale_file"))
    combat_path = data_dir / "combat" / "identities" / Path(item.get("file", "")).name
    en = load_json(en_path) if en_path and en_path.exists() else {}
    th = load_json(th_path) if th_path and th_path.exists() else None
    combat = load_json(combat_path) if combat_path.exists() else None
    return item, en, th, combat


def get_wiki_asset_entry(asset_manifest: dict[str, Any], identity_id: str | None, english_name: str | None) -> dict[str, Any] | None:
    by_id = ((asset_manifest.get("wiki_identity_layers") or {}).get("by_identity_id") or {})
    if identity_id and identity_id in by_id:
        return by_id[identity_id]
    wanted = norm(english_name)
    for entry in by_id.values():
        if norm(entry.get("english_name")) == wanted:
            return entry
    return None


def scan_wiki_folder(entry: dict[str, Any] | None) -> list[Path]:
    if not entry or not entry.get("folder"):
        return []
    folder = Path(entry["folder"])
    if not folder.exists():
        return []
    return [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}]


def find_image(files: list[Path], english_name: str, *terms: str, reject: tuple[str, ...] = (), require_identity: bool = False) -> str | None:
    wanted = [norm(term) for term in terms if norm(term)]
    rejected = [norm(term) for term in reject if norm(term)]
    identity_key = norm(english_name)
    scored: list[tuple[int, Path]] = []
    for path in files:
        key = norm(path.name)
        if wanted and not all(term in key for term in wanted):
            continue
        if require_identity and identity_key and identity_key not in key:
            continue
        if rejected and any(term in key for term in rejected):
            continue
        score = 0
        if identity_key and identity_key in key:
            score += 50
        if "profile" in key:
            score += 30
        if "idle sprite" in key:
            score += 20
        if "moving sprite" in key:
            score += 10
        scored.append((score, path))
    if not scored:
        return None
    scored.sort(key=lambda row: row[0], reverse=True)
    return str(scored[0][1].resolve())


def identity_images(english_name: str, files: list[Path]) -> dict[str, Any]:
    profile = find_image(files, english_name, "profile", require_identity=True)
    idle = find_image(files, english_name, "idle", "sprite")
    moving = find_image(files, english_name, "moving", "sprite")
    acquisition = find_image(files, english_name, "acquisition")
    return {
        "profile": profile,
        "idle_sprite": idle,
        "moving_sprite": moving,
        "acquisition": acquisition,
        "thumbnail": profile or idle or moving or acquisition,
    }


def token_matches(asset_manifest: dict[str, Any], texts: list[str]) -> dict[str, Any]:
    token_re = re.compile(r"\[([A-Za-z0-9_]+)\]")
    matched = ((asset_manifest.get("database_token_asset_matches") or {}).get("matched") or {})
    labels = localization_tables().get("token_labels") or {}
    result: dict[str, Any] = {}
    for text in texts:
        for token in token_re.findall(text or ""):
            if token in TRIGGER_COLORS:
                result[token] = {"kind": "trigger", "color": TRIGGER_COLORS[token], "label": labels.get(token, {})}
            elif token in matched:
                result[token] = {"kind": "icon", "path": matched[token], "label": labels.get(token, {})}
            else:
                result.setdefault(token, {"kind": "missing", "label": labels.get(token, {})})
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


def build_payload(query: str, data_dir: Path, uptie: int, lang: str) -> dict[str, Any]:
    item, en, th, combat = find_identity(query, data_dir)
    manifest = load_json(data_dir / "assets" / "asset_manifest.json")
    identity = en.get("identity") or {}
    identity_id = identity.get("id")
    english_name = identity.get("english_name")
    wiki_entry = get_wiki_asset_entry(manifest, identity_id, english_name)
    people = localization_tables().get("personality_names") or {}
    localized_personality = people.get(str(identity_id or "")) or {}
    files = scan_wiki_folder(wiki_entry)
    th_skills = localized_skill_map(th)
    combat_skills = combat_skill_map(combat)
    wiki_skills = (wiki_entry or {}).get("skills") or {}

    skills: list[dict[str, Any]] = []
    all_texts: list[str] = []
    localized_passives = (th or {}).get("passives") or {}
    for rows in (en.get("passives") or {}).values():
        for passive in rows or []:
            all_texts.append(passive.get("en") or "")
    for rows in localized_passives.values():
        for passive in rows or []:
            all_texts.append(passive.get("description") or "")
    for skill in en.get("skills") or []:
        if skill.get("uptie") != uptie:
            continue
        key = (skill.get("source_skill_text_id"), skill.get("slot"), skill.get("uptie"))
        local = th_skills.get(key)
        mechanics = combat_skills.get(key)
        assets = wiki_skills.get(str(skill.get("source_skill_text_id"))) or {}
        texts = [skill.get("english_description") or ""]
        texts.extend((coin.get("en") or "") for coin in skill.get("coin_texts") or [])
        if local:
            texts.append(local.get("description") or "")
            texts.extend((coin.get("text") or "") for coin in local.get("coin_texts") or [])
        all_texts.extend(texts)
        skills.append(
            {
                "slot": skill.get("slot"),
                "uptie": skill.get("uptie"),
                "source_skill_text_id": skill.get("source_skill_text_id"),
                "name": skill.get("name"),
                "localized_name": local.get("name") if local else None,
                "affinity": skill.get("affinity"),
                "damage_type": skill.get("damage_type"),
                "base_power": skill.get("base_power"),
                "coin_power": skill.get("coin_power"),
                "coin_count": skill.get("coin_count"),
                "deck_count": skill.get("deck_count"),
                "attack_weight": skill.get("attack_weight"),
                "offense_level": skill.get("offense_level"),
                "english_description": skill.get("english_description"),
                "localized_description": local.get("description") if local else None,
                "coin_texts": skill.get("coin_texts") or [],
                "localized_coin_texts": local.get("coin_texts") if local else [],
                "combat_mechanics": mechanics,
                "assets": assets,
            }
        )

    payload = {
        "schema_version": 1,
        "kind": "limbus_identity_profile",
        "query": query,
        "lang": lang,
        "uptie": uptie,
        "identity": identity,
        "localized_identity": th,
        "localized_personality": localized_personality,
        "combat_stats": en.get("combat_stats") or {},
        "images": identity_images(english_name or "", files),
        "skills": skills,
        "passives": en.get("passives") or {},
        "localized_passives": localized_passives,
        "combat_available": combat is not None,
        "token_assets": token_matches(manifest, all_texts),
        "match": item,
    }
    return payload


def rich_text(value: str | None, token_assets: dict[str, Any]) -> str:
    value = html.escape((value or "-").replace('<style="highlight">', "").replace("</style>", ""))

    def replace_token(match: re.Match[str]) -> str:
        token = match.group(1)
        asset = token_assets.get(token) or {}
        if asset.get("kind") == "trigger":
            return f'<span class="trigger" style="color:{asset["color"]}">[{html.escape(token)}]</span>'
        if asset.get("kind") == "icon" and asset.get("path"):
            return f'<span class="token"><img src="{file_url(asset["path"])}" alt="">[{html.escape(token)}]</span>'
        return f'<span class="missing">[{html.escape(token)}]</span>'

    return re.sub(r"\[([A-Za-z0-9_]+)\]", replace_token, value).replace("\n", "<br>")


def render_skill_icon(skill: dict[str, Any]) -> str:
    layers = ((skill.get("assets") or {}).get("layers") or {})
    bg = file_url((layers.get("background") or {}).get("absolute_path"))
    art = file_url((layers.get("art") or {}).get("absolute_path"))
    rim = file_url((layers.get("rim") or {}).get("absolute_path"))
    return f"""
      <div class="skill-icon">
        {f'<img class="bg" src="{bg}" alt="">' if bg else ''}
        {f'<img class="art" src="{art}" alt="">' if art else ''}
        {f'<img class="rim" src="{rim}" alt="">' if rim else ''}
      </div>
    """


def render_html(payload: dict[str, Any]) -> str:
    identity = payload["identity"]
    stats = payload.get("combat_stats") or {}
    res = stats.get("resistances") or {}
    thumb = file_url((payload.get("images") or {}).get("thumbnail"))
    token_assets = payload.get("token_assets") or {}
    skill_cards = []
    for skill in payload.get("skills") or []:
        mechanics = skill.get("combat_mechanics") or {}
        coins = mechanics.get("coins") or []
        coin_line = " ".join(f'<span class="coin">{coin.get("power"):+}</span>' for coin in coins if coin.get("power") is not None)
        scripts = [script.get("script_name") for script in mechanics.get("scripts") or [] if script.get("script_name")]
        for coin in coins:
            scripts.extend(script.get("script_name") for script in coin.get("scripts") or [] if script.get("script_name"))
        script_line = ", ".join(sorted(set(scripts))) or "no script data"
        skill_cards.append(
            f"""
            <article class="skill-card">
              <div class="skill-head">
                {render_skill_icon(skill)}
                <div>
                  <h2>{html.escape((skill.get("name") or {}).get("en") or "-")}</h2>
                  <p>{html.escape(skill.get("localized_name") or "")}</p>
                </div>
              </div>
              <div class="chips">
                <span>{html.escape(str(skill.get("slot")))}</span>
                <span>{html.escape(str(skill.get("affinity")))}</span>
                <span>{html.escape(str(skill.get("damage_type")))}</span>
                <span>{skill.get("base_power")} {skill.get("coin_power"):+} x{skill.get("coin_count")}</span>
                <span>deck x{skill.get("deck_count")}</span>
                <span>atk weight {skill.get("attack_weight")}</span>
              </div>
              <div class="text-block"><b>EN</b><br>{rich_text(skill.get("english_description"), token_assets)}</div>
              <div class="text-block local"><b>Local</b><br>{rich_text(skill.get("localized_description"), token_assets)}</div>
              <div class="mechanics"><b>Mechanics</b><br>Coins: {coin_line or "-"}<br>Scripts: {html.escape(script_line)}</div>
            </article>
            """
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(identity.get("english_name") or "Identity Profile")}</title>
  <style>
    :root {{ color-scheme: dark; font-family: Arial, sans-serif; background:#111; color:#eee; }}
    body {{ margin:0; background:#121212; }}
    main {{ max-width:1180px; margin:0 auto; padding:24px; }}
    header {{ display:grid; grid-template-columns:96px 1fr; gap:18px; align-items:center; border-bottom:1px solid #333; padding-bottom:18px; }}
    .portrait {{ width:80px; height:80px; object-fit:contain; background:#1d1d1d; border:1px solid #333; }}
    h1 {{ margin:0 0 6px; font-size:28px; }}
    .meta, .chips {{ display:flex; flex-wrap:wrap; gap:8px; color:#bbb; }}
    .meta span, .chips span {{ border:1px solid #333; background:#1b1b1b; padding:4px 8px; border-radius:4px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:14px; margin-top:18px; }}
    .skill-card {{ background:#181818; border:1px solid #333; border-radius:8px; padding:14px; }}
    .skill-head {{ display:grid; grid-template-columns:64px 1fr; gap:12px; align-items:center; }}
    .skill-head h2 {{ margin:0; font-size:18px; }}
    .skill-head p {{ margin:4px 0 0; color:#bbb; }}
    .skill-icon {{ position:relative; width:58px; height:58px; }}
    .skill-icon img {{ position:absolute; width:58px; height:58px; object-fit:contain; }}
    .skill-icon .bg {{ z-index:1; }}
    .skill-icon .art {{ z-index:2; width:42px; height:42px; left:8px; top:8px; border-radius:4px; }}
    .skill-icon .rim {{ z-index:3; }}
    .text-block, .mechanics {{ margin-top:12px; line-height:1.45; color:#ddd; }}
    .local {{ color:#f2e0b8; }}
    .token {{ display:inline-flex; gap:3px; align-items:center; white-space:nowrap; color:#f2e0b8; }}
    .token img {{ width:18px; height:18px; object-fit:contain; }}
    .missing {{ color:#ff9f9f; }}
    .coin {{ display:inline-block; min-width:28px; text-align:center; border:1px solid #444; padding:2px 5px; margin-right:4px; }}
  </style>
</head>
<body>
<main>
  <header>
    {f'<img class="portrait" src="{thumb}" alt="">' if thumb else '<div class="portrait"></div>'}
    <div>
      <h1>{html.escape(identity.get("english_name") or "-")}</h1>
      <div class="meta">
        <span>{html.escape(identity.get("sinner") or "-")}</span>
        <span>000 rarity {html.escape(str(identity.get("rarity")))} </span>
        <span>HP {html.escape(str(stats.get("hp")))}</span>
        <span>DEF {html.escape(str(stats.get("defense_level")))}</span>
        <span>Slash {res.get("slash")} / Pierce {res.get("pierce")} / Blunt {res.get("blunt")}</span>
        <span>UT{payload.get("uptie")}</span>
      </div>
    </div>
  </header>
  <section class="grid">
    {''.join(skill_cards)}
  </section>
</main>
</body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a bot-ready Identity profile payload and HTML preview.")
    parser.add_argument("query", help="Identity name or search query.")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--uptie", type=int, default=4)
    parser.add_argument("--lang", choices=["en", "th", "both"], default="both")
    parser.add_argument("--json-out", type=Path, default=ROOT / "outputs" / "identity_profile_payload.json")
    parser.add_argument("--html-out", type=Path, default=ROOT / "outputs" / "identity_profile_preview.html")
    args = parser.parse_args()

    payload = build_payload(args.query, args.data.resolve(), args.uptie, args.lang)
    write_json(args.json_out, payload)
    args.html_out.parent.mkdir(parents=True, exist_ok=True)
    args.html_out.write_text(render_html(payload), encoding="utf-8")

    identity = payload.get("identity") or {}
    print("Identity profile built")
    print(f"  Identity: {identity.get('english_name')} [{identity.get('id')}]")
    print(f"  Skills: {len(payload.get('skills') or [])}")
    print(f"  Thumbnail: {(payload.get('images') or {}).get('thumbnail')}")
    print(f"  JSON: {args.json_out}")
    print(f"  HTML: {args.html_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

















