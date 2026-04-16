import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

with open("data/sources.json", "r", encoding="utf-8") as f:
    sources = json.load(f)

results = []

for source in sources:
    for url in source["urls"]:
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(" ", strip=True)
                full_url = urljoin(url, href)

                if "hank" in text.lower() or href.lower().endswith(".pdf"):
                    results.append({
                        "entity": source["name"],
                        "title": text or href,
                        "url": full_url,
                        "source_page": url,
                        "found_at": datetime.utcnow().isoformat() + "Z",
                        "is_new": True
                    })

        except Exception as e:
            results.append({
                "entity": source["name"],
                "title": f"ERROR: {e}",
                "url": url,
                "source_page": url,
                "found_at": datetime.utcnow().isoformat() + "Z",
                "is_new": False
            })

# poista duplikaatit
unique = {}
for item in results:
    if item["url"] not in unique:
        unique[item["url"]] = item

results = list(unique.values())

with open("data/procurements.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
