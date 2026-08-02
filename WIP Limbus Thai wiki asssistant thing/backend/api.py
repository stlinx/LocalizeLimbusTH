from __future__ import annotations

import json
import mimetypes
import re
import sys
from datetime import datetime, timezone
from functools import lru_cache
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .services import BOSS_REVIEWED_DIR, DEFAULT_DB, get_boss_profile, get_boss_turn_intent, get_identity_profile, get_panic_info, get_status_effect, list_status_effects, search_bosses, search_identity


ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = ROOT / "work"
WEB_ROOT = ROOT / "web"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

if str(WORK_DIR) not in sys.path:
    sys.path.insert(0, str(WORK_DIR))

from build_identity_profile import build_payload  # noqa: E402
from render_identity_card import coin_effect_icons, render_identity_card, skill_icon  # noqa: E402
from simulator.service import simulate_clash_payload  # noqa: E402
from simulator.damage import simulate_damage_payload  # noqa: E402


def response_json(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: Any) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status.value)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def response_file(handler: BaseHTTPRequestHandler, path: Path, cache_control: str = "public, max-age=3600") -> None:
    if not path.exists() or not path.is_file():
        response_json(handler, HTTPStatus.NOT_FOUND, {"error": "asset_not_found"})
        return
    body = path.read_bytes()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    handler.send_response(HTTPStatus.OK.value)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Cache-Control", cache_control)
    handler.end_headers()
    handler.wfile.write(body)


def response_static(handler: BaseHTTPRequestHandler, request_path: str) -> bool:
    route = request_path.rstrip("/") or "/"
    if route == "/":
        relative = Path("index.html")
    else:
        relative = Path(unquote(route.lstrip("/")))
    target = (WEB_ROOT / relative).resolve()
    try:
        target.relative_to(WEB_ROOT.resolve())
    except ValueError:
        response_json(handler, HTTPStatus.FORBIDDEN, {"error": "forbidden"})
        return True
    if not target.exists() or not target.is_file():
        return False
    response_file(handler, target, "no-cache")
    return True


def first_param(params: dict[str, list[str]], name: str, default: str = "") -> str:
    values = params.get(name) or []
    return values[0] if values else default


def int_param(params: dict[str, list[str]], name: str, default: int) -> int:
    value = first_param(params, name, str(default))
    try:
        return int(value)
    except ValueError:
        return default


def error_payload(exc: Exception) -> dict[str, str]:
    return {"error": exc.__class__.__name__, "message": str(exc)}


@lru_cache(maxsize=256)
def profile_payload(identity_id: str, db_path: Path, uptie: int, lang: str) -> dict[str, Any]:
    profile = get_identity_profile(identity_id, db_path, uptie, lang)
    return build_payload(profile["identity"]["english_name"], ROOT / "data", uptie, lang)


def cache_path(*parts: str) -> Path:
    path = ROOT / "outputs" / "web_assets"
    path.mkdir(parents=True, exist_ok=True)
    return path.joinpath(*parts)



def boss_source_asset_dir(boss: dict[str, Any]) -> Path | None:
    source_html = boss.get("source_html")
    if not source_html:
        return None
    html_path = Path(source_html)
    candidates = [html_path.with_name(html_path.stem + "_files"), html_path.parent / (html_path.stem.replace(":", "_") + "_files")]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None

@lru_cache(maxsize=512)
def boss_skill_layers(boss_id: str, skill_id: str) -> dict[str, dict[str, str]]:
    boss = get_boss_profile(boss_id)
    folder = boss_source_asset_dir(boss)
    skill = next((item for item in boss.get("skills") or [] if str(item.get("skill_id")) == skill_id), None)
    if not folder or not skill:
        return {}
    art_path = Path(skill.get("asset_path") or "")
    if not art_path.exists():
        return {}
    layers: dict[str, dict[str, str]] = {"art": {"absolute_path": str(art_path)}}
    source_html = boss.get("source_html")
    if not source_html:
        return layers
    html_path = Path(source_html)
    if not html_path.exists():
        return layers
    try:
        html = html_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return layers
    art_name = art_path.name
    index = html.find(art_name)
    if index < 0:
        index = html.find(art_name.replace("_", " "))
    if index < 0:
        return layers
    window = html[max(0, index - 1400): index + 1400]
    image_names = re.findall(r'(?:src|alt)="[^"]*?(?:112px-)?([A-Za-z]+\dBG?\.png)"', window)
    bg_name = None
    rim_name = None
    for name in image_names:
        if name.endswith("BG.png") and not bg_name:
            bg_name = name
        elif not name.endswith("BG.png") and not rim_name:
            rim_name = name
    def find_layer(name: str | None) -> Path | None:
        if not name:
            return None
        candidates = [folder / name, folder / f"112px-{name}"]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        matches = list(folder.glob(f"*{name}"))
        return matches[0] if matches else None
    bg = find_layer(bg_name)
    rim = find_layer(rim_name)
    if bg:
        layers["background"] = {"absolute_path": str(bg)}
    if rim:
        layers["rim"] = {"absolute_path": str(rim)}
    return layers


def boss_skill_icon_image(boss_id: str, skill_id: str, size: int = 160):
    boss = get_boss_profile(boss_id)
    skill = next((item for item in boss.get("skills") or [] if str(item.get("skill_id")) == skill_id), None)
    if not skill:
        return None
    composed_skill = dict(skill)
    composed_skill["assets"] = {"layers": boss_skill_layers(boss_id, skill_id)}
    return skill_icon(composed_skill, size)

def boss_asset_path(boss_id: str, group: str, key: str) -> Path | None:
    boss = get_boss_profile(boss_id)
    if group == "image":
        asset = (boss.get("assets") or {}).get(key)
        return Path(asset) if asset else None
    if group == "skill":
        for skill in boss.get("skills") or []:
            if str(skill.get("skill_id")) == key and skill.get("asset_path"):
                return Path(skill["asset_path"])
    if group == "status":
        try:
            index = int(key)
        except ValueError:
            return None
        statuses = boss.get("unique_statuses") or []
        if 0 <= index < len(statuses):
            asset = statuses[index].get("icon_path")
            return Path(asset) if asset else None
    if group == "coin":
        coin_name = re.sub(r"[^0-9A-Za-z_-]+", "", key)
        if not re.fullmatch(r"CoinEffect\d+", coin_name):
            return None
        asset_dir = boss_source_asset_dir(boss)
        if asset_dir:
            for candidate in (asset_dir / f"25px-{coin_name}.png", asset_dir / f"{coin_name}.png"):
                if candidate.exists():
                    return candidate
            matches = sorted(asset_dir.glob(f"*{coin_name}*.png"))
            if matches:
                return matches[0]
    return None


def safe_file_stem(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z._-]+", "_", value).strip("_") or "boss"


def save_reviewed_boss(payload: dict[str, Any]) -> dict[str, Any]:
    boss = payload.get("boss")
    if not isinstance(boss, dict):
        raise ValueError("boss must be an object")
    boss_id = str(payload.get("boss_id") or boss.get("boss_id") or "").strip()
    if not boss_id:
        raise ValueError("boss_id is required")
    boss["boss_id"] = boss_id
    review = dict(boss.get("review") or {})
    review["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    review["reviewed_by"] = str(payload.get("reviewed_by") or review.get("reviewed_by") or "local_admin")
    review["sections"] = payload.get("sections") if isinstance(payload.get("sections"), dict) else review.get("sections", {})
    boss["review"] = review
    boss["review_status"] = str(payload.get("review_status") or boss.get("review_status") or "reviewed_local")
    boss["source"] = "reviewed_fixture"
    boss["reviewed_override"] = True
    BOSS_REVIEWED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = BOSS_REVIEWED_DIR / f"{safe_file_stem(boss_id)}.json"
    tmp_path = out_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(boss, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(out_path)
    return {"ok": True, "boss_id": boss_id, "path": str(out_path), "boss": boss}


class LimbusApiHandler(BaseHTTPRequestHandler):
    server_version = "LimbusAssistantAPI/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT.value)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def read_json_body(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length") or "0"
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("Bad Content-Length") from exc
        if length <= 0:
            return {}
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON body: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)
        db_path = Path(first_param(params, "db", str(DEFAULT_DB)))

        try:
            payload = self.read_json_body()
            if path == "/simulate/clash":
                response_json(self, HTTPStatus.OK, simulate_clash_payload(payload, db_path))
                return
            if path == "/simulate/damage":
                response_json(self, HTTPStatus.OK, simulate_damage_payload(payload))
                return
            if path == "/bosses/review":
                response_json(self, HTTPStatus.OK, save_reviewed_boss(payload))
                return
            response_json(self, HTTPStatus.NOT_FOUND, {"error": "not_found", "path": path})
        except ValueError as exc:
            response_json(self, HTTPStatus.BAD_REQUEST, error_payload(exc))
        except Exception as exc:
            response_json(self, HTTPStatus.INTERNAL_SERVER_ERROR, error_payload(exc))
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)
        db_path = Path(first_param(params, "db", str(DEFAULT_DB)))

        try:
            if path == "/health":
                response_json(
                    self,
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "service": "limbus-assistant-api",
                        "db": str(db_path),
                        "db_exists": db_path.exists(),
                    },
                )
                return

            if path == "/identities/search":
                query = first_param(params, "q")
                if not query:
                    response_json(self, HTTPStatus.BAD_REQUEST, {"error": "missing_query", "param": "q"})
                    return
                limit = max(1, min(int_param(params, "limit", 8), 25))
                response_json(self, HTTPStatus.OK, {"query": query, "items": search_identity(query, db_path, limit)})
                return

            if path.startswith("/identities/"):
                identity_id = unquote(path.removeprefix("/identities/"))
                uptie = int_param(params, "uptie", 4)
                lang = first_param(params, "lang", "th")
                profile = get_identity_profile(identity_id, db_path, uptie, lang)
                payload = profile_payload(identity_id, db_path, uptie, lang)
                profile["token_assets"] = payload.get("token_assets") or {}
                profile["images"] = payload.get("images") or {}
                response_json(self, HTTPStatus.OK, profile)
                return

            if path == "/statuses":
                lang = first_param(params, "lang", "th")
                limit = max(1, min(int_param(params, "limit", 1000), 2000))
                response_json(self, HTTPStatus.OK, list_status_effects(db_path, lang, limit))
                return
            if path == "/status/search":
                query = first_param(params, "q")
                if not query:
                    response_json(self, HTTPStatus.BAD_REQUEST, {"error": "missing_query", "param": "q"})
                    return
                lang = first_param(params, "lang", "th")
                response_json(self, HTTPStatus.OK, {"query": query, "item": get_status_effect(query, db_path, lang)})
                return

            if path == "/panic/search":
                query = first_param(params, "q")
                if not query:
                    response_json(self, HTTPStatus.BAD_REQUEST, {"error": "missing_query", "param": "q"})
                    return
                lang = first_param(params, "lang", "th")
                response_json(self, HTTPStatus.OK, {"query": query, "item": get_panic_info(query, db_path, lang)})
                return

            if path == "/bosses/search":
                query = first_param(params, "q")
                limit = max(1, min(int_param(params, "limit", 8), 25))
                response_json(self, HTTPStatus.OK, search_bosses(query, limit))
                return

            if path.startswith("/bosses/") and path.endswith("/intent"):
                boss_id = unquote(path.removeprefix("/bosses/").removesuffix("/intent"))
                turn = int_param(params, "turn", 1)
                hp_percent = float(first_param(params, "hp_percent", "100") or "100")
                response_json(self, HTTPStatus.OK, get_boss_turn_intent(boss_id, turn, hp_percent))
                return

            if path.startswith("/bosses/"):
                boss_id = unquote(path.removeprefix("/bosses/"))
                response_json(self, HTTPStatus.OK, get_boss_profile(boss_id))
                return
            if path.startswith("/assets/boss-skill-icon/"):
                rest = unquote(path.removeprefix("/assets/boss-skill-icon/"))
                parts = rest.split("/", 1)
                if len(parts) != 2:
                    response_json(self, HTTPStatus.BAD_REQUEST, {"error": "bad_boss_skill_icon_path"})
                    return
                boss_id, skill_id = parts
                out_path = cache_path(f"boss_{boss_id}_{skill_id}.png")
                if not out_path.exists():
                    image = boss_skill_icon_image(boss_id, skill_id, 160)
                    if image is None:
                        response_json(self, HTTPStatus.NOT_FOUND, {"error": "boss_skill_not_found", "skill": skill_id})
                        return
                    image.save(out_path)
                response_file(self, out_path)
                return

            if path.startswith("/assets/boss/"):
                rest = unquote(path.removeprefix("/assets/boss/"))
                parts = rest.split("/", 2)
                if len(parts) != 3:
                    response_json(self, HTTPStatus.BAD_REQUEST, {"error": "bad_boss_asset_path"})
                    return
                boss_id, group, key = parts
                asset_path = boss_asset_path(boss_id, group, key)
                if not asset_path:
                    response_json(self, HTTPStatus.NOT_FOUND, {"error": "boss_asset_not_found"})
                    return
                response_file(self, asset_path)
                return

            if path.startswith("/assets/status/"):
                status_key = unquote(path.removeprefix("/assets/status/"))
                status = get_status_effect(status_key, db_path, "en")
                response_file(self, Path(status.get("icon_path") or ""))
                return

            if path.startswith("/assets/token/"):
                rest = unquote(path.removeprefix("/assets/token/"))
                parts = rest.split("/", 1)
                if len(parts) != 2:
                    response_json(self, HTTPStatus.BAD_REQUEST, {"error": "bad_token_path"})
                    return
                identity_id, token = parts
                uptie = int_param(params, "uptie", 4)
                lang = first_param(params, "lang", "th")
                payload = profile_payload(identity_id, db_path, uptie, lang)
                asset = (payload.get("token_assets") or {}).get(token) or {}
                response_file(self, Path(asset.get("path") or ""))
                return

            if path.startswith("/assets/identity-image/"):
                identity_id = unquote(path.removeprefix("/assets/identity-image/"))
                uptie = int_param(params, "uptie", 4)
                lang = first_param(params, "lang", "th")
                payload = profile_payload(identity_id, db_path, uptie, lang)
                images = payload.get("images") or {}
                for key in ("profile", "thumbnail", "idle_sprite", "acquisition", "moving_sprite"):
                    if images.get(key):
                        response_file(self, Path(images[key]))
                        return
                response_json(self, HTTPStatus.NOT_FOUND, {"error": "identity_image_not_found"})
                return

            if path.startswith("/assets/identity-sprite/"):
                identity_id = unquote(path.removeprefix("/assets/identity-sprite/"))
                uptie = int_param(params, "uptie", 4)
                lang = first_param(params, "lang", "th")
                payload = profile_payload(identity_id, db_path, uptie, lang)
                images = payload.get("images") or {}
                for key in ("idle_sprite", "moving_sprite", "thumbnail", "profile", "acquisition"):
                    if images.get(key):
                        response_file(self, Path(images[key]))
                        return
                response_json(self, HTTPStatus.NOT_FOUND, {"error": "identity_sprite_not_found"})
                return

            if path.startswith("/assets/skill-icon/"):
                rest = unquote(path.removeprefix("/assets/skill-icon/"))
                parts = rest.split("/", 1)
                if len(parts) != 2:
                    response_json(self, HTTPStatus.BAD_REQUEST, {"error": "bad_skill_icon_path"})
                    return
                identity_id, skill_key = parts
                uptie = int_param(params, "uptie", 4)
                lang = first_param(params, "lang", "th")
                payload = profile_payload(identity_id, db_path, uptie, lang)
                skills = payload.get("skills") or []
                skill = next((item for item in skills if str(item.get("source_skill_text_id")) == skill_key), None)
                if not skill:
                    skill = next((item for item in skills if str(item.get("slot")) == skill_key), None)
                if not skill:
                    response_json(self, HTTPStatus.NOT_FOUND, {"error": "skill_not_found", "skill": skill_key})
                    return
                out_path = cache_path(f"{identity_id}_{skill_key}_UT{uptie}.png")
                if not out_path.exists():
                    skill_icon(skill, 160).save(out_path)
                response_file(self, out_path)
                return

            if path.startswith("/assets/coin-effect/"):
                rest = unquote(path.removeprefix("/assets/coin-effect/"))
                parts = rest.split("/", 1)
                if len(parts) != 2:
                    response_json(self, HTTPStatus.BAD_REQUEST, {"error": "bad_coin_effect_path"})
                    return
                identity_id, coin_index_raw = parts
                try:
                    coin_index = int(coin_index_raw)
                except ValueError:
                    response_json(self, HTTPStatus.BAD_REQUEST, {"error": "bad_coin_index"})
                    return
                uptie = int_param(params, "uptie", 4)
                lang = first_param(params, "lang", "th")
                payload = profile_payload(identity_id, db_path, uptie, lang)
                icons = coin_effect_icons(payload)
                response_file(self, Path(icons.get(coin_index) or ""))
                return

            if path.startswith("/assets/identity-card/"):
                identity_id = unquote(path.removeprefix("/assets/identity-card/"))
                uptie = int_param(params, "uptie", 4)
                lang = first_param(params, "lang", "th")
                profile = get_identity_profile(identity_id, db_path, uptie, lang)
                query = profile["identity"]["english_name"]
                safe_name = re.sub(r"[^0-9A-Za-z._-]+", "_", query).strip("_") or "identity"
                cached_card = ROOT / "outputs" / "discord_cards" / f"{safe_name}_UT{uptie}_{lang}.png"
                renderer_path = WORK_DIR / "render_identity_card.py"
                card_fresh = cached_card.exists() and cached_card.stat().st_mtime >= renderer_path.stat().st_mtime
                card_path = cached_card if card_fresh else render_identity_card(query, ROOT / "data", uptie, lang)
                response_file(self, card_path)
                return

            if response_static(self, parsed.path):
                return

            response_json(self, HTTPStatus.NOT_FOUND, {"error": "not_found", "path": path})
        except ValueError as exc:
            response_json(self, HTTPStatus.NOT_FOUND, error_payload(exc))
        except Exception as exc:
            response_json(self, HTTPStatus.INTERNAL_SERVER_ERROR, error_payload(exc))


def run(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    server = ThreadingHTTPServer((host, port), LimbusApiHandler)
    print(f"Limbus API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the local Limbus assistant API.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    run(args.host, args.port)


if __name__ == "__main__":
    main()


