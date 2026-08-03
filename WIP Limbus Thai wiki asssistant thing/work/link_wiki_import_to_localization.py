from __future__ import annotations

import argparse
import html
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


def norm(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\n", " ")
    value = value.replace("Ry\u014dsh\u016b", "Ryoshu")
    value = value.replace("::", " ")
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def best_ratio(left: str, right: str) -> float:
    return SequenceMatcher(None, norm(left), norm(right)).ratio()


def localized_pair(value: dict[str, str] | None) -> dict[str, str | None]:
    value = value or {}
    en = value.get("en") or value.get("local") or None
    local = value.get("local") or en
    return {"en": en, "local": local}


def level_for_uptie(levels: list[dict[str, Any]], uptie: int | None) -> dict[str, Any] | None:
    if not levels:
        return None
    if uptie is None:
        return levels[-1]
    exact = [level for level in levels if level.get("level") == uptie]
    if exact:
        return exact[-1]
    eligible = [level for level in levels if isinstance(level.get("level"), int) and level["level"] <= uptie]
    return eligible[-1] if eligible else levels[0]


def identity_display_name(identity: dict[str, Any]) -> str:
    title = localized_pair(identity.get("title")).get("en") or ""
    name = localized_pair(identity.get("name")).get("en") or ""
    return f"{title} {name}".strip()


def build_identity_candidates(curated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for identity in curated:
        title = localized_pair(identity.get("title")).get("en") or ""
        name = localized_pair(identity.get("name")).get("en") or ""
        candidates.append(
            {
                "id": identity.get("source_personality_id"),
                "sinner": name,
                "title": title,
                "display": identity_display_name(identity),
                "identity": identity,
            }
        )
    return candidates


def match_identity(wiki_identity: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    wiki_title = wiki_identity.get("identity_name") or ""
    wiki_sinner = wiki_identity.get("sinner") or ""
    ranked = []
    for candidate in candidates:
        if wiki_sinner and norm(candidate["sinner"]) != norm(wiki_sinner):
            continue
        score = max(
            best_ratio(wiki_title, candidate["title"]),
            best_ratio(f"{wiki_title} {wiki_sinner}", candidate["display"]),
        )
        ranked.append((score, candidate))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][0] < 0.72:
        return None
    chosen = ranked[0][1]
    return {
        "source_personality_id": chosen["id"],
        "title": localized_pair(chosen["identity"].get("title")),
        "name": localized_pair(chosen["identity"].get("name")),
        "score": round(ranked[0][0], 3),
        "identity": chosen["identity"],
    }


def match_skill(wiki_skill: dict[str, Any], localized_identity: dict[str, Any] | None) -> dict[str, Any] | None:
    if not localized_identity or not wiki_skill.get("name"):
        return None
    slot = wiki_skill.get("slot")
    ranked = []
    for skill in localized_identity.get("skills", []):
        slot_bonus = 0.15 if skill.get("slot") == slot else 0.0
        names = [localized_pair(level.get("name")).get("en") or "" for level in skill.get("levels", [])]
        score = max([best_ratio(wiki_skill.get("name"), name) for name in names] or [0.0]) + slot_bonus
        ranked.append((score, skill))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][0] < 0.88:
        return None
    skill = ranked[0][1]
    level = level_for_uptie(skill.get("levels", []), wiki_skill.get("uptie"))
    return {
        "source_skill_text_id": skill.get("source_skill_text_id"),
        "slot": skill.get("slot"),
        "score": round(min(ranked[0][0], 1.0), 3),
        "selected_level": level.get("level") if level else None,
        "name": localized_pair(level.get("name") if level else None),
        "desc": localized_pair(level.get("desc") if level else None),
        "coin_texts": level.get("coin_texts", []) if level else [],
    }


def match_passive(wiki_passive: dict[str, Any], passive_type: str, localized_identity: dict[str, Any] | None) -> dict[str, Any] | None:
    if not localized_identity or not wiki_passive.get("name"):
        return None
    ranked = []
    for passive in localized_identity.get("passives", []):
        if passive.get("passive_type") != passive_type:
            continue
        score = best_ratio(wiki_passive.get("name"), localized_pair(passive.get("name")).get("en") or "")
        ranked.append((score, passive))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked or ranked[0][0] < 0.82:
        return None
    passive = ranked[0][1]
    return {
        "source_passive_text_id": passive.get("source_passive_text_id"),
        "passive_type": passive.get("passive_type"),
        "score": round(ranked[0][0], 3),
        "name": localized_pair(passive.get("name")),
        "desc": localized_pair(passive.get("desc")),
        "summary": localized_pair(passive.get("summary")),
    }


def link_imports(wiki_imports: list[dict[str, Any]], curated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = build_identity_candidates(curated)
    linked = []
    for wiki_identity in wiki_imports:
        identity_match = match_identity(wiki_identity, candidates)
        localized_identity = identity_match.pop("identity") if identity_match else None
        skills = []
        for wiki_skill in wiki_identity.get("skills", []):
            skills.append(
                {
                    "wiki": wiki_skill,
                    "localization_match": match_skill(wiki_skill, localized_identity),
                    "review_status": "matched" if match_skill(wiki_skill, localized_identity) else "needs_review",
                }
            )
        passives: dict[str, list[dict[str, Any]]] = {"combat": [], "support": []}
        for passive_type, wiki_passives in wiki_identity.get("passives", {}).items():
            passives[passive_type] = [
                {
                    "wiki": passive,
                    "localization_match": match_passive(passive, passive_type, localized_identity),
                    "review_status": "matched" if match_passive(passive, passive_type, localized_identity) else "needs_review",
                }
                for passive in wiki_passives
            ]
        linked.append(
            {
                "wiki_identity": wiki_identity,
                "localization_identity_match": identity_match,
                "skills": skills,
                "passives": passives,
            }
        )
    return linked


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def write_review_html(linked: list[dict[str, Any]], out_path: Path) -> None:
    from build_identity_review_app import build_html

    out_path.write_text(build_html({"identities": linked}), encoding="utf-8")
    return

def main() -> None:
    parser = argparse.ArgumentParser(description="Link wiki identity imports to curated localization draft records.")
    parser.add_argument("--wiki", type=Path, default=Path("outputs/wiki_identity_imports.json"))
    parser.add_argument("--curated", type=Path, default=Path("outputs/curated_identity_drafts.json"))
    parser.add_argument("--out", type=Path, default=Path("outputs/wiki_identity_localized_review.json"))
    parser.add_argument("--html", type=Path, default=Path("outputs/wiki_identity_localized_review.html"))
    args = parser.parse_args()

    wiki = json.loads(args.wiki.read_text(encoding="utf-8"))["identities"]
    curated = json.loads(args.curated.read_text(encoding="utf-8"))["identities"]
    linked = link_imports(wiki, curated)
    from build_identity_review_app import enrich_data

    review_data = enrich_data({"identities": linked})
    args.out.write_text(json.dumps(review_data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_review_html(review_data["identities"], args.html)
    print(f"Linked {len(linked)} identities")
    print(f"Wrote {args.out}")
    print(f"Wrote {args.html}")


if __name__ == "__main__":
    main()

