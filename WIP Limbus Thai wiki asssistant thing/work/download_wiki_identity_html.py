from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urljoin, urlparse
from urllib.request import Request, urlopen


API_URL = "https://limbuscompany.wiki.gg/api.php"
WIKI_BASE = "https://limbuscompany.wiki.gg"
DEFAULT_OUT = Path("inputs/wiki_identity_html")
USER_AGENT = "LimbusAssistantDataImporter/0.1 (local personal database build)"


class ImageCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            return
        attrs_dict = dict(attrs)
        src = attrs_dict.get("src")
        if src:
            self.images.append((src, attrs_dict.get("alt")))


def request_json(url: str) -> dict[str, Any]:
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def request_bytes(url: str) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=60) as response:
        return response.read()


def safe_filename(value: str, suffix: str = "") -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value)
    value = re.sub(r"\s+", " ", value).strip().strip(".")
    return f"{value}{suffix}" if suffix and not value.endswith(suffix) else value


def api_url(params: dict[str, str | int]) -> str:
    return API_URL + "?" + "&".join(f"{key}={quote(str(value))}" for key, value in params.items())


def category_members(category: str, limit: int | None = None) -> list[str]:
    titles: list[str] = []
    params: dict[str, str | int] = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category if category.startswith("Category:") else f"Category:{category}",
        "cmnamespace": 0,
        "cmlimit": "max",
        "format": "json",
    }
    while True:
        data = request_json(api_url(params))
        titles.extend(member["title"] for member in data.get("query", {}).get("categorymembers", []))
        if limit and len(titles) >= limit:
            return titles[:limit]
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            return titles
        params["cmcontinue"] = cont


def page_html(title: str) -> str:
    return request_bytes(f"{WIKI_BASE}/wiki/{quote(title.replace(' ', '_'))}").decode("utf-8", errors="replace")


def image_filename(src: str, alt: str | None) -> str:
    path_name = Path(unquote(urlparse(src).path)).name
    if path_name:
        return safe_filename(path_name)
    if alt:
        return safe_filename(alt)
    return "image.png"


def collect_images(html: str) -> list[tuple[str, str | None]]:
    parser = ImageCollector()
    parser.feed(html)
    seen: set[str] = set()
    images: list[tuple[str, str | None]] = []
    for src, alt in parser.images:
        url = urljoin(WIKI_BASE, src)
        if url in seen:
            continue
        seen.add(url)
        images.append((url, alt))
    return images


def download_image(url: str, alt: str | None, files_dir: Path, force: bool) -> str | None:
    filename = image_filename(url, alt)
    path = files_dir / filename
    if path.exists() and not force:
        return None
    path.write_bytes(request_bytes(url))
    return filename


def download_images(images: list[tuple[str, str | None]], files_dir: Path, force: bool, image_workers: int) -> None:
    if image_workers <= 1:
        for index, (url, alt) in enumerate(images, start=1):
            try:
                download_image(url, alt, files_dir, force)
            except Exception as exc:
                print(f"  image failed [{index}]: {image_filename(url, alt)} ({exc})")
        return

    with ThreadPoolExecutor(max_workers=image_workers) as executor:
        futures = {
            executor.submit(download_image, url, alt, files_dir, force): (index, url, alt)
            for index, (url, alt) in enumerate(images, start=1)
        }
        for future in as_completed(futures):
            index, url, alt = futures[future]
            try:
                future.result()
            except Exception as exc:
                print(f"  image failed [{index}]: {image_filename(url, alt)} ({exc})")


def download_identity(title: str, out_dir: Path, delay: float, force: bool, image_workers: int) -> Path:
    html_path = out_dir / safe_filename(title, " - Limbus Company Wiki.html")
    files_dir = html_path.with_name(f"{html_path.stem}_files")
    if html_path.exists() and not force:
        print(f"skip html: {html_path.name}")
        return html_path

    print(f"download page: {title}")
    html = page_html(title)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    files_dir.mkdir(parents=True, exist_ok=True)
    download_images(collect_images(html), files_dir, force, image_workers)
    if delay:
        time.sleep(delay)
    return html_path


def read_titles_file(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-download Limbus wiki Identity HTML pages and image folders.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--category", default="Identities")
    parser.add_argument("--titles-file", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--workers", type=int, default=1, help="Number of identity pages to download in parallel.")
    parser.add_argument("--image-workers", type=int, default=4, help="Number of images per page to download in parallel.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    titles = read_titles_file(args.titles_file) if args.titles_file else category_members(args.category, limit=args.limit)
    if not titles:
        raise SystemExit("No identity titles found.")

    print(
        f"Downloading {len(titles)} page(s) into {args.out} "
        f"with {args.workers} page worker(s), {args.image_workers} image worker(s)"
    )
    if args.workers <= 1:
        for title in titles:
            download_identity(title, args.out, args.delay, args.force, args.image_workers)
        return

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(download_identity, title, args.out, args.delay, args.force, args.image_workers): title
            for title in titles
        }
        for future in as_completed(futures):
            title = futures[future]
            try:
                future.result()
            except Exception as exc:
                print(f"page failed: {title} ({exc})")


if __name__ == "__main__":
    main()
