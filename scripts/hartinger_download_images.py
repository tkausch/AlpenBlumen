#!/usr/bin/env python3
"""
hartinger_download_images.py
----------------------------
Given the JSON array produced by hartinger_images.py, download the referenced Wikimedia
Commons images into a local directory named `images` (or a custom output directory).
By default the script reads from `data/hartinger.json` relative to this file.

Usage:
    python hartinger_download_images.py
    python hartinger_download_images.py custom.json --output-dir data/images
    python hartinger_download_images.py -  # read JSON array from stdin
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse
import re

import requests

API_URL = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "alpenblumen-download-images/1.0 (+https://github.com/)"}  # replace contact URL if publishing
DEFAULT_JSON = Path(__file__).resolve().parent / "data" / "hartinger.json"


def load_entries(source: str) -> List[Dict]:
    if source == "-":
        data = json.load(sys.stdin)
    else:
        with open(source, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("Expected the input JSON to contain an array.")
    return data


def chunked(seq: Iterable[str], size: int) -> Iterable[List[str]]:
    chunk: List[str] = []
    for item in seq:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def fetch_imageinfo(titles: List[str], session: requests.Session) -> Dict[str, Dict]:
    """
    Retrieve imageinfo metadata for the given Commons file titles.
    """
    result: Dict[str, Dict] = {}
    for batch in chunked(titles, 50):
        params = {
            "action": "query",
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
            "formatversion": "2",
            "titles": "|".join(batch),
        }
        resp = session.get(API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for page in data.get("query", {}).get("pages", []):
            result[page.get("title", "")] = page
        time.sleep(0.1)  # be polite to the API
    return result


def sanitize_name(name: str) -> str:
    # Preserve spaces for readability but strip disallowed characters.
    cleaned = name.strip().replace("_", " ")
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "image"


def title_basename(title: str) -> str:
    base = title.split(":", 1)[-1]
    base = base.rsplit(".", 1)[0]
    return base


def ensure_unique(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    idx = 2
    while True:
        candidate = path.with_name(f"{stem}_{idx}{suffix}")
        if not candidate.exists():
            return candidate
        idx += 1


def download_file(url: str, destination: Path, session: requests.Session) -> None:
    response = session.get(url, timeout=60, stream=True)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as fh:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                fh.write(chunk)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Wikimedia Commons images listed in a hartinger_images JSON array.")
    parser.add_argument(
        "source",
        nargs="?",
        default=str(DEFAULT_JSON),
        help=f"Path to JSON file or '-' to read from stdin (default: {DEFAULT_JSON}).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="images",
        help="Directory to save the downloaded files (default: images).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip downloading files whose target filename already exists.",
    )
    args = parser.parse_args()

    entries = load_entries(args.source)
    titles = [entry.get("title") for entry in entries if entry.get("title")]
    if not titles:
        print("No file titles found in the input.", file=sys.stderr)
        return

    session = requests.Session()
    session.headers.update(UA)
    metadata = fetch_imageinfo(titles, session)

    output_dir = Path(args.output_dir)
    saved = 0
    skipped = 0
    for entry in entries:
        title = entry.get("title")
        if not title or re.search(r"\d", title):
            continue
        page = metadata.get(title)
        if not page:
            print(f"Warning: no metadata found for '{title}'.", file=sys.stderr)
            continue
        info = page.get("imageinfo", [])
        if not info:
            print(f"Warning: no imageinfo available for '{title}'.", file=sys.stderr)
            continue
        url = info[0].get("url")
        if not url:
            print(f"Warning: missing URL for '{title}'.", file=sys.stderr)
            continue

        latin_name = entry.get("latin_name") or title_basename(title)
        slug = sanitize_name(latin_name)
        ext = Path(urlparse(url).path).suffix or ".jpg"
        target_path = output_dir / f"{slug}{ext}"
        target_path = ensure_unique(target_path)

        if args.skip_existing and target_path.exists():
            skipped += 1
            continue

        try:
            download_file(url, target_path, session)
            saved += 1
            print(f"Saved {title} -> {target_path}")
        except requests.RequestException as exc:
            print(f"Error downloading '{title}': {exc}", file=sys.stderr)

    print(f"Completed: {saved} downloaded, {skipped} skipped.", file=sys.stderr)


if __name__ == "__main__":
    main()
