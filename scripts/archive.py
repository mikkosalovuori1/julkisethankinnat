import json
from pathlib import Path
from datetime import datetime

PROCUREMENTS_FILE = Path("data/procurements.json")
SEARCH_INDEX_FILE = Path("data/search_index.json")
HISTORY_DIR = Path("history/2026")
HISTORY_FILE = HISTORY_DIR / "procurements-2026.json"

HISTORY_DIR.mkdir(parents=True, exist_ok=True)

def load_json(path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def atomic_write_json(path, data):
    tmp_path = path.with_suffix(path.suffix + ".writing")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)

items = load_json(PROCUREMENTS_FILE, [])
history = load_json(HISTORY_FILE, [])

existing_ids = {x.get("id") for x in history if x.get("id")}
for item in items:
    if item.get("id") not in existing_ids:
        history.append(item)

search_index = [
    {
        "id": item.get("id"),
        "title": item.get("title", ""),
        "entity": item.get("entity", ""),
        "area": item.get("area", ""),
        "item_type": item.get("item_type", ""),
        "cpv_primary": item.get("cpv_primary", ""),
        "search_text": item.get("search_text", ""),
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    for item in items
]

atomic_write_json(HISTORY_FILE, history)
atomic_write_json(SEARCH_INDEX_FILE, search_index)
