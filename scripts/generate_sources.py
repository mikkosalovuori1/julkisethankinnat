import json
from pathlib import Path

SOURCES_FILE = "data/sources.json"

# Lista kunnista (optimoitu domain-logiikka)
municipalities = [
    "helsinki","espoo","vantaa","tampere","turku","oulu","jyvaskyla","lahti","kuopio","pori",
    "lappeenranta","vaasa","seinajoki","rovaniemi","joensuu","mikkeli","kotka","kouvola",
    "salo","hyvinkaa","jarvenpaa","nurmijarvi","tuusula","kirkkonummi","kaarina","raisio",
    "lohja","kajaani","kemi","tornio","savonlinna","imatra","riihimaki","hameenlinna",
    "porvoo","rauma","naantali","kokkola","iisalmi","viitasaari","kuusamo","ylivieska",
    "ulvila","karkkila","kemijarvi","pieksamaki","nurmes","lieksa","suonenjoki","forssa"
]

def build_url(name):
    return f"https://www.{name}.fi/hankinnat"

def load_existing():
    if not Path(SOURCES_FILE).exists():
        return []
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    sources = load_existing()

    existing_names = set(s["name"].lower() for s in sources)

    for m in municipalities:
        name = m.capitalize()

        if m in existing_names:
            continue

        sources.append({
            "name": name,
            "area": "Suomi",
            "source_name": name,
            "urls": [build_url(m)]
        })

    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
