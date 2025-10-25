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
    python flower_wiki.py "Gentiana verna"
"""
import sys
import json
import time
import re
from typing import Optional, Dict, Any
from urllib.parse import quote

import requests

WD_SPARQL = "https://query.wikidata.org/sparql"
WD_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
UA = {"User-Agent": "flower-wiki-script/1.0 (+https://example.com; mailto:someone@example.com)"}

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

def main():
    if len(sys.argv) < 2:
        print("Usage: python flower_wiki.py \"Gentiana verna\"")
        sys.exit(2)
    latin = sys.argv[1].strip()
    payload = build_payload(latin)
    print(json.dumps(payload, ensure_ascii=False, indent=4))

if __name__ == "__main__":
    main()
