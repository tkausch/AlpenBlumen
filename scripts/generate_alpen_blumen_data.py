#!/usr/bin/env python3
"""
flower_wiki.py
---------------
Given a Latin (scientific) name of a flower, fetch multilingual common names and short
descriptions from Wikipedia, and family/genus from Wikidata. Outputs a JSON object like:

{
    "english": {"name": "...","description": "..."},
    "german": {"name": "...","description": "..."},
    "french": {"name": "...","description": "..."},
    "latin": "Gentiana verna",
    "family": "Gentianaceae",
    "genus": "Gentiana"
}

Usage:
    python generate_alpen_blumen_data.py "Gentiana verna"
    python generate_alpen_blumen_data.py --from-hartinger
    python generate_alpen_blumen_data.py --from-hartinger --output data/custom.json
"""
import argparse
import sys
import json
import time
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import quote

import requests

WD_SPARQL = "https://query.wikidata.org/sparql"
WD_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
UA = {"User-Agent": "flower-wiki-script/1.0 (+https://example.com; mailto:someone@example.com)"}
SCRIPT_DIR = Path(__file__).resolve().parent
LEGACY_ALPENBLUMEN_JSON = SCRIPT_DIR.parent / "AlpenBlumen/other/AlpenBlumen.json"
DATA_DIR = SCRIPT_DIR / "data"
HARTINGER_JSON = DATA_DIR / "hartinger.json"
BATCH_OUTPUT_JSON = DATA_DIR / "AlpenBlumen.json"

# Wikidata item IDs for taxon ranks we care about
RANK_SPECIES = "Q7432"
RANK_SUBSPECIES = "Q68947"
RANK_GENUS = "Q34740"
RANK_FAMILY = "Q35409"

def die(msg: str, code: int = 1):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)

def sparql_find_item_by_taxon_name(latin: str) -> Optional[str]:
    """
    Find the Wikidata QID for a taxon by exact taxon name (P225).
    Prefer species/subspecies if multiple are returned.
    """
    query = f"""
    SELECT ?item ?rank WHERE {{
      ?item wdt:P225 "{latin}" .
      OPTIONAL {{ ?item wdt:P105 ?rank. }}
    }}
    """
    r = requests.get(WD_SPARQL, params={"query": query, "format": "json"}, headers=UA, timeout=30)
    r.raise_for_status()
    results = r.json()["results"]["bindings"]
    if not results:
        return None
    # Prefer species/subspecies if available
    def rank_priority(rank_uri: Optional[str]) -> int:
        if not rank_uri:
            return 10
        qid = rank_uri.rsplit("/", 1)[-1]
        if qid == RANK_SPECIES: return 0
        if qid == RANK_SUBSPECIES: return 1
        return 5

    results.sort(key=lambda b: rank_priority(b.get("rank", {}).get("value")))
    item_uri = results[0]["item"]["value"]
    return item_uri.rsplit("/", 1)[-1]  # QID

def fetch_entity(qid: str) -> Dict[str, Any]:
    r = requests.get(WD_ENTITY.format(qid=qid), headers=UA, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["entities"][qid]

def claim_value_id(entity: Dict[str, Any], prop: str) -> Optional[str]:
    claims = entity.get("claims", {}).get(prop, [])
    if not claims:
        return None
    snak = claims[0]["mainsnak"]
    dv = snak.get("datavalue")
    if not dv:
        return None
    val = dv.get("value")
    if isinstance(val, dict) and "id" in val:
        return val["id"]
    return None

def claim_string(entity: Dict[str, Any], prop: str) -> Optional[str]:
    claims = entity.get("claims", {}).get(prop, [])
    if not claims:
        return None
    snak = claims[0]["mainsnak"]
    dv = snak.get("datavalue")
    if not dv:
        return None
    val = dv.get("value")
    if isinstance(val, str):
        return val
    return None

def get_rank_qid(entity: Dict[str, Any]) -> Optional[str]:
    return claim_value_id(entity, "P105")  # taxon rank

def get_parent_taxon_qid(entity: Dict[str, Any]) -> Optional[str]:
    return claim_value_id(entity, "P171")  # parent taxon

def get_taxon_name(entity: Dict[str, Any]) -> Optional[str]:
    return claim_string(entity, "P225")  # taxon name (Latin)

def walk_up_to_rank(start_qid: str, target_rank_qid: str, max_steps: int = 10) -> Optional[str]:
    """
    Walk parent taxon (P171) until we find a node whose rank (P105) matches target_rank_qid.
    Return its Latin taxon name (P225).
    """
    qid = start_qid
    for _ in range(max_steps):
        ent = fetch_entity(qid)
        rank = get_rank_qid(ent)
        if rank == target_rank_qid:
            return get_taxon_name(ent)
        parent = get_parent_taxon_qid(ent)
        if not parent:
            return None
        qid = parent
        time.sleep(0.1)  # be polite to the API
    return None

def get_lang_name_and_summary(entity: Dict[str, Any], latin: str, lang: str) -> Dict[str, str]:
    """
    For a given language, find the Wikipedia sitelink title (prefer),
    fallback to the Wikidata label or Latin name. Then fetch a short summary.
    """
    # Prefer Wikipedia page title
    sitelinks = entity.get("sitelinks", {})
    title = None
    key = f"{lang}wiki"
    if key in sitelinks:
        title = sitelinks[key]["title"]
    else:
        # Fallback: label in that language
        labels = entity.get("labels", {})
        title = labels.get(lang, {}).get("value") or latin

    summary = fetch_wikipedia_summary(title, lang)
    # Try to shorten to ~2 sentences
    summary = first_sentences(summary, 2)
    return {"name": title, "description": summary}

def fetch_wikipedia_summary(title: str, lang: str) -> str:
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
    try:
        r = requests.get(url, headers=UA, timeout=30)
        if r.status_code == 404:
            return ""
        r.raise_for_status()
        data = r.json()
        # 'extract' is human-friendly plain-text summary
        return data.get("extract", "") or ""
    except requests.RequestException:
        return ""

def first_sentences(text: str, n: int = 2) -> str:
    if not text:
        return text
    # A simple sentence splitter that handles common abbreviations reasonably.
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÄÖÜÀÂÉÈÊÎÔÙÇ])', text.strip())
    return " ".join(sentences[:n]).strip()

def build_payload(latin: str) -> Dict[str, Any]:
    qid = sparql_find_item_by_taxon_name(latin)
    if not qid:
        die(f"No Wikidata item found for taxon name '{latin}'.")

    entity = fetch_entity(qid)
    # genus & family (Latin)
    genus = walk_up_to_rank(qid, RANK_GENUS)
    family = walk_up_to_rank(qid, RANK_FAMILY)

    result = {
        "english": get_lang_name_and_summary(entity, latin, "en"),
        "german": get_lang_name_and_summary(entity, latin, "de"),
        "french": get_lang_name_and_summary(entity, latin, "fr"),
        "latin": latin,
        "family": family or "",
        "genus": genus or "",
    }
    return result

def load_json_array(path: Path) -> List[Any]:
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            die(f"Failed to parse JSON file '{path}': {exc}")
        if not isinstance(data, list):
            die(f"Expected a JSON array in '{path}'.")
        return data
    path.parent.mkdir(parents=True, exist_ok=True)
    return []

def gather_hartinger_latin_names(path: Path) -> List[str]:
    if not path.exists():
        die(f"Missing Hartinger dataset at '{path}'. Run hartinger_images.py first.")
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw_entries = json.load(fh)
    except json.JSONDecodeError as exc:
        die(f"Failed to parse Hartinger JSON '{path}': {exc}")
    if not isinstance(raw_entries, list):
        die(f"Expected a JSON array in '{path}'.")
    seen = set()
    names: List[str] = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        latin = entry.get("latin_name")
        if not latin:
            continue
        latin = str(latin).strip()
        if not latin or latin in seen:
            continue
        seen.add(latin)
        names.append(latin)
    if not names:
        die(f"No latin_name values found in '{path}'.")
    return names

def run_single(latin: str, output_path: Optional[str]) -> None:
    payload = build_payload(latin)
    target = Path(output_path) if output_path else LEGACY_ALPENBLUMEN_JSON
    entries = load_json_array(target)
    entries.append(payload)
    with target.open("w", encoding="utf-8") as fh:
        json.dump(entries, fh, ensure_ascii=False, indent=4)
        fh.write("\n")
    print(json.dumps(payload, ensure_ascii=False, indent=4))
    print(f"Appended entry for '{latin}' to {target}", file=sys.stderr)

def run_batch(output_path: Optional[str]) -> None:
    latin_names = gather_hartinger_latin_names(HARTINGER_JSON)
    results: List[Dict[str, Any]] = []
    failures = 0
    for latin in latin_names:
        try:
            payload = build_payload(latin)
        except SystemExit:
            failures += 1
            continue
        except requests.RequestException as exc:
            failures += 1
            print(f"Error fetching data for '{latin}': {exc}", file=sys.stderr)
            continue
        results.append(payload)
        time.sleep(0.2)
    if not results:
        die("No payloads generated from Hartinger dataset.")
    target = Path(output_path) if output_path else BATCH_OUTPUT_JSON
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Wrote {len(results)} entries to {target}")
    if failures:
        print(f"Skipped {failures} latin names due to errors.", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Fetch multilingual flower data from Wikipedia/Wikidata.")
    parser.add_argument("latin", nargs="?", help="Latin (scientific) name to fetch in single mode.")
    parser.add_argument(
        "--from-hartinger",
        action="store_true",
        help="Generate entries for all latin_name values in data/hartinger.json.",
    )
    parser.add_argument(
        "--output",
        help="Override output JSON path. Defaults to AlpenBlumen/other/AlpenBlumen.json in single mode, data/AlpenBlumen.json in batch mode.",
    )
    args = parser.parse_args()

    if args.from_hartinger:
        run_batch(args.output)
        return

    if not args.latin:
        parser.error("Provide a Latin name or use --from-hartinger.")
    run_single(args.latin.strip(), args.output)

if __name__ == "__main__":
    main()
