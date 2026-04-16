import json
from pathlib import Path

SOURCES_FILE = "data/sources.json"

municipalities = [
    "helsinki","espoo","vantaa","tampere","turku","oulu","jyvaskyla","lahti","kuopio","pori",
    "lappeenranta","vaasa","seinajoki","rovaniemi","joensuu","mikkeli","kotka","kouvola",
    "salo","hyvinkaa","jarvenpaa","nurmijarvi","tuusula","kirkkonummi","kaarina","raisio",
    "lohja","kajaani","kemi","tornio","savonlinna","imatra","riihimaki","hameenlinna",
    "porvoo","rauma","naantali","kokkola","iisalmi","viitasaari","kuusamo","ylivieska",
    "ulvila","karkkila","kemijarvi","pieksamaki","nurmes","lieksa","suonenjoki","forssa"
]

def build_urls(name: str):
    base = f"https://www.{name}.fi"

    return [
        f"{base}/hankinnat",
        f"{base}/paatoksenteko",
        f"{base}/dynasty",
        f"{base}/dynasty10",
        f"{base}/cgi/DREQUEST.PHP",
        f"{base}/tweb",
        f"{base}/tweb/ktwebscr",
        f"{base}/oncloudos",
        f"{base}/asia"
    ]

def load_existing():
    path = Path(SOURCES_FILE)
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def main():
    sources = load_existing()

    existing_names = set()
    for s in sources:
        name = (s.get("name") or "").strip().lower()
        if name:
            existing_names.add(name)

    for m in municipalities:
        name = m.capitalize()

        if m in existing_names or name.lower() in existing_names:
            continue

        sources.append({
            "name": name,
            "area": "Suomi",
            "source_name": name,
            "urls": build_urls(m)
        })

    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
