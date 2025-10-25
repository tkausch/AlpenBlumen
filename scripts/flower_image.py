#!/usr/bin/env python3
"""Download Anton Hartinger alpine flora plates from Wikimedia Commons.

Given one or more Latin species names, this script looks up the corresponding
“Atlas der Alpenflora …” file on Wikimedia Commons, downloads the image, and
places it into the Xcode asset catalog (`Assets.xcassets/<Latin>.imageset/`).

Usage examples:
    python scripts/flower_image.py "Androsace alpina"
    python scripts/flower_image.py --assets-dir AlpenBlumen/assets/Assets.xcassets Gentiana verna

Use --force to replace an existing image in the target imageset.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib import parse, request


COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "AlpenBlumenImageFetcher/1.0 (+https://github.com/)"
DEFAULT_TEMPLATE = "Atlas der Alpenflora {latin}.jpg"


class CommonsError(RuntimeError):
    """Raised when Wikimedia Commons returns an error."""


def fetch_json(params: Dict[str, str]) -> Dict:
    query = parse.urlencode(params)
    url = f"{COMMONS_API}?{query}"
    req = request.Request(url, headers={"User-Agent": USER_AGENT})
    with request.urlopen(req) as resp:  # nosec - trusted Wikimedia endpoint
        return json.load(resp)


def normalize_title(title: str) -> str:
    return title.replace(" ", "_")


def build_candidate_titles(latin_name: str) -> List[str]:
    variants = set()
    variants.add(DEFAULT_TEMPLATE.format(latin=latin_name))
    variants.add(DEFAULT_TEMPLATE.format(latin=normalize_title(latin_name)))
    return [f"File:{variant}" for variant in variants]


def query_image_info(title: str) -> Optional[Dict]:
    data = fetch_json(
        {
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "format": "json",
            "formatversion": "2",
        }
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    page = pages[0]
    if page.get("missing"):
        return None
    info = page.get("imageinfo", [])
    return info[0] if info else None


def search_commons(latin_name: str) -> Iterable[str]:
    query = f'intitle:"Atlas der Alpenflora" {latin_name}'
    data = fetch_json(
        {
            "action": "query",
            "list": "search",
            "srnamespace": "6",  # File namespace
            "srlimit": "10",
            "srsearch": query,
            "format": "json",
            "formatversion": "2",
        }
    )
    for hit in data.get("query", {}).get("search", []):
        title = hit.get("title")
        if title:
            yield title


def resolve_image(latin_name: str) -> Optional[Dict]:
    for candidate in build_candidate_titles(latin_name):
        info = query_image_info(candidate)
        if info:
            return info
    for title in search_commons(latin_name):
        info = query_image_info(title)
        if info:
            return info
    return None


def write_contents_json(imageset_dir: Path, filename: str, attribution: str) -> None:
    contents = {
        "images": [
            {
                "filename": filename,
                "idiom": "universal",
            }
        ],
        "info": {
            "author": attribution or "Wikimedia Commons",
            "version": 1,
        },
    }
    (imageset_dir / "Contents.json").write_text(json.dumps(contents, indent=2) + "\n", encoding="utf-8")


def download_image(url: str, destination: Path) -> None:
    req = request.Request(url, headers={"User-Agent": USER_AGENT})
    with request.urlopen(req) as resp, destination.open("wb") as output:
        output.write(resp.read())


def fetch_attribution(meta: Dict) -> str:
    extmeta = meta.get("extmetadata", {}) if isinstance(meta, dict) else {}
    artist = extmeta.get("Artist", {}).get("value", "")
    license_name = extmeta.get("LicenseShortName", {}).get("value", "")
    credit = extmeta.get("Credit", {}).get("value", "")
    # Strip HTML tags for readability.
    def strip_tags(text: str) -> str:
        inside = False
        result = []
        for char in text:
            if char == "<":
                inside = True
            elif char == ">":
                inside = False
            elif not inside:
                result.append(char)
        return "".join(result).strip()

    parts = [strip_tags(value) for value in (artist, credit, license_name) if value]
    return " | ".join(parts)


def ensure_imageset_dir(assets_dir: Path, latin_name: str) -> Path:
    imageset_dir = assets_dir / f"{latin_name}.imageset"
    imageset_dir.mkdir(parents=True, exist_ok=True)
    return imageset_dir


def save_image(latin_name: str, info: Dict, assets_dir: Path, force: bool) -> None:
    url = info.get("url")
    if not url:
        raise CommonsError("Image info missing download URL.")
    suffix = Path(parse.urlparse(url).path).suffix or ".jpg"
    filename = f"{latin_name}{suffix}"
    imageset_dir = ensure_imageset_dir(assets_dir, latin_name)
    target_path = imageset_dir / filename
    if target_path.exists() and not force:
        print(f"[skip] {latin_name}: image already exists (use --force to overwrite)")
        return
    download_image(url, target_path)
    attribution = fetch_attribution(info)
    write_contents_json(imageset_dir, filename, attribution)
    print(f"[ok] {latin_name}: saved {filename}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Anton Hartinger plates from Wikimedia Commons.")
    parser.add_argument("latin_names", nargs="+", help="Latin names to fetch, e.g. 'Androsace alpina'")
    parser.add_argument(
        "--assets-dir",
        default=Path("AlpenBlumen/assets/Assets.xcassets"),
        type=Path,
        help="Path to the Xcode asset catalog",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing images")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    assets_dir: Path = args.assets_dir
    if not assets_dir.exists():
        print(f"Asset directory not found: {assets_dir}", file=sys.stderr)
        return 1

    exit_code = 0
    for latin_name in args.latin_names:
        latin_name = latin_name.strip()
        if not latin_name:
            continue
        try:
            info = resolve_image(latin_name)
            if not info:
                print(f"[warn] {latin_name}: no matching Commons file found", file=sys.stderr)
                exit_code = 2
                continue
            save_image(latin_name, info, assets_dir, args.force)
        except CommonsError as exc:
            print(f"[error] {latin_name}: {exc}", file=sys.stderr)
            exit_code = 3
        except Exception as exc:  # pragma: no cover - unexpected failure
            print(f"[error] {latin_name}: unexpected failure ({exc})", file=sys.stderr)
            exit_code = 4
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

