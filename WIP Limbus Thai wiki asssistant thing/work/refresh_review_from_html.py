from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("$ " + " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the localized review HTML from a folder of saved/downloaded wiki Identity HTML files.")
    parser.add_argument("html_folder", nargs="?", type=Path, default=Path("inputs/wiki_identity_html"))
    parser.add_argument("--imports", type=Path, default=Path("outputs/wiki_identity_imports.json"))
    parser.add_argument("--summary", type=Path, default=Path("outputs/wiki_identity_imports_summary.md"))
    parser.add_argument("--review-json", type=Path, default=Path("outputs/wiki_identity_localized_review.json"))
    parser.add_argument("--review-html", type=Path, default=Path("outputs/wiki_identity_localized_review.html"))
    args = parser.parse_args()

    html_folder = args.html_folder
    if not html_folder.is_absolute():
        html_folder = ROOT / html_folder
    if not html_folder.exists():
        raise SystemExit(f"HTML folder does not exist: {html_folder}")

    run([
        sys.executable,
        "work/import_wiki_html_identities.py",
        str(html_folder),
        "--out",
        str(args.imports),
        "--summary",
        str(args.summary),
    ])
    run([
        sys.executable,
        "work/link_wiki_import_to_localization.py",
        "--wiki",
        str(args.imports),
        "--out",
        str(args.review_json),
        "--html",
        str(args.review_html),
    ])
    print(f"Review updated: {ROOT / args.review_html}")


if __name__ == "__main__":
    main()
