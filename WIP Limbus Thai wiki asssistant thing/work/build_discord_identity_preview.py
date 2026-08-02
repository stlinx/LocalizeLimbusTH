from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

from build_identity_profile import ROOT, build_payload, file_url, render_skill_icon, rich_text, write_json


def clean_slot(value: str | None) -> str:
    return (value or "").replace("_", " ").title()


def embed_json(payload: dict[str, Any]) -> dict[str, Any]:
    identity = payload.get("identity") or {}
    stats = payload.get("combat_stats") or {}
    res = stats.get("resistances") or {}
    fields: list[dict[str, Any]] = [
        {
            "name": "Stats",
            "value": (
                f"HP {stats.get('hp')} | DEF {stats.get('defense_level')}\n"
                f"Slash {res.get('slash')} / Pierce {res.get('pierce')} / Blunt {res.get('blunt')}"
            ),
            "inline": False,
        }
    ]

    for skill in payload.get("skills") or []:
        name = (skill.get("name") or {}).get("en") or "-"
        local_name = skill.get("localized_name") or name
        power = f"{skill.get('base_power')} {skill.get('coin_power'):+} x{skill.get('coin_count')}"
        fields.append(
            {
                "name": f"{clean_slot(skill.get('slot'))}: {name}",
                "name_th": f"{clean_slot(skill.get('slot'))}: {local_name}",
                "value": f"{skill.get('affinity')} {skill.get('damage_type')} | {power} | Weight {skill.get('attack_weight')}",
                "description_en": skill.get("english_description"),
                "description_th": skill.get("localized_description"),
                "inline": False,
            }
        )

    return {
        "title": identity.get("english_name"),
        "description": f"{identity.get('sinner')} | Rarity {identity.get('rarity')} | UT{payload.get('uptie')}",
        "thumbnail": (payload.get("images") or {}).get("thumbnail"),
        "fields": fields,
        "footer": {
            "text": "Limbus assistant preview payload. Raw simulator scripts stay backend-only.",
        },
    }


def coin_line(skill: dict[str, Any]) -> str:
    mechanics = skill.get("combat_mechanics") or {}
    coins = mechanics.get("coins") or []
    powers = [coin.get("power") for coin in coins if coin.get("power") is not None]
    base = skill.get("base_power")
    if powers:
        coins_html = " ".join(f'<span class="coin">{power:+}</span>' for power in powers)
        return f'<span class="coin-base">base {base}</span> {coins_html}'
    count = skill.get("coin_count") or 0
    coins_html = " ".join(f'<span class="coin">{skill.get("coin_power"):+}</span>' for _ in range(int(count)))
    return f'<span class="coin-base">base {base}</span> {coins_html}'


def strip_tags(value: str | None) -> str:
    return re.sub(r"<[^>]+>", "", value or "")


def render_html(payload: dict[str, Any], embed: dict[str, Any]) -> str:
    identity = payload.get("identity") or {}
    stats = payload.get("combat_stats") or {}
    res = stats.get("resistances") or {}
    token_assets = payload.get("token_assets") or {}
    thumb = file_url((payload.get("images") or {}).get("thumbnail"))

    skill_blocks = []
    for skill in payload.get("skills") or []:
        en_name = html.escape((skill.get("name") or {}).get("en") or "-")
        th_name = html.escape(skill.get("localized_name") or (skill.get("name") or {}).get("en") or "-")
        skill_blocks.append(
            f"""
            <section class="skill">
              {render_skill_icon(skill)}
              <div class="skill-main">
                <div class="skill-title">
                  <strong data-en="{en_name}" data-th="{th_name}">{th_name}</strong>
                  <span>{html.escape(clean_slot(skill.get("slot")))} / {html.escape(str(skill.get("affinity")))} {html.escape(str(skill.get("damage_type")))}</span>
                </div>
                <div class="skill-meta">
                  <span>Weight {skill.get("attack_weight")}</span>
                  <span>Coins {coin_line(skill)}</span>
                </div>
                <div class="skill-text text-en">{rich_text(strip_tags(skill.get("english_description")), token_assets)}</div>
                <div class="skill-text text-th">{rich_text(strip_tags(skill.get("localized_description")), token_assets)}</div>
              </div>
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Discord Preview - {html.escape(identity.get("english_name") or "Identity")}</title>
  <style>
    :root {{ color-scheme: dark; font-family: "Segoe UI", Arial, sans-serif; background:#313338; color:#dbdee1; }}
    body {{ margin:0; min-height:100vh; display:grid; place-items:start center; background:#313338; }}
    main {{ width:min(760px, calc(100vw - 32px)); margin:28px auto; }}
    .channel {{ background:#2b2d31; border-radius:8px; padding:18px; box-shadow:0 20px 70px rgba(0,0,0,.35); }}
    .message {{ display:grid; grid-template-columns:42px 1fr; gap:12px; }}
    .avatar {{ width:42px; height:42px; border-radius:50%; background:#5865f2; display:grid; place-items:center; font-weight:700; }}
    .author {{ color:#f2f3f5; font-weight:600; margin-bottom:6px; }}
    .author span {{ color:#949ba4; font-weight:400; font-size:12px; margin-left:6px; }}
    .embed {{ border-left:4px solid #b89054; background:#24262b; border-radius:4px; padding:14px 14px 12px; max-width:660px; }}
    .embed-top {{ display:grid; grid-template-columns:1fr 86px; gap:14px; align-items:start; }}
    .title {{ font-size:18px; font-weight:700; color:#f2f3f5; margin:0 0 5px; }}
    .subtitle {{ color:#b5bac1; font-size:13px; margin-bottom:10px; }}
    .thumb {{ width:80px; height:80px; object-fit:contain; justify-self:end; background:#1e1f22; border-radius:4px; }}
    .stats {{ display:flex; flex-wrap:wrap; gap:6px; margin:8px 0 12px; align-items:center; }}
    .stats span, .skill-meta > span {{
      display:inline-flex; align-items:center; min-height:24px; box-sizing:border-box;
      background:#1e1f22; border:1px solid #383a40; border-radius:4px;
      padding:3px 7px; color:#b5bac1; font-size:12px; line-height:16px;
    }}
    .buttons {{ display:flex; gap:8px; margin:10px 0 14px; }}
    button {{ border:1px solid #4e5058; background:#383a40; color:#f2f3f5; border-radius:4px; padding:6px 12px; cursor:pointer; }}
    button.active {{ background:#5865f2; border-color:#5865f2; }}
    .skill {{ display:grid; grid-template-columns:58px 1fr; gap:10px; padding-top:12px; margin-top:12px; border-top:1px solid #34363c; }}
    .skill-title strong {{ display:block; color:#f2f3f5; }}
    .skill-title span {{ color:#949ba4; font-size:12px; }}
    .skill-meta {{ display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin:7px 0; }}
    .skill-text {{ color:#dbdee1; line-height:1.4; font-size:13px; }}
    .text-th {{ display:none; color:#f1dcc0; }}
    .lang-th .text-en {{ display:none; }}
    .lang-th .text-th {{ display:block; }}
    .skill-icon {{ position:relative; width:58px; height:58px; overflow:hidden; }}
    .skill-icon img {{ position:absolute; width:58px; height:58px; object-fit:contain; }}
    .skill-icon .bg {{ z-index:1; }}
    .skill-icon .art {{
      z-index:2; width:38px; height:38px; left:10px; top:10px; border-radius:3px;
      clip-path:polygon(18% 0, 82% 0, 100% 18%, 100% 82%, 82% 100%, 18% 100%, 0 82%, 0 18%);
    }}
    .skill-icon .rim {{ z-index:3; }}
    .token {{ display:inline-flex; align-items:center; gap:3px; color:#f1dcc0; white-space:nowrap; }}
    .token img {{ width:16px; height:16px; object-fit:contain; }}
    .trigger {{ font-weight:600; }}
    .missing {{ color:#ff9f9f; }}
    .coin {{
      display:inline-flex; align-items:center; justify-content:center; min-width:22px; height:18px;
      box-sizing:border-box; text-align:center; padding:0 4px; margin-left:2px;
      background:#111214; border:1px solid #44474f; border-radius:3px; color:#f2f3f5; line-height:16px;
    }}
    .foot {{ color:#949ba4; font-size:11px; margin-top:12px; }}
  </style>
</head>
<body>
  <main>
    <div class="channel">
      <div class="message">
        <div class="avatar">LC</div>
        <div>
          <div class="author">Limbus Assistant <span>BOT preview</span></div>
          <div id="embed" class="embed lang-th">
            <div class="embed-top">
              <div>
                <h1 class="title">{html.escape(embed.get("title") or "-")}</h1>
                <div class="subtitle">{html.escape(embed.get("description") or "")}</div>
                <div class="stats">
                  <span>HP {html.escape(str(stats.get("hp")))}</span>
                  <span>DEF {html.escape(str(stats.get("defense_level")))}</span>
                  <span>Slash {res.get("slash")}</span>
                  <span>Pierce {res.get("pierce")}</span>
                  <span>Blunt {res.get("blunt")}</span>
                </div>
              </div>
              {f'<img class="thumb" src="{thumb}" alt="">' if thumb else '<div></div>'}
            </div>
            <div class="buttons">
              <button id="enBtn" type="button">EN</button>
              <button id="thBtn" class="active" type="button">TH</button>
            </div>
            {''.join(skill_blocks)}
            <div class="foot">Discord-style preview. Raw simulator data stays hidden in backend JSON.</div>
          </div>
        </div>
      </div>
    </div>
  </main>
  <script>
    const embed = document.getElementById("embed");
    const enBtn = document.getElementById("enBtn");
    const thBtn = document.getElementById("thBtn");
    function setLang(lang) {{
      embed.classList.toggle("lang-th", lang === "th");
      enBtn.classList.toggle("active", lang === "en");
      thBtn.classList.toggle("active", lang === "th");
      document.querySelectorAll(".skill-title strong").forEach((node) => {{
        node.textContent = node.dataset[lang] || node.dataset.en;
      }});
    }}
    enBtn.addEventListener("click", () => setLang("en"));
    thBtn.addEventListener("click", () => setLang("th"));
  </script>
</body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Discord-style Identity response preview.")
    parser.add_argument("query")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--uptie", type=int, default=4)
    parser.add_argument("--lang", choices=["en", "th", "both"], default="both")
    parser.add_argument("--json-out", type=Path, default=ROOT / "outputs" / "discord_identity_embed.json")
    parser.add_argument("--html-out", type=Path, default=ROOT / "outputs" / "discord_identity_embed_preview.html")
    args = parser.parse_args()

    payload = build_payload(args.query, args.data.resolve(), args.uptie, args.lang)
    embed = embed_json(payload)
    write_json(args.json_out, {"profile": payload, "discord_embed": embed})
    args.html_out.parent.mkdir(parents=True, exist_ok=True)
    args.html_out.write_text(render_html(payload, embed), encoding="utf-8")

    print("Discord identity preview built")
    print(f"  Identity: {embed.get('title')}")
    print(f"  JSON: {args.json_out}")
    print(f"  HTML: {args.html_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



