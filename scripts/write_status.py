import json
from pathlib import Path
from datetime import datetime

PROCUREMENTS_FILE = Path("data/procurements.json")
STATUS_FILE = Path("data/status.json")

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

status = {
    "crawl_running": False,
    "last_updated": datetime.utcnow().isoformat() + "Z",
    "row_count": len(items)
}

atomic_write_json(STATUS_FILE, status)
