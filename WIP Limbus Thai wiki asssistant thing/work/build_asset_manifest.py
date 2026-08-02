from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSET_ROOT = Path(
    "C:/Users/kimoj/Downloads/LC.Localization.Interface.1.4.2/"
    "LC Localization Interface 1.4\u02d02/"
    "[\u21f2] Assets Directory/"
    "Limbus Images"
)
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
SIN_AFFINITIES = {"wrath", "lust", "sloth", "gluttony", "gloom", "pride", "envy"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_stem(value: str | None) -> str:
    value = value or ""
    value = re.sub(r"\.(json|png|jpg|jpeg|webp|gif|html)$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^\d+px-", "", value)
    value = value.replace("_", " ").replace("-", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def norm(value: str | None) -> str:
    value = clean_stem(value).lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^0-9a-z]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def rel_or_abs(path: Path, base: Path | None) -> str:
    if base:
        try:
            return path.resolve().relative_to(base.resolve()).as_posix()
        except ValueError:
            pass
    return str(path.resolve())


def image_record(path: Path, source: str, base: Path | None) -> dict[str, Any]:
    return {
        "source": source,
        "path": rel_or_abs(path, base),
        "absolute_path": str(path.resolve()),
        "filename": path.name,
    }


def add_lookup(lookup: dict[str, list[dict[str, Any]]], key: str | None, record: dict[str, Any]) -> None:
    key = norm(key)
    if not key:
        return
    bucket = lookup.setdefault(key, [])
    if not any(item.get("absolute_path") == record.get("absolute_path") for item in bucket):
        bucket.append(record)


def scan_images(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTS]


def build_keyword_assets(asset_root: Path, base: Path | None) -> dict[str, Any]:
    keyword_root = asset_root / "Keywords"
    unsuitable_root = asset_root / "Keywords (Not suitable for Sprite tag)"
    by_token: dict[str, dict[str, Any]] = {}
    lookup: dict[str, list[dict[str, Any]]] = {}
    files: list[dict[str, Any]] = []

    for folder, source in [(keyword_root, "limbus_keywords"), (unsuitable_root, "limbus_keywords_extra")]:
        for path in scan_images(folder):
            record = image_record(path, source, base)
            token = clean_stem(path.name)
            files.append(record)
            by_token.setdefault(token, record)
            add_lookup(lookup, token, record)
            add_lookup(lookup, path.name, record)

    return {
        "count": len(files),
        "files": files,
        "by_token": by_token,
        "lookup": lookup,
    }


def build_limbus_skill_metadata(asset_root: Path) -> dict[str, Any]:
    skill_root = asset_root / "Skills"
    by_skill_id: dict[str, dict[str, Any]] = {}
    files: list[str] = []

    for path in skill_root.rglob("*.json") if skill_root.exists() else []:
        files.append(str(path.resolve()))
        try:
            data = load_json(path)
        except Exception:
            continue
        rows = data if isinstance(data, list) else data.get("list") or data.get("data") or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            skill_id = row.get("id") or row.get("skillId") or row.get("skill_id")
            if skill_id is None:
                continue
            skill_data = row.get("skillData") or []
            first_data = skill_data[0] if skill_data and isinstance(skill_data[0], dict) else {}
            by_skill_id[str(skill_id)] = {
                "source_file": str(path.resolve()),
                "skill_tier": row.get("skillTier"),
                "skill_data_count": len(skill_data) if isinstance(skill_data, list) else 0,
                "attribute_type": first_data.get("attributeType"),
                "attack_type": first_data.get("atkType"),
                "defense_type": first_data.get("defType"),
                "base_power": first_data.get("defaultValue"),
                "level_correction": first_data.get("skillLevelCorrection"),
                "target_num": first_data.get("targetNum"),
                "coin_count": len(first_data.get("coinList") or []),
            }

    return {
        "count": len(by_skill_id),
        "source_files": files,
        "by_skill_id": by_skill_id,
    }


def wiki_identity_name_from_folder(folder: Path) -> str:
    name = folder.name
    suffix = " - Limbus Company Wiki_files"
    if name.endswith(suffix):
        name = name[: -len(suffix)]
    return name.replace("__", ":")


def build_wiki_folder_map(wiki_root: Path) -> dict[str, Path]:
    folders: dict[str, Path] = {}
    if not wiki_root.exists():
        return folders
    for folder in wiki_root.rglob("*_files"):
        if folder.is_dir():
            folders[norm(wiki_identity_name_from_folder(folder))] = folder
    return folders


def slot_rank(slot: str | None) -> str | None:
    match = re.search(r"(\d+)$", slot or "")
    return match.group(1) if match else None


def find_first(files: list[Path], *needles: str, reject: tuple[str, ...] = ()) -> Path | None:
    normalized = [(path, norm(path.name)) for path in files]
    wanted = [norm(needle) for needle in needles if norm(needle)]
    rejected = [norm(item) for item in reject if norm(item)]
    for path, key in normalized:
        key_compact = key.replace(" ", "")
        if wanted and not all(needle in key or needle.replace(" ", "") in key_compact for needle in wanted):
            continue
        if rejected and any(item in key for item in rejected):
            continue
        return path
    return None

def find_skill_art(files: list[Path], skill_name: str, sinner: str | None) -> Path | None:
    if not skill_name:
        return None
    rejects = ("def icon", "profile", "sprite", "animation", "uptied", "acquisition")
    candidates = [
        find_first(files, skill_name, sinner or "", "Icon", reject=rejects),
        find_first(files, skill_name, sinner or "", "Skill", reject=rejects),
        find_first(files, skill_name, sinner or "", reject=rejects),
        find_first(files, skill_name, "Icon", reject=rejects),
        find_first(files, skill_name, "Skill", reject=rejects),
        find_first(files, skill_name, reject=rejects),
    ]
    return next((path for path in candidates if path), None)



def skill_art_candidates(files: list[Path], sinner: str | None) -> list[Path]:
    reject_terms = ["def icon", "profile", "sprite", "animation", "uptied", "acquisition", "teaser"]
    result: list[Path] = []
    for path in files:
        key = norm(path.name)
        if not key.startswith("74px"):
            continue
        if sinner and norm(sinner) not in key:
            continue
        if any(term in key for term in reject_terms):
            continue
        if "icon" not in key and "skill" not in key:
            continue
        result.append(path)
    return sorted(result, key=lambda path: path.name)


def fallback_skill_art_by_slot(candidates: list[Path], slot: str | None) -> Path | None:
    rank = slot_rank(slot)
    if rank:
        index = int(rank) - 1
        if 0 <= index < len(candidates):
            return candidates[index]
    if slot and "special" in slot and candidates:
        return candidates[-1]
    return None

def build_wiki_identity_assets(data_dir: Path, wiki_root: Path, base: Path | None) -> dict[str, Any]:
    identity_dir = data_dir / "identities" / "en"
    folder_map = build_wiki_folder_map(wiki_root)
    by_identity_id: dict[str, dict[str, Any]] = {}
    skill_layer_count = 0
    missing_folders: list[str] = []

    for identity_file in sorted(identity_dir.glob("*.json")) if identity_dir.exists() else []:
        identity_data = load_json(identity_file)
        identity = identity_data.get("identity") or {}
        identity_id = str(identity.get("id") or "")
        english_name = identity.get("english_name") or identity_file.stem
        folder = folder_map.get(norm(english_name))
        if not folder:
            missing_folders.append(english_name)
            continue

        images = scan_images(folder)
        by_skill: dict[str, dict[str, Any]] = {}
        art_candidates = skill_art_candidates(images, identity.get("sinner"))
        for skill in identity_data.get("skills") or []:
            skill_id = str(skill.get("source_skill_text_id") or "")
            if not skill_id or skill_id in by_skill:
                continue
            affinity = skill.get("affinity")
            rank = slot_rank(skill.get("slot"))
            skill_name = ((skill.get("name") or {}).get("en") or "").strip()
            sinner = identity.get("sinner")

            bg = find_first(images, f"{affinity}{rank}BG") if affinity and rank else None
            rim = find_first(images, f"{affinity}{rank}") if affinity and rank else None
            art = find_skill_art(images, skill_name, sinner) or fallback_skill_art_by_slot(art_candidates, skill.get("slot"))

            layers: dict[str, Any] = {}
            if bg:
                layers["background"] = image_record(bg, "wiki_identity_html", base)
            if art:
                layers["art"] = image_record(art, "wiki_identity_html", base)
            if rim:
                layers["rim"] = image_record(rim, "wiki_identity_html", base)
            if layers:
                skill_layer_count += 1

            by_skill[skill_id] = {
                "skill_name": skill_name,
                "slot": skill.get("slot"),
                "affinity": affinity,
                "rank": rank,
                "layers": layers,
            }

        by_identity_id[identity_id] = {
            "english_name": english_name,
            "folder": str(folder.resolve()),
            "skills": by_skill,
        }

    return {
        "count": len(by_identity_id),
        "skill_layer_count": skill_layer_count,
        "missing_identity_folders": missing_folders,
        "by_identity_id": by_identity_id,
    }


def collect_database_tokens(data_dir: Path) -> dict[str, Any]:
    token_re = re.compile(r"\[([A-Za-z0-9_]+)\]")
    tokens: dict[str, int] = {}
    for folder in [data_dir / "identities" / "en", data_dir / "identities" / "locales" / "th"]:
        if not folder.exists():
            continue
        for path in folder.glob("*.json"):
            text = path.read_text(encoding="utf-8-sig")
            for token in token_re.findall(text):
                tokens[token] = tokens.get(token, 0) + 1
    return {
        "count": len(tokens),
        "tokens": dict(sorted(tokens.items(), key=lambda item: (-item[1], item[0]))),
    }


def summarize_matches(tokens: dict[str, Any], keyword_assets: dict[str, Any]) -> dict[str, Any]:
    lookup = keyword_assets.get("lookup") or {}
    direct = keyword_assets.get("by_token") or {}
    matched: dict[str, str] = {}
    missing: list[str] = []
    for token in tokens.get("tokens") or {}:
        if token in direct:
            matched[token] = direct[token]["path"]
        elif norm(token) in lookup and lookup[norm(token)]:
            matched[token] = lookup[norm(token)][0]["path"]
        else:
            missing.append(token)
    return {
        "matched_count": len(matched),
        "missing_count": len(missing),
        "matched": matched,
        "missing": missing,
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    asset_root = args.assets.resolve()
    data_dir = args.data.resolve()
    wiki_root = args.wiki.resolve()
    base = args.relative_to.resolve() if args.relative_to else None

    keyword_assets = build_keyword_assets(asset_root, base)
    database_tokens = collect_database_tokens(data_dir)
    return {
        "schema_version": 1,
        "kind": "limbus_asset_manifest",
        "sources": {
            "limbus_images": str(asset_root),
            "wiki_identity_html": str(wiki_root),
            "data": str(data_dir),
        },
        "keywords": keyword_assets,
        "skills_metadata": build_limbus_skill_metadata(asset_root),
        "wiki_identity_layers": build_wiki_identity_assets(data_dir, wiki_root, base),
        "database_tokens": database_tokens,
        "database_token_asset_matches": summarize_matches(database_tokens, keyword_assets),
        "rendering_notes": {
            "skill_icon_layer_order": ["background", "art", "rim"],
            "token_rendering": "Prefer keywords.by_token or database_token_asset_matches. Use wiki images only as fallback for old [img:Name.png] text.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Limbus asset manifest for bot and website rendering.")
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSET_ROOT, help="Limbus Images asset directory.")
    parser.add_argument("--wiki", type=Path, default=ROOT / "inputs" / "wiki_identity_html", help="Saved wiki HTML folder.")
    parser.add_argument("--data", type=Path, default=ROOT / "data", help="Exported database root.")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "assets" / "asset_manifest.json", help="Output manifest JSON.")
    parser.add_argument("--relative-to", type=Path, default=None, help="Also store paths relative to this directory when possible.")
    args = parser.parse_args()

    manifest = build_manifest(args)
    write_json(args.out, manifest)

    print("Limbus asset manifest")
    print(f"  Output: {args.out}")
    print(f"  Keyword images: {manifest['keywords']['count']}")
    print(f"  Skill metadata rows: {manifest['skills_metadata']['count']}")
    print(f"  Wiki identity folders: {manifest['wiki_identity_layers']['count']}")
    print(f"  Wiki skill layer records: {manifest['wiki_identity_layers']['skill_layer_count']}")
    print(f"  Database tokens: {manifest['database_tokens']['count']}")
    print(f"  Token icon matches: {manifest['database_token_asset_matches']['matched_count']}")
    print(f"  Token icon missing: {manifest['database_token_asset_matches']['missing_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())








