import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
from pathlib import Path

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
            soup = BeautifulSoup(r.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(" ", strip=True)
                full_url = urljoin(url, href)

                blob = f"{text} {href}".lower()
                if any(token in blob for token in [
                    "hank", "tarjous", "kilpailu", "sopimus",
                    ".pdf", "invest", "budjet", "suunnitelma", "kalenteri"
                ]):
                    old_item = old_by_url.get(full_url)
                    results.append({
                        "id": full_url,
                        "entity": entity_name,
                        "unit_name": entity_name,
                        "area": area_name,
                        "source_name": source_name,
                        "source_page": url,
                        "title": text or href,
                        "url": full_url,
                        "document_url": full_url if full_url.lower().endswith(".pdf") else "",
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

for source in sources:
    for url in source["urls"]:
        try:
            r = requests.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 HankintaSeurantaBot/1.0"
            })
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(" ", strip=True)
                full_url = urljoin(url, href)

                if "hank" in text.lower() or href.lower().endswith(".pdf"):
                    old_item = old_by_url.get(full_url)
                    matched_keywords = detect_keywords(text)

                    item = {
                        "entity": source["name"],
                        "title": text or href,
                        "url": full_url,
                        "source_page": url,
                        "found_at": old_item.get("found_at") if old_item else datetime.utcnow().isoformat() + "Z",
                        "last_seen_at": datetime.utcnow().isoformat() + "Z",
                        "is_new": old_item is None,
                        "matched_keywords": matched_keywords
                    }

                    results.append(item)

        except Exception as e:
            results.append({
                "entity": source["name"],
                "title": f"ERROR: {e}",
                "url": url,
                "source_page": url,
                "found_at": datetime.utcnow().isoformat() + "Z",
                "last_seen_at": datetime.utcnow().isoformat() + "Z",
                "is_new": False,
                "matched_keywords": []
            })

unique = {}
for item in results:
    key = item["url"]
    if key not in unique:
        unique[key] = item

results = list(unique.values())

with open(PROCUREMENTS_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
