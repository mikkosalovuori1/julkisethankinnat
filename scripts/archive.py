import json
from pathlib import Path
from datetime import datetime

PROCUREMENTS_FILE = "data/procurements.json"
HISTORY_FILE = "history/2026/procurements-2026.json"
SEARCH_INDEX_FILE = "data/search_index.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

current_items = load_json(PROCUREMENTS_FILE, [])
history_items = load_json(HISTORY_FILE, [])

history_by_id = {item.get("id"): item for item in history_items if item.get("id")}

for item in current_items:
    key = item.get("id")
    if key not in history_by_id:
        history_by_id[key] = {
            **item,
            "history_year": "2026",
            "archived_first_seen_at": item.get("found_at", datetime.utcnow().isoformat() + "Z"),
            "archived_last_seen_at": item.get("last_seen_at", datetime.utcnow().isoformat() + "Z")
        }
    else:
        history_by_id[key]["archived_last_seen_at"] = item.get("last_seen_at", datetime.utcnow().isoformat() + "Z")
        history_by_id[key].update(item)

history_list = list(history_by_id.values())

Path("history/2026").mkdir(parents=True, exist_ok=True)

with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(history_list, f, ensure_ascii=False, indent=2)

search_index = []
for item in history_list:
    search_index.append({
        "id": item.get("id", ""),
        "title": item.get("title", ""),
        "entity": item.get("entity", ""),
        "unit_name": item.get("unit_name", ""),
        "area": item.get("area", ""),
        "source_name": item.get("source_name", ""),
        "cpv_primary": item.get("cpv_primary", ""),
        "cpv_label": item.get("cpv_label", ""),
        "item_type": item.get("item_type", ""),
        "published_at": item.get("published_at", ""),
        "source_page": item.get("source_page", ""),
        "url": item.get("url", ""),
        "matched_keywords": item.get("matched_keywords", []),
        "search_text": item.get("search_text", "")
    })

with open(SEARCH_INDEX_FILE, "w", encoding="utf-8") as f:
    json.dump(search_index, f, ensure_ascii=False, indent=2)
