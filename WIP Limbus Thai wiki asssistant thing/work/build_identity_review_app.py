from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "work" / "sample_data" / "localization_full"
def find_keyword_asset_dir() -> Path | None:
    base = Path.home() / "Downloads" / "LC.Localization.Interface.1.4.2"
    if not base.exists():
        return None
    for candidate in base.rglob("Keywords"):
        if candidate.is_dir() and candidate.parent.name == "Limbus Images":
            return candidate
    return None


KEYWORD_ASSET_DIR = find_keyword_asset_dir()


TRIGGER_KEYWORDS = {
    "WinDuel": {"en": "[Clash Win]", "color": "#f95e00"},
    "WhenUse": {"en": "[On Use]", "color": "#27cefe"},
    "EndCoin": {"en": "[After Current Coin Attack]", "color": "#93f03f"},
    "EndSkill": {"en": "[After Attack]", "color": "#93f03f"},
    "AllyKill": {"en": "[On Ally Kill]", "color": "#93f03f"},
    "CantDuel": {"en": "[Unclashable]", "color": "#fe0000"},
    "EndBattle": {"en": "[Turn End]", "color": "#93f03f"},
    "BeforeHit": {"en": "[Before Getting Hit]", "color": "#93f03f"},
    "EnemyKill": {"en": "[On Kill]", "color": "#93f03f"},
    "DuelGuard": {"en": "[Clashable Guard]", "color": "#93f03f"},
    "BeforeUse": {"en": "[Before Use]", "color": "#93f03f"},
    "DefeatDuel": {"en": "[Hit after Clash Lose]", "color": "#fe0000"},
    "TargetKill": {"en": "[On Target Kill]", "color": "#93f03f"},
    "DuelCounter": {"en": "[Clashable Counter]", "color": "#f95e00"},
    "StartBattle": {"en": "[Combat Start]", "color": "#93f03f"},
    "EndSkillTail": {"en": "[Tails Attack End]", "color": "#c90080"},
    "EndSkillHead": {"en": "[Heads Attack End]", "color": "#fe59c0"},
    "BeforeAttack": {"en": "[Before Attack]", "color": "#93f03f"},
    "CanDuelGuard": {"en": "[Clashable Guard]", "color": "#9f6a3a"},
    "AllyKillFail": {"en": "[On Ally Kill Fail]", "color": "#93f03f"},
    "CantIdentify": {"en": "[Indiscriminate]", "color": "#fe0000"},
    "WinDuelAttack": {"en": "[Hit after Clash Win]", "color": "#93f03f"},
    "EnemyKillFail": {"en": "[Failed Kill]", "color": "#93f03f"},
    "OnDefeatEvade": {"en": "[Failed Evade]", "color": "#fe0000"},
    "OnSucceedEvade": {"en": "[On Evade]", "color": "#93f03f"},
    "OnSucceedAttack": {"en": "[On Hit]", "color": "#93f03f"},
    "TurnStartBattle": {"en": "[Turn Start]", "color": "#93f03f"},
    "CantChangeTarget": {"en": "[Target Fixed]", "color": "#93f03f"},
    "DefeatDuelAttack": {"en": "[Hit after Clash Lose]", "color": "#93f03f"},
    "WinDuelAttackHead": {"en": "[Heads Hit after Clash Win]", "color": "#93f03f"},
    "CriticalActivated": {"en": "[On Crit]", "color": "#93f03f"},
    "StartBattle_Force": {"en": "[Combat Start]", "color": "#93f13e"},
    "OnSucceedAttackTail": {"en": "[Tails Hit]", "color": "#93f03f"},
    "OnSucceedAttackHead": {"en": "[Heads Hit]", "color": "#c6fe94"},
    "CriticalOnSucceedAttack": {"en": "[On Crit]", "color": "#93f03f"},
    "CriticalEnemyTargetKill": {"en": "[On Crit Kill Against Enemy]", "color": "#93f03f"},
    "ReUseOnSucceedAttackHead": {"en": "[Reuse - Heads Hit]", "color": "#93f03f"},
    "CriticalEnemyTargetKillFail": {"en": "[On Crit Kill Fail Against Enemy]", "color": "#93f03f"},
    "UnBrokenCoinOnSucceedAttack": {"en": "[On Hit without Cracking]", "color": "#93f03f"},
}


def norm(value: str | None) -> str:
    if not value:
        return ""
    value = Path(value).stem
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"[^0-9A-Za-z]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def load_rows(filename: str) -> dict[str, dict]:
    path = DATA_DIR / filename
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8-sig")).get("dataList", [])
    return {str(row.get("id")): row for row in rows if row.get("id")}


def pair(en_row: dict | None, local_row: dict | None, key: str) -> dict[str, str | None]:
    en = (en_row or {}).get(key)
    local = (local_row or {}).get(key) or en
    return {"en": en, "local": local}


def build_common_lookup() -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for kind, en_file, local_file in [
        ("status", "EN_Bufs.json", "Bufs.json"),
        ("keyword", "EN_BattleKeywords.json", "BattleKeywords.json"),
    ]:
        en_rows = load_rows(en_file)
        local_rows = load_rows(local_file)
        for row_id, en_row in en_rows.items():
            local_row = local_rows.get(row_id)
            name = pair(en_row, local_row, "name")
            if not name["en"]:
                continue
            lookup.setdefault(
                norm(name["en"]),
                {
                    "kind": kind,
                    "id": row_id,
                    "name": name,
                    "desc": pair(en_row, local_row, "desc"),
                    "summary": pair(en_row, local_row, "summary"),
                },
            )
    return lookup



def build_token_lookup() -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for kind, en_file, local_file in [
        ("status", "EN_Bufs.json", "Bufs.json"),
        ("keyword", "EN_BattleKeywords.json", "BattleKeywords.json"),
    ]:
        en_rows = load_rows(en_file)
        local_rows = load_rows(local_file)
        for row_id, en_row in en_rows.items():
            local_row = local_rows.get(row_id)
            lookup[str(row_id)] = {
                "kind": kind,
                "id": str(row_id),
                "name": pair(en_row, local_row, "name"),
                "desc": pair(en_row, local_row, "desc"),
                "summary": pair(en_row, local_row, "summary"),
            }
    return lookup
def build_template_lookup() -> dict[str, dict]:
    en_rows = load_rows("EN_BuffAbilities.json")
    local_rows = load_rows("BuffAbilities.json")
    interesting = {
        "GiveBuffOnSucceedAttack",
        "AtkDamageMultiplier",
        "SlotWeightAdder",
        "AtkAdder",
        "DefAdder",
        "ResultAdder",
        "CoinPowerAdder",
        "PlusCoinPowerAdder",
        "MinusCoinPowerAdder",
    }
    templates = {}
    for row_id in interesting:
        en_row = en_rows.get(row_id)
        if not en_row:
            continue
        local_row = local_rows.get(row_id)
        templates[row_id] = {
            "id": row_id,
            "desc": pair(en_row, local_row, "desc"),
            "variation": pair(en_row, local_row, "variation"),
        }
    return templates


def source_asset_folder(source_path: str | None) -> Path | None:
    if not source_path:
        return None
    html_path = Path(source_path)
    folder = html_path.with_name(f"{html_path.stem}_files")
    return folder if folder.exists() else None


def extract_common_terms(text: str | None, lookup: dict[str, dict]) -> list[dict]:
    seen = set()
    terms = []
    for token in re.findall(r"\[img:([^\]]+)\]", text or ""):
        term = lookup.get(norm(token))
        if not term or term["id"] in seen:
            continue
        seen.add(term["id"])
        terms.append({"token": token, **term})
    return terms


def infer_template_hints(text: str | None, templates: dict[str, dict]) -> list[dict]:
    hints = []
    source = text or ""
    if re.search(r"\[On Hit\].*\b(Inflict|Gain)\b", source) and "GiveBuffOnSucceedAttack" in templates:
        hints.append(templates["GiveBuffOnSucceedAttack"])
    if "Atk Weight" in source and "SlotWeightAdder" in templates:
        hints.append(templates["SlotWeightAdder"])
    if "Final Power" in source and "ResultAdder" in templates:
        hints.append(templates["ResultAdder"])
    if "Coin Power" in source and "CoinPowerAdder" in templates:
        hints.append(templates["CoinPowerAdder"])
    return hints


def enrich_data(data: dict) -> dict:
    common_lookup = build_common_lookup()
    template_lookup = build_template_lookup()
    token_lookup = build_token_lookup()
    for item in data.get("identities", []):
        wiki = item.get("wiki_identity") or {}
        asset_folder = source_asset_folder((wiki.get("source") or {}).get("path"))
        if asset_folder:
            wiki["asset_folder"] = str(asset_folder)
            wiki["asset_files"] = [p.name for p in asset_folder.iterdir() if p.is_file()]
        for skill in item.get("skills", []):
            effect_text = (skill.get("wiki") or {}).get("effects_text")
            skill["common_terms"] = extract_common_terms(effect_text, common_lookup)
            skill["template_hints"] = infer_template_hints(effect_text, template_lookup)
        for passive_rows in (item.get("passives") or {}).values():
            for passive in passive_rows:
                effect_text = (passive.get("wiki") or {}).get("text") or (passive.get("wiki") or {}).get("description")
                passive["common_terms"] = extract_common_terms(effect_text, common_lookup)
                passive["template_hints"] = infer_template_hints(effect_text, template_lookup)
    if KEYWORD_ASSET_DIR and KEYWORD_ASSET_DIR.exists():
        data["keyword_asset_folder"] = str(KEYWORD_ASSET_DIR)
        data["keyword_asset_files"] = [p.name for p in KEYWORD_ASSET_DIR.rglob("*.png") if p.is_file()]
    data["token_lookup"] = token_lookup
    data["trigger_keywords"] = TRIGGER_KEYWORDS
    data["common_effect_templates"] = template_lookup
    return data


def build_html(data: dict) -> str:
    data = enrich_data(data)
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Limbus Identity Review</title>
  <style>
    :root {
      --bg: #111315;
      --panel: #181b1e;
      --panel-2: #202428;
      --line: #343a40;
      --text: #eee8dc;
      --muted: #aeb6bb;
      --gold: #d5b56d;
      --green: #63c084;
      --red: #e07569;
      --blue: #73a7df;
      --ink: #0d0f10;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      overflow: auto;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--text);
      background: var(--bg);
    }
    button, input, select { font: inherit; }
    .app {
      display: grid;
      grid-template-columns: 330px minmax(0, 1fr);
      min-height: 100vh;
    }
    aside {
      position: sticky;
      top: 0;
      height: 100vh;
      border-right: 1px solid var(--line);
      background: #151719;
      min-width: 0;
      display: flex;
      flex-direction: column;
    }
    .side-head { padding: 18px 16px 12px; border-bottom: 1px solid var(--line); }
    h1 { margin: 0 0 12px; font-size: 18px; line-height: 1.25; font-weight: 750; }
    .search {
      width: 100%;
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #0f1113;
      color: var(--text);
      padding: 0 10px;
      outline: none;
    }
    .identity-list { overflow: auto; padding: 8px; }
    .identity-btn {
      width: 100%;
      min-height: 82px;
      margin: 0 0 8px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #1a1d20;
      color: var(--text);
      text-align: left;
      padding: 10px;
      cursor: pointer;
    }
    .identity-btn.active { border-color: var(--gold); background: #24221b; }
    .identity-btn strong { display: block; font-size: 13px; line-height: 1.25; }
    .identity-btn span { display: block; color: var(--muted); font-size: 12px; margin-top: 3px; }
    .mini-row { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 2px 7px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
    }
    .pill.ok { color: var(--green); border-color: rgba(99,192,132,.45); }
    .pill.warn { color: var(--red); border-color: rgba(224,117,105,.5); }
    main { min-width: 0; overflow: visible; background: #101214; }
    .topbar {
      position: sticky;
      top: 0;
      z-index: 5;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      padding: 16px 20px;
      border-bottom: 1px solid var(--line);
      background: rgba(16,18,20,.96);
      backdrop-filter: blur(8px);
    }
    .title-line { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    h2 { margin: 0; font-size: 20px; line-height: 1.22; }
    .subline { color: var(--muted); margin-top: 5px; font-size: 13px; }
    .controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
    .seg { display: inline-flex; border: 1px solid var(--line); border-radius: 7px; overflow: hidden; height: 34px; }
    .seg button {
      min-width: 42px;
      border: 0;
      border-right: 1px solid var(--line);
      background: var(--panel);
      color: var(--muted);
      cursor: pointer;
    }
    .seg button:last-child { border-right: 0; }
    .seg button.active { background: var(--gold); color: var(--ink); font-weight: 750; }
    .action {
      height: 34px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--panel);
      color: var(--text);
      padding: 0 10px;
      cursor: pointer;
    }
    .content { padding: 18px 20px 40px; }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(150px, 1fr));
      gap: 10px;
      margin-bottom: 18px;
    }
    .stat {
      min-height: 72px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 10px;
    }
    .stat label { display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
    .stat strong { display: block; margin-top: 6px; font-size: 16px; }
    .stat p { margin: 6px 0 0; color: var(--muted); font-size: 12px; line-height: 1.35; }
    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 22px 0 10px;
    }
    h3 { margin: 0; font-size: 16px; }
    .skill-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 12px;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      min-width: 0;
      overflow: hidden;
    }
    .skill-title-row { display: grid; grid-template-columns: 54px minmax(0, 1fr); gap: 10px; align-items: center; }
    .skill-icon-stack {
      position: relative;
      width: 54px;
      height: 54px;
      border-radius: 7px;
      background: #08090a;
      border: 1px solid var(--line);
      overflow: hidden;
      flex: 0 0 auto;
    }
    .skill-icon-stack img { position: absolute; object-fit: contain; pointer-events: none; }
    .skill-icon-bg { inset: -3px; width: 58px; height: 58px; z-index: 1; }
    .skill-icon-art { inset: 8px; width: 38px; height: 38px; border-radius: 4px; z-index: 2; }
    .skill-icon-rim { inset: -3px; width: 58px; height: 58px; z-index: 3; }
    .skill-icon-empty { display: grid; place-items: center; color: var(--muted); font-size: 10px; }
    .card-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      padding: 12px;
      border-bottom: 1px solid var(--line);
      background: var(--panel-2);
    }
    .card h4 { margin: 0; font-size: 15px; line-height: 1.25; }
    .local-name { color: var(--muted); font-size: 12px; margin-top: 3px; overflow-wrap: anywhere; }
    .badge {
      align-self: start;
      padding: 3px 7px;
      border-radius: 999px;
      border: 1px solid var(--line);
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
    }
    .badge.ok { color: var(--green); border-color: rgba(99,192,132,.45); }
    .badge.warn { color: var(--red); border-color: rgba(224,117,105,.5); }
    .meta {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 1px;
      background: var(--line);
    }
    .meta div { background: #141719; padding: 8px; min-width: 0; }
    .meta label { display: block; color: var(--muted); font-size: 10px; text-transform: uppercase; }
    .meta strong { display: block; margin-top: 3px; font-size: 13px; overflow-wrap: anywhere; }
    .text-block { padding: 12px; border-top: 1px solid var(--line); }
    .text-block label { display: block; color: var(--gold); font-size: 11px; text-transform: uppercase; margin-bottom: 6px; }
    pre, .rich-text {
      margin: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 12px;
      line-height: 1.45;
      color: #e6e0d6;
    }
    .edit-text {
      width: 100%;
      min-height: 86px;
      margin-top: 10px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #0f1113;
      color: var(--text);
      padding: 9px 10px;
      font: 12px/1.45 "Segoe UI", Arial, sans-serif;
      outline: none;
    }
    .edit-text:focus { border-color: var(--gold); box-shadow: 0 0 0 2px rgba(213,181,109,.14); }
    .edit-note { margin-top: 7px; color: var(--muted); font-size: 11px; }
    .edit-panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 12px;
      margin-bottom: 18px;
    }
    .edit-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 10px;
    }
    .edit-field label {
      display: block;
      color: var(--gold);
      font-size: 10px;
      text-transform: uppercase;
      margin-bottom: 5px;
    }
    .edit-input {
      width: 100%;
      height: 32px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #0f1113;
      color: var(--text);
      padding: 0 9px;
      outline: none;
    }
    .edit-input:focus { border-color: var(--gold); box-shadow: 0 0 0 2px rgba(213,181,109,.14); }
    .inline-icon {
      width: 18px;
      height: 18px;
      object-fit: contain;
      vertical-align: -4px;
      margin: 0 2px;
    }
    .missing-icon { color: var(--blue); }
    .token-icon { display: inline-flex; align-items: center; gap: 3px; white-space: nowrap; }
    .trigger-token { font-weight: 700; white-space: nowrap; }
    .term-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px; }
    .term {
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #141719;
      padding: 8px;
      min-width: 0;
    }
    .term strong { display: block; font-size: 12px; overflow-wrap: anywhere; }
    .term span { display: block; color: var(--muted); font-size: 11px; margin-top: 3px; overflow-wrap: anywhere; }
    .template-list { display: grid; gap: 6px; }
    .template-row { border-left: 2px solid var(--blue); padding-left: 8px; color: var(--muted); font-size: 12px; }
    .passive-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 12px; }
    .empty {
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 18px;
      color: var(--muted);
      background: var(--panel);
    }
    .error-box {
      display: none;
      margin-bottom: 14px;
      border: 1px solid rgba(224,117,105,.65);
      border-radius: 8px;
      background: #261716;
      color: #ffd8d3;
      padding: 12px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-size: 12px;
      line-height: 1.45;
    }
    @media (max-width: 900px) {
      body { overflow: auto; }
      .app { display: block; height: auto; }
      aside { height: 320px; border-right: 0; border-bottom: 1px solid var(--line); }
      main { overflow: visible; }
      .topbar { grid-template-columns: 1fr; }
      .controls { justify-content: flex-start; }
      .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .skill-grid, .passive-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <div class="side-head">
        <h1>Identity Import Review</h1>
        <input id="search" class="search" placeholder="Search identity, sinner, ID">
      </div>
      <div id="identityList" class="identity-list"></div>
    </aside>
    <main>
      <div class="topbar">
        <div>
          <div class="title-line">
            <h2 id="identityTitle"></h2>
            <span id="identityStatus" class="badge"></span>
          </div>
          <div id="identitySubline" class="subline"></div>
        </div>
        <div class="controls">
          <div class="seg" id="uptieSeg" aria-label="Uptie"></div>
          <div class="seg" id="filterSeg" aria-label="Review filter"></div>
          <button class="action" id="downloadJson">Download Current</button>
          <button class="action" id="downloadAllJson">Download All JSON</button>
          <button class="action" id="clearDraft">Clear Draft</button>
        </div>
      </div>
      <div class="content">
        <div id="errorBox" class="error-box"></div>
        <div id="summaryGrid" class="summary-grid"></div>
        <div id="canonicalEditor" class="edit-panel"></div>
        <div class="section-head"><h3 id="skillHeading">Skills</h3><span id="skillCount" class="pill"></span></div>
        <div id="skillGrid" class="skill-grid"></div>
        <div class="section-head"><h3>Passives</h3><span id="passiveCount" class="pill"></span></div>
        <div id="passiveGrid" class="passive-grid"></div>
      </div>
    </main>
  </div>
  <script type="application/json" id="review-data">__DATA__</script>
  <script>
    const DATA = JSON.parse(document.getElementById("review-data").textContent);
    const state = { index: 0, uptie: 4, filter: "all", search: "" };
    const slotOrder = { skill_1: 1, skill_2: 2, skill_3: 3, defense: 4 };

    const $ = (id) => document.getElementById(id);
    const text = (value, fallback = "-") => {
      if (value === null || value === undefined || value === "") return fallback;
      return String(value);
    };
    const safe = (value, fallback = "-") => text(value, fallback).replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[char]));
    const pairLocalRaw = (pair) => pair && pair.local ? pair.local : "";
    const pairEnRaw = (pair) => pair && pair.en ? pair.en : "";
    const pairLocal = (pair) => text(pairLocalRaw(pair));
    const pairEn = (pair) => text(pairEnRaw(pair));
    const fileUrl = (folder, file) => encodeURI(`file:///${String(folder).split("\\\\").join("/")}/${file}`);
    const tokenStem = (token) => String(token).replace(/\.[^.]+$/, "");
    const assetKey = (value) => tokenStem(value || "")
      .toLowerCase()
      .replace(/^\d+px-/, "")
      .replace(/[_-]+/g, " ")
      .replace(/[^0-9a-z]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    const assetForToken = (item, token) => {
      const wiki = item.wiki_identity || {};
      const files = wiki.asset_files || [];
      const wanted = String(token || "").toLowerCase();
      const key = assetKey(token);
      const found = files.find((file) => file.toLowerCase().endsWith(wanted))
        || files.find((file) => assetKey(file) === key)
        || files.find((file) => assetKey(file).endsWith(key));
      return found && wiki.asset_folder ? fileUrl(wiki.asset_folder, found) : null;
    };
    const skillIconStack = (item, wiki) => {
      const affinityRank = wiki && wiki.affinity && wiki.rank ? `${wiki.affinity}${wiki.rank}` : null;
      const bg = affinityRank ? assetForToken(item, `${affinityRank}BG.png`) : null;
      const rim = affinityRank ? assetForToken(item, `${affinityRank}.png`) : null;
      const art = assetForToken(item, wiki && wiki.icon_alt);
      if (!bg && !rim && !art) return `<div class="skill-icon-stack skill-icon-empty">no icon</div>`;
      return `<div class="skill-icon-stack" title="${safe(text(wiki && wiki.icon_alt))}">
        ${bg ? `<img class="skill-icon-bg" src="${bg}" alt="">` : ""}
        ${rim ? `<img class="skill-icon-rim" src="${rim}" alt="">` : ""}
        ${art ? `<img class="skill-icon-art" src="${art}" alt="${safe(wiki && wiki.name)}">` : ""}
      </div>`;
    };
    const keywordAssetForToken = (token) => {
      const files = DATA.keyword_asset_files || [];
      const folder = DATA.keyword_asset_folder;
      const stem = tokenStem(token).toLowerCase();
      const found = files.find((file) => tokenStem(file).toLowerCase() === stem)
        || files.find((file) => tokenStem(file).toLowerCase().includes(stem));
      return found && folder ? fileUrl(folder, found) : null;
    };
    const cleanMarkupText = (value, fallback = "-") => text(value, fallback)
      .replace(/<style=\"highlight\">/g, "")
      .replace(/<\/style>/g, "");
    const tokenDisplay = (token) => {
      const term = (DATA.token_lookup || {})[token];
      if (!term) return tokenStem(token);
      return pairLocal(term.name) || pairEn(term.name) || tokenStem(token);
    };
    const tokenMarkup = (rawToken, item, source) => {
      const token = String(rawToken).trim();
      const trigger = (DATA.trigger_keywords || {})[token];
      if (trigger) return `<span class="trigger-token" style="color:${safe(trigger.color)}">${safe(trigger.en)}</span>`;
      const src = source === "wiki" ? assetForToken(item, token) : keywordAssetForToken(token);
      const label = source === "wiki" ? tokenStem(token) : tokenDisplay(token);
      if (!src) return `<span class="missing-icon">[${safe(label)}]</span>`;
      if (source === "wiki") return `<img class="inline-icon" src="${src}" title="${safe(label)}" alt="${safe(label)}">`;
      return `<span class="token-icon"><img class="inline-icon" src="${src}" title="${safe(label)}" alt="${safe(label)}"><span>[${safe(label)}]</span></span>`;
    };
    const richWikiText = (value, item, fallback = "-") => safe(value, fallback)
      .replace(/\[img:([^\]]+)\]/g, (full, token) => tokenMarkup(token, item, "wiki"));
    const richLocalizedText = (value, item, fallback = "-") => safe(cleanMarkupText(value, fallback))
      .replace(/\[([^\]\\n]+)\]/g, (full, token) => tokenMarkup(token, item, "localized"));
    const commonBlock = (row) => {
      const terms = row.common_terms || [];
      const templates = row.template_hints || [];
      if (!terms.length && !templates.length) return "";
      const termHtml = terms.length ? `<div class="text-block"><label>Common Terms from Bufs / BattleKeywords</label><div class="term-grid">${terms.map((term) => `
        <div class="term"><strong>${safe(pairLocal(term.name))}</strong><span>${term.kind} / ${term.id} / EN: ${safe(pairEn(term.name))}</span><span>${safe(pairLocal(term.summary || term.desc))}</span></div>
      `).join("")}</div></div>` : "";
      const templateHtml = templates.length ? `<div class="text-block"><label>BuffAbility Template Hints</label><div class="template-list">${templates.map((template) => `
        <div class="template-row"><strong>${safe(template.id)}</strong> / ${safe(pairEn(template.desc))}<br>${safe(pairLocal(template.desc))}</div>
      `).join("")}</div></div>` : "";
      return termHtml + templateHtml;
    };
    const fallbackClass = (pair) => pair && pair.local && pair.en && pair.local !== pair.en ? "" : " EN fallback";
    const adminEdit = (target) => {
      if (!target.admin_edit) target.admin_edit = {};
      return target.admin_edit;
    };
    const canonValue = (target, key, fallback = "") => {
      const edits = target && target.admin_edit ? target.admin_edit : {};
      if (edits[key] !== undefined && edits[key] !== null && edits[key] !== "") return edits[key];
      return fallback;
    };
    const editInput = (label, edit, key, value, extra = "") => `
      <div class="edit-field">
        <label>${safe(label)}</label>
        <input class="edit-input" data-edit="${edit}" data-key="${key}" ${extra} value="${safe(value, "")}">
      </div>`;
    const readNumber = (value) => {
      if (value === null || value === undefined || String(value).trim() === "") return null;
      const number = Number(value);
      return Number.isFinite(number) ? number : value;
    };
    const identityName = (item) => {
      const wiki = item.wiki_identity || {};
      return canonValue(item, "english_name", `${text(wiki.identity_name, "")} ${text(wiki.sinner, "")}`.trim());
    };
    const matchCounts = (item) => {
      const skills = item.skills || [];
      const passives = Object.values(item.passives || {}).flat();
      return {
        skillsMatched: skills.filter((row) => row.localization_match).length,
        skillsTotal: skills.length,
        passivesMatched: passives.filter((row) => row.localization_match).length,
        passivesTotal: passives.length,
      };
    };
    const isVisibleStatus = (row) => state.filter === "all" || row.review_status === state.filter;
    const statusBadge = (status) => status === "matched"
      ? `<span class="badge ok">matched</span>`
      : `<span class="badge warn">needs review</span>`;

    const DRAFT_KEY = "limbus_identity_review_admin_edits_v2";
    function gatherAdminEdits() {
      return (DATA.identities || []).map((item) => ({
        identity: item.admin_edit || null,
        skills: (item.skills || []).map((skill) => skill.admin_edit || null),
        passives: Object.fromEntries(Object.entries(item.passives || {}).map(([type, list]) => [
          type,
          (list || []).map((passive) => passive.admin_edit || null),
        ])),
      }));
    }
    function applyAdminEdits(snapshot) {
      if (!Array.isArray(snapshot)) return;
      snapshot.forEach((saved, index) => {
        const item = (DATA.identities || [])[index];
        if (!item || !saved) return;
        if (saved.identity) item.admin_edit = saved.identity;
        (saved.skills || []).forEach((edit, skillIndex) => {
          if (edit && item.skills && item.skills[skillIndex]) item.skills[skillIndex].admin_edit = edit;
        });
        Object.entries(saved.passives || {}).forEach(([type, edits]) => {
          const list = (item.passives || {})[type] || [];
          (edits || []).forEach((edit, passiveIndex) => {
            if (edit && list[passiveIndex]) list[passiveIndex].admin_edit = edit;
          });
        });
      });
    }
    function saveDraft() {
      try { localStorage.setItem(DRAFT_KEY, JSON.stringify(gatherAdminEdits())); } catch (error) {}
    }
    try { applyAdminEdits(JSON.parse(localStorage.getItem(DRAFT_KEY) || "null")); } catch (error) {}
    function renderIdentityList() {
      const q = state.search.trim().toLowerCase();
      $("identityList").innerHTML = DATA.identities
        .map((item, index) => ({ item, index }))
        .filter(({ item }) => {
          const ident = item.localization_identity_match || {};
          const hay = `${identityName(item)} ${text(ident.source_personality_id, "")}`.toLowerCase();
          return !q || hay.includes(q);
        })
        .map(({ item, index }) => {
          const ident = item.localization_identity_match || {};
          const counts = matchCounts(item);
          const allOk = counts.skillsMatched === counts.skillsTotal && counts.passivesMatched === counts.passivesTotal;
          return `<button class="identity-btn ${index === state.index ? "active" : ""}" data-index="${index}">
            <strong>${identityName(item)}</strong>
            <span>ID ${text(ident.source_personality_id)} / ${pairLocal(ident.title)} ${pairLocal(ident.name)}</span>
            <div class="mini-row">
              <span class="pill ${counts.skillsMatched === counts.skillsTotal ? "ok" : "warn"}">Skills ${counts.skillsMatched}/${counts.skillsTotal}</span>
              <span class="pill ${counts.passivesMatched === counts.passivesTotal ? "ok" : "warn"}">Passives ${counts.passivesMatched}/${counts.passivesTotal}</span>
              <span class="pill ${allOk ? "ok" : "warn"}">${allOk ? "Ready" : "Review"}</span>
            </div>
          </button>`;
        }).join("") || `<div class="empty">No identities match that search.</div>`;
      document.querySelectorAll(".identity-btn").forEach((button) => {
        button.addEventListener("click", () => {
          state.index = Number(button.dataset.index);
          safeRender();
        });
      });
    }

    function renderControls() {
      $("uptieSeg").innerHTML = [1, 2, 3, 4].map((value) =>
        `<button class="${state.uptie === value ? "active" : ""}" data-uptie="${value}">UT${value}</button>`
      ).join("");
      $("filterSeg").innerHTML = [
        ["all", "All"],
        ["matched", "Matched"],
        ["needs_review", "Review"],
      ].map(([value, label]) =>
        `<button class="${state.filter === value ? "active" : ""}" data-filter="${value}">${label}</button>`
      ).join("");
      document.querySelectorAll("[data-uptie]").forEach((button) => {
        button.addEventListener("click", () => {
          state.uptie = Number(button.dataset.uptie);
          safeRender();
        });
      });
      document.querySelectorAll("[data-filter]").forEach((button) => {
        button.addEventListener("click", () => {
          state.filter = button.dataset.filter;
          safeRender();
        });
      });
    }

    function renderSummary(item) {
      const wiki = item.wiki_identity || {};
      const ident = item.localization_identity_match || {};
      const stats = wiki.stats || {};
      const speed = (stats.speed_by_uptie || {})[`uptie_${state.uptie}`];
      const res = stats.resistances || {};
      $("summaryGrid").innerHTML = [
        ["Localization", `ID ${text(ident.source_personality_id)}`, `${pairLocal(ident.title)} ${pairLocal(ident.name)}${fallbackClass(ident.title)}`],
        ["Combat Stats", `HP ${text(stats.hp)} / Speed ${text(speed)}`, `Defense level ${text(stats.defense_level)} / Rarity ${text(wiki.rarity)}`],
        ["Resistances", `${text(res.slash && res.slash.multiplier)} / ${text(res.pierce && res.pierce.multiplier)} / ${text(res.blunt && res.blunt.multiplier)}`, `Slash / Pierce / Blunt (${text(res.slash && res.slash.label)} / ${text(res.pierce && res.pierce.label)} / ${text(res.blunt && res.blunt.label)})`],
        ["Source", text(wiki.source && wiki.source.type), text(wiki.source && wiki.source.path)],
      ].map(([label, strong, body]) => `<div class="stat"><label>${label}</label><strong>${strong}</strong><p>${body}</p></div>`).join("");
    }

    function renderCanonicalEditor(item) {
      const wiki = item.wiki_identity || {};
      const stats = wiki.stats || {};
      const res = stats.resistances || {};
      const edit = item.admin_edit || {};
      $("canonicalEditor").innerHTML = `
        <div class="section-head" style="margin:0 0 10px"><h3>Canonical Bot Data</h3><span class="pill">exports to English/system JSON</span></div>
        <div class="edit-grid">
          ${editInput("English Name", "identity-canonical", "english_name", identityName(item))}
          ${editInput("Sinner", "identity-canonical", "sinner", canonValue(item, "sinner", wiki.sinner || ""))}
          ${editInput("Rarity", "identity-canonical", "rarity", canonValue(item, "rarity", wiki.rarity ?? ""), 'type="number"')}
          ${editInput("HP", "identity-canonical", "hp", canonValue(item, "hp", stats.hp ?? ""), 'type="number"')}
          ${editInput("Defense Level", "identity-canonical", "defense_level", canonValue(item, "defense_level", stats.defense_level ?? ""), 'type="number"')}
          ${editInput("Slash Res", "identity-canonical", "res_slash", canonValue(item, "res_slash", (res.slash && res.slash.multiplier) ?? ""))}
          ${editInput("Pierce Res", "identity-canonical", "res_pierce", canonValue(item, "res_pierce", (res.pierce && res.pierce.multiplier) ?? ""))}
          ${editInput("Blunt Res", "identity-canonical", "res_blunt", canonValue(item, "res_blunt", (res.blunt && res.blunt.multiplier) ?? ""))}
        </div>
        <div class="edit-note">These are the bot/simulator fields. They override parsed wiki/localization data only in downloaded JSON.</div>
      `;
    }
    function sortSkills(rows) {
      return [...rows].sort((a, b) => {
        const aw = a.wiki || {};
        const bw = b.wiki || {};
        return (slotOrder[aw.slot] || 99) - (slotOrder[bw.slot] || 99)
          || text(aw.name).localeCompare(text(bw.name));
      });
    }

    function skillCanonicalBlock(row) {
      const wiki = row.wiki || {};
      const match = row.localization_match || {};
      const desc = canonValue(row, "english_description", pairEnRaw(match.desc) || wiki.effects_text || "");
      const level = wiki.level || {};
      return `<div class="text-block">
        <label>Bot / English Skill Data</label>
        <div class="edit-grid">
          ${editInput("English Skill Name", "skill-canonical", "english_name", canonValue(row, "english_name", pairEnRaw(match.name) || wiki.name || ""), `data-skill-index="${row.sourceIndex}"`)}
          ${editInput("Affinity", "skill-canonical", "affinity", canonValue(row, "affinity", wiki.affinity || ""), `data-skill-index="${row.sourceIndex}"`)}
          ${editInput("Damage Type", "skill-canonical", "damage_type", canonValue(row, "damage_type", wiki.damage_type || ""), `data-skill-index="${row.sourceIndex}"`)}
          ${editInput("Base Power", "skill-canonical", "base_power", canonValue(row, "base_power", wiki.base_power ?? ""), `data-skill-index="${row.sourceIndex}"`)}
          ${editInput("Coin Power", "skill-canonical", "coin_power", canonValue(row, "coin_power", wiki.coin_power ?? ""), `data-skill-index="${row.sourceIndex}"`)}
          ${editInput("Coin Count", "skill-canonical", "coin_count", canonValue(row, "coin_count", wiki.coin_count ?? ""), `data-skill-index="${row.sourceIndex}"`)}
          ${editInput("Atk Weight", "skill-canonical", "attack_weight", canonValue(row, "attack_weight", wiki.attack_weight ?? ""), `data-skill-index="${row.sourceIndex}"`)}
          ${editInput("Offense Total", "skill-canonical", "offense_total", canonValue(row, "offense_total", level.total ?? ""), `data-skill-index="${row.sourceIndex}"`)}
        </div>
        <textarea class="edit-text" data-edit="skill-canonical" data-key="english_description" data-skill-index="${row.sourceIndex}">${safe(desc, "")}</textarea>
        <div class="edit-note">These fields are exported for bot search/tool use. Localized text below is only for final display language.</div>
      </div>`;
    }

    function passiveCanonicalBlock(row) {
      const wiki = row.wiki || {};
      const match = row.localization_match || {};
      const desc = canonValue(row, "english_description", pairEnRaw(match.desc) || wiki.text || wiki.description || "");
      return `<div class="text-block">
        <label>Bot / English Passive Data</label>
        <div class="edit-grid">
          ${editInput("English Passive Name", "passive-canonical", "english_name", canonValue(row, "english_name", pairEnRaw(match.name) || wiki.name || ""), `data-passive-type="${row.passiveType}" data-passive-index="${row.sourceIndex}"`)}
          ${editInput("Requirement", "passive-canonical", "requirement", canonValue(row, "requirement", wiki.requirement || ""), `data-passive-type="${row.passiveType}" data-passive-index="${row.sourceIndex}"`)}
        </div>
        <textarea class="edit-text" data-edit="passive-canonical" data-key="english_description" data-passive-type="${row.passiveType}" data-passive-index="${row.sourceIndex}">${safe(desc, "")}</textarea>
      </div>`;
    }
    function renderSkills(item) {
      const rows = sortSkills((item.skills || []).map((row, sourceIndex) => ({ ...row, sourceIndex })).filter((row) => {
        const wiki = row.wiki || {};
        return Number(wiki.uptie) === state.uptie && isVisibleStatus(row);
      }));
      $("skillHeading").textContent = `Skills - Uptie ${state.uptie}`;
      $("skillCount").textContent = `${rows.length} visible`;
      $("skillGrid").innerHTML = rows.map((row) => {
        const wiki = row.wiki || {};
        const match = row.localization_match || {};
        const level = wiki.level || {};
        const coinTexts = (match.coin_texts || []).map((coin) => `[Coin ${text(coin.coin_index)}.${text(coin.effect_index)}] ${pairLocal(coin.desc)}`).join("\\n\\n");
        const skillIcon = skillIconStack(item, wiki);
        return `<article class="card">
          <div class="card-head">
            <div class="skill-title-row">
              ${skillIcon}
              <div>
                <h4>${text(wiki.name)}</h4>
                <div class="local-name">${pairLocal(match.name)}${fallbackClass(match.name)}</div>
              </div>
            </div>
            ${statusBadge(row.review_status)}
          </div>
          <div class="meta">
            <div><label>Slot</label><strong>${text(wiki.slot)} / UT${text(wiki.uptie)}</strong></div>
            <div><label>Power</label><strong>${text(wiki.base_power)} ${text(wiki.coin_power)} x${text(wiki.coin_count)}</strong></div>
            <div><label>Type</label><strong>${text(wiki.affinity)} ${text(wiki.damage_type)}</strong></div>
            <div><label>Level</label><strong>${text(level.total)} (${text(level.base)}+${text(level.correction)})</strong></div>
            <div><label>Weight</label><strong>${text(wiki.attack_weight)}</strong></div>
            <div><label>Local ID</label><strong>${text(match.source_skill_text_id)}</strong></div>
            <div><label>Match</label><strong>${text(match.score)}</strong></div>
            <div><label>Icon</label><strong>${text(wiki.icon_alt)}</strong></div>
          </div>
          ${skillCanonicalBlock(row)}
          <div class="text-block"><label>Localized Description</label><div class="rich-text">${richLocalizedText(pairLocal(match.desc), item)}</div><textarea class="edit-text" data-edit="skill-desc" data-skill-index="${row.sourceIndex}">${safe(pairLocal(match.desc), "")}</textarea><div class="edit-note">Edit raw localized text, then click elsewhere to refresh preview.</div></div>
          <div class="text-block"><label>Localized Coin Text</label><div class="rich-text">${richLocalizedText(coinTexts, item, "No localized coin text.")}</div>${(match.coin_texts || []).map((coin, coinIndex) => `<textarea class="edit-text" data-edit="coin-desc" data-skill-index="${row.sourceIndex}" data-coin-index="${coinIndex}">${safe(pairLocal(coin.desc), "")}</textarea>`).join("")}<div class="edit-note">Each box writes back to that coin effect.</div></div>
          ${commonBlock(row)}
        </article>`;
      }).join("") || `<div class="empty">No skills for this uptie/filter.</div>`;
    }

    function renderPassives(item) {
      const rows = Object.entries(item.passives || {}).flatMap(([type, list]) =>
        (list || []).map((row, sourceIndex) => ({ ...row, passiveType: type, sourceIndex }))
      ).filter(isVisibleStatus);
      $("passiveCount").textContent = `${rows.length} visible`;
      $("passiveGrid").innerHTML = rows.map((row) => {
        const wiki = row.wiki || {};
        const match = row.localization_match || {};
        return `<article class="card">
          <div class="card-head">
            <div>
              <h4>${text(wiki.name)}</h4>
              <div class="local-name">${row.passiveType} / ${pairLocal(match.name)}${fallbackClass(match.name)}</div>
            </div>
            ${statusBadge(row.review_status)}
          </div>
          <div class="meta">
            <div><label>Type</label><strong>${row.passiveType}</strong></div>
            <div><label>Requirement</label><strong>${text(wiki.requirement)}</strong></div>
            <div><label>Local ID</label><strong>${text(match.source_passive_text_id)}</strong></div>
            <div><label>Match</label><strong>${text(match.score)}</strong></div>
          </div>
          ${passiveCanonicalBlock(row)}
          <div class="text-block"><label>Localized Passive</label><div class="rich-text">${richLocalizedText(pairLocal(match.desc), item)}</div><textarea class="edit-text" data-edit="passive-desc" data-passive-type="${row.passiveType}" data-passive-index="${row.sourceIndex}">${safe(pairLocal(match.desc), "")}</textarea><div class="edit-note">Edit raw localized passive text, then click elsewhere to refresh preview.</div></div>
          ${commonBlock(row)}
        </article>`;
      }).join("") || `<div class="empty">No passives for this filter.</div>`;
    }

    function render() {
      renderIdentityList();
      renderControls();
      const item = DATA.identities[state.index];
      const wiki = item.wiki_identity || {};
      const ident = item.localization_identity_match || {};
      const counts = matchCounts(item);
      const allOk = counts.skillsMatched === counts.skillsTotal && counts.passivesMatched === counts.passivesTotal;
      $("identityTitle").textContent = identityName(item);
      $("identitySubline").textContent = `Localized: ${pairLocal(ident.title)} ${pairLocal(ident.name)} / source ${text(ident.source_personality_id)}`;
      $("identityStatus").className = `badge ${allOk ? "ok" : "warn"}`;
      $("identityStatus").textContent = allOk ? "ready" : "needs review";
      renderSummary(item);
      renderCanonicalEditor(item);
      renderSkills(item);
      renderPassives(item);
    }

    $("search").addEventListener("input", (event) => {
      state.search = event.target.value;
      safeRenderIdentityList();
    });
    function showError(error) {
      const box = $("errorBox");
      if (!box) return;
      box.style.display = "block";
      box.textContent = `Review page render failed:\n${error && (error.stack || error.message || error)}`;
    }

    function safeRender() {
      try {
        $("errorBox").style.display = "none";
        render();
      } catch (error) {
        showError(error);
      }
    }

    function safeRenderIdentityList() {
      try {
        renderIdentityList();
      } catch (error) {
        showError(error);
      }
    }

    function setPairLocal(pair, value) {
      if (!pair) return;
      pair.local = value;
    }

    function updateEditTarget(target) {
      const item = DATA.identities[state.index];
      const kind = target.dataset.edit;
      if (kind === "identity-canonical") {
        const edits = adminEdit(item);
        edits[target.dataset.key] = target.value;
      }
      if (kind === "skill-canonical") {
        const skill = (item.skills || [])[Number(target.dataset.skillIndex)];
        if (skill) adminEdit(skill)[target.dataset.key] = target.value;
      }
      if (kind === "passive-canonical") {
        const passive = (((item.passives || {})[target.dataset.passiveType]) || [])[Number(target.dataset.passiveIndex)];
        if (passive) adminEdit(passive)[target.dataset.key] = target.value;
      }
      if (kind === "skill-desc") {
        const skill = (item.skills || [])[Number(target.dataset.skillIndex)];
        setPairLocal(skill && skill.localization_match && skill.localization_match.desc, target.value);
      }
      if (kind === "coin-desc") {
        const skill = (item.skills || [])[Number(target.dataset.skillIndex)];
        const coin = skill && skill.localization_match && (skill.localization_match.coin_texts || [])[Number(target.dataset.coinIndex)];
        setPairLocal(coin && coin.desc, target.value);
      }
      if (kind === "passive-desc") {
        const passive = (((item.passives || {})[target.dataset.passiveType]) || [])[Number(target.dataset.passiveIndex)];
        setPairLocal(passive && passive.localization_match && passive.localization_match.desc, target.value);
      }
      saveDraft();
    }

    function resistanceExport(resistance) {
      return {
        slash: resistance && resistance.slash ? Number(resistance.slash.multiplier) : null,
        pierce: resistance && resistance.pierce ? Number(resistance.pierce.multiplier) : null,
        blunt: resistance && resistance.blunt ? Number(resistance.blunt.multiplier) : null,
      };
    }

    function finalizeIdentity(item) {
      const wiki = item.wiki_identity || {};
      const ident = item.localization_identity_match || {};
      const stats = wiki.stats || {};
      const englishName = identityName(item);
      return {
        schema_version: 1,
        kind: "limbus_identity",
        identity: {
          id: text(ident.source_personality_id, null),
          english_name: englishName,
          localized_name: `${pairLocal(ident.title)} ${pairLocal(ident.name)}`.trim(),
          sinner: canonValue(item, "sinner", text(wiki.sinner, null)),
          rarity: readNumber(canonValue(item, "rarity", wiki.rarity ?? null)),
        },
        combat_stats: {
          hp: readNumber(canonValue(item, "hp", stats.hp ?? null)),
          speed_by_uptie: stats.speed_by_uptie || {},
          defense_level: readNumber(canonValue(item, "defense_level", stats.defense_level ?? null)),
          resistances: {
            slash: readNumber(canonValue(item, "res_slash", stats.resistances && stats.resistances.slash ? stats.resistances.slash.multiplier : null)),
            pierce: readNumber(canonValue(item, "res_pierce", stats.resistances && stats.resistances.pierce ? stats.resistances.pierce.multiplier : null)),
            blunt: readNumber(canonValue(item, "res_blunt", stats.resistances && stats.resistances.blunt ? stats.resistances.blunt.multiplier : null)),
          },
        },
        skills: (item.skills || []).map((row) => {
          const wikiSkill = row.wiki || {};
          const match = row.localization_match || {};
          return {
            slot: wikiSkill.slot || match.slot || null,
            uptie: wikiSkill.uptie ?? null,
            source_skill_text_id: match.source_skill_text_id || null,
            name: { en: canonValue(row, "english_name", pairEnRaw(match.name) || wikiSkill.name || null), local: pairLocal(match.name) },
            affinity: canonValue(row, "affinity", wikiSkill.affinity || null),
            damage_type: canonValue(row, "damage_type", wikiSkill.damage_type || null),
            skill_type: wikiSkill.skill_type || null,
            base_power: readNumber(canonValue(row, "base_power", wikiSkill.base_power ?? null)),
            coin_power: readNumber(canonValue(row, "coin_power", wikiSkill.coin_power ?? null)),
            coin_count: readNumber(canonValue(row, "coin_count", wikiSkill.coin_count ?? null)),
            attack_weight: readNumber(canonValue(row, "attack_weight", wikiSkill.attack_weight ?? null)),
            offense_level: { ...(wikiSkill.level || {}), total: readNumber(canonValue(row, "offense_total", wikiSkill.level && wikiSkill.level.total ? wikiSkill.level.total : null)) },
            localized_description: pairLocal(match.desc),
            english_description: canonValue(row, "english_description", pairEnRaw(match.desc) || wikiSkill.effects_text || null),
            coin_texts: (match.coin_texts || []).map((coin) => ({
              coin_index: coin.coin_index,
              effect_index: coin.effect_index,
              local: pairLocal(coin.desc),
              en: pairEn(coin.desc),
            })),
          };
        }),
        passives: Object.fromEntries(Object.entries(item.passives || {}).map(([type, list]) => [
          type,
          (list || []).map((row) => {
            const wikiPassive = row.wiki || {};
            const match = row.localization_match || {};
            return {
              source_passive_text_id: match.source_passive_text_id || null,
              name: { en: canonValue(row, "english_name", pairEnRaw(match.name) || wikiPassive.name || null), local: pairLocal(match.name) },
              requirement: canonValue(row, "requirement", wikiPassive.requirement || null),
              local: pairLocal(match.desc),
              en: canonValue(row, "english_description", pairEnRaw(match.desc) || wikiPassive.text || wikiPassive.description || null),
            };
          })
        ])),
        admin_strategy_notes: {
          playstyle_summary: "",
          important_conditions: [],
          recommended_teams: [],
          boss_notes: [],
          rotation_notes: "",
        },
        import_review: {
          status: "reviewed_export",
          exported_at: new Date().toISOString(),
          source_html: wiki.source || null,
        },
      };
    }

    function filenameForIdentity(item) {
      return `${identityName(item) || "identity"}.json`.replace(/[<>:"/\\|?*]+/g, "_").replace(/\s+/g, " ").trim();
    }


    function finalizeAllIdentities() {
      return {
        schema_version: 1,
        kind: "limbus_identity_batch",
        exported_at: new Date().toISOString(),
        count: (DATA.identities || []).length,
        files: (DATA.identities || []).map((item) => ({
          filename: filenameForIdentity(item),
          data: finalizeIdentity(item),
        })),
      };
    }
    function downloadJson(filename, value) {
      const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }

    document.addEventListener("input", (event) => {
      if (event.target && event.target.matches(".edit-text, .edit-input")) updateEditTarget(event.target);
    });
    document.addEventListener("focusout", (event) => {
      if (event.target && event.target.matches(".edit-text, .edit-input")) {
        updateEditTarget(event.target);
        safeRender();
      }
    });
    document.addEventListener("change", (event) => {
      if (event.target && event.target.matches(".edit-text, .edit-input")) updateEditTarget(event.target);
    });

    $("downloadJson").addEventListener("click", () => {
      const item = DATA.identities[state.index];
      downloadJson(filenameForIdentity(item), finalizeIdentity(item));
      $("downloadJson").textContent = "Downloaded";
      setTimeout(() => $("downloadJson").textContent = "Download Current", 900);
    });
    $("downloadAllJson").addEventListener("click", () => {
      downloadJson("limbus_identity_batch.json", finalizeAllIdentities());
      $("downloadAllJson").textContent = "Downloaded";
      setTimeout(() => $("downloadAllJson").textContent = "Download All JSON", 900);
    });
    $("clearDraft").addEventListener("click", () => {
      try { localStorage.removeItem(DRAFT_KEY); } catch (error) {}
      (DATA.identities || []).forEach((item) => {
        delete item.admin_edit;
        (item.skills || []).forEach((skill) => delete skill.admin_edit);
        Object.values(item.passives || {}).flat().forEach((passive) => delete passive.admin_edit);
      });
      safeRender();
    });
    safeRender();
  </script>
</body>
</html>""".replace("__DATA__", payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static identity localization review app.")
    parser.add_argument("--input", type=Path, default=Path("outputs/wiki_identity_localized_review.json"))
    parser.add_argument("--out", type=Path, default=Path("outputs/wiki_identity_localized_review.html"))
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    args.out.write_text(build_html(data), encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()









































