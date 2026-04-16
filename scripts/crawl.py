import json
import requests
from datetime import datetime
from pathlib import Path
from scripts.parsers import route_parser

SOURCES_FILE = "data/sources.json"
PROCUREMENTS_FILE = "data/procurements.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

with open(SOURCES_FILE, "r", encoding="utf-8") as f:
    sources = json.load(f)

old_items = load_json(PROCUREMENTS_FILE, [])
old_by_url = {item.get("url"): item for item in old_items if item.get("url")}

results = []

for source in sources:
    entity_name = source["name"]
    area_name = source.get("area", "")
    source_name = source.get("source_name", "Website")

    for url in source["urls"]:
        try:
            r = requests.get(
                url,
                timeout=30,
                headers={"User-Agent": "Mozilla/5.0 HankintaSeurantaBot/1.0"}
            )
            r.raise_for_status()

            parser = route_parser(url)
            items = parser(url, r.text)

            for p in items:
                full_url = p["url"]
                old_item = old_by_url.get(full_url)

                results.append({
                    "id": full_url,
                    "entity": entity_name,
                    "unit_name": entity_name,
                    "area": area_name,
                    "source_name": source_name,
                    "source_page": url,
                    "title": p.get("title") or full_url,
                    "url": full_url,
                    "document_url": p.get("document_url", ""),
                    "type_hint": p.get("type_hint", ""),
                    "found_at": old_item.get("found_at") if old_item else datetime.utcnow().isoformat() + "Z",
                    "last_seen_at": datetime.utcnow().isoformat() + "Z",
                    "is_new": old_item is None
                })

        except Exception as e:
            results.append({
                "id": f"{entity_name}-{url}",
                "entity": entity_name,
                "unit_name": entity_name,
                "area": area_name,
                "source_name": source_name,
                "source_page": url,
                "title": f"ERROR: {e}",
                "url": url,
                "document_url": "",
                "type_hint": "",
                "found_at": datetime.utcnow().isoformat() + "Z",
                "last_seen_at": datetime.utcnow().isoformat() + "Z",
                "is_new": False
            })

unique = {}
for item in results:
    key = item["url"]
    if key not in unique:
        unique[key] = item

results = list(unique.values())

with open(PROCUREMENTS_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
