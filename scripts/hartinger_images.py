#!/usr/bin/env python3
"""
hartinger_images.py
-------------------
Query Wikimedia Commons for Anton Hartinger plates and extract Latin flower names.

By default the script inspects all Atlas der Alpenflora volumes, but you can
pass additional category titles via CLI. Results are written to
`data/hartinger.json` relative to this script (override with `--output`).

Usage (default behavior):
    python hartinger_images.py

This is equivalent to running `python hartinger_images.py --output data/hartinger.json`.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import time
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List, Optional, Sequence, Set

import requests

API_URL = "https://commons.wikimedia.org/w/api.php"
DEFAULT_CATEGORIES = [
    "Atlas der Alpenflora, Volume 1",
    "Atlas der Alpenflora, Volume 2",
    "Atlas der Alpenflora, Volume 3",
    "Atlas der Alpenflora, Volume 4",
]
UA = {"User-Agent": "alpenblumen-hartinger-script/1.0 (+https://github.com/)"}  # replace contact URL if publishing


@dataclass
class PlateEntry:
    title: str
    latin_name: Optional[str]
    source_category: str


class CommonsClient:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(UA)

    def get(self, params: Dict[str, str]) -> Dict:
        params.setdefault("format", "json")
        params.setdefault("formatversion", "2")
        response = self.session.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def category_files(self, category: str) -> Iterable[str]:
        """
        Yield file titles inside the given Commons category.
        """
        continue_token: Optional[str] = None
        cat_title = f"Category:{category}"
        while True:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": cat_title,
                "cmtype": "file",
                "cmlimit": "50",
            }
            if continue_token:
                params["cmcontinue"] = continue_token
            data = self.get(params)
            members = data.get("query", {}).get("categorymembers", [])
            for member in members:
                yield member["title"]
            continue_token = data.get("continue", {}).get("cmcontinue")
            if not continue_token:
                break
            time.sleep(0.1)  # polite pause

    def fetch_metadata(self, titles: Sequence[str]) -> Dict[str, Dict]:
        """
        Fetch extmetadata for the given file titles.
        """
        title_chunks = [titles[i : i + 50] for i in range(0, len(titles), 50)]
        result: Dict[str, Dict] = {}
        for chunk in title_chunks:
            params = {
                "action": "query",
                "prop": "imageinfo",
                "iiprop": "extmetadata",
                "titles": "|".join(chunk),
            }
            data = self.get(params)
            pages = data.get("query", {}).get("pages", [])
            for page in pages:
                result[page["title"]] = page
            time.sleep(0.1)
        return result


def clean_latin_name(name: str) -> Optional[str]:
    name = name.strip()
    if not name:
        return None
    # Replace HTML artifacts
    name = re.sub(r"&nbsp;?", " ", name)
    name = re.sub(r"\s+", " ", name)
    # Filter out obvious non-binomial strings
    if len(name.split()) < 1:
        return None
    return name


def latin_from_title(title: str) -> Optional[str]:
    base = title.split(":", 1)[-1]
    base = base.rsplit(".", 1)[0]
    parts = [p.strip() for p in base.split("-") if p.strip()]
    if not parts:
        return None
    candidate = parts[-1]
    candidate = candidate.replace("_", " ")
    return clean_latin_name(candidate)


def latin_from_metadata(page: Dict) -> Set[str]:
    names: Set[str] = set()
    imageinfo = page.get("imageinfo", [])
    if not imageinfo:
        return names
    metadata = imageinfo[0].get("extmetadata", {})
    description = metadata.get("ImageDescription", {}).get("value", "")
    object_name = metadata.get("ObjectName", {}).get("value", "")
    for text in (description, object_name):
        if not text:
            continue
        italics = re.findall(r"<i>([^<]+)</i>", text, flags=re.IGNORECASE)
        for item in italics:
            cleaned = clean_latin_name(item)
            if cleaned:
                names.add(cleaned)
        # fallback: look for binomial names in plain text
        for match in re.findall(r"\b([A-Z][a-z]+(?:\s+[a-z]{2,}))\b", text):
            cleaned = clean_latin_name(match)
            if cleaned:
                names.add(cleaned)
    return names


def gather_latin_names(categories: Sequence[str]) -> List[PlateEntry]:
    client = CommonsClient()
    entries: List[PlateEntry] = []
    seen_titles: Set[str] = set()

    for category in categories:
        files = list(client.category_files(category))
        if not files:
            continue
        metadata = client.fetch_metadata(files)
        for title in files:
            if re.search(r"\d", title):
                continue
            if title in seen_titles:
                continue
            page = metadata.get(title, {})
            latin_candidates = latin_from_metadata(page)
            title_candidate = latin_from_title(title)
            if title_candidate:
                latin_candidates.add(title_candidate)
            latin_name = None
            if latin_candidates:
                latin_name = sorted(latin_candidates)[0]
            entries.append(
                PlateEntry(
                    title=title,
                    latin_name=latin_name,
                    source_category=category,
                )
            )
            seen_titles.add(title)
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Latin flower names from Anton Hartinger plates on Wikimedia Commons.")
    parser.add_argument(
        "--category",
        "-c",
        action="append",
        dest="categories",
        help="Commons category title without the 'Category:' prefix. Can be provided multiple times.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Path to write JSON output. Defaults to data/hartinger.json beside this script.",
    )
    args = parser.parse_args()

    categories = args.categories or DEFAULT_CATEGORIES
    entries = gather_latin_names(categories)
    payload = [asdict(entry) for entry in entries]

    default_output = Path(__file__).resolve().parent / "data" / "hartinger.json"
    output_path = Path(args.output) if args.output else default_output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {len(payload)} entries to {output_path}")


if __name__ == "__main__":
    main()
