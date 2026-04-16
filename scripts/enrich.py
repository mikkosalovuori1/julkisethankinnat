import json
from pathlib import Path
from urllib.parse import urlparse

PROCUREMENTS_FILE = "data/procurements.json"
CPV_RULES_FILE = "data/cpv_rules.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def classify_type(text):
    t = text.lower()

    if any(x in t for x in ["talousarvio", "budjetti", "määräraha"]):
        return "budjetti"
    if any(x in t for x in ["investointi", "investointiohjelma", "investointipäätös"]):
        return "investointipäätös"
    if any(x in t for x in ["hankintasuunnitelma", "suunnitelma", "kilpailutetaan vuonna"]):
        return "hankintasuunnitelma"
    if any(x in t for x in ["hankintakalenteri", "kalenteri"]):
        return "hankintakalenteritieto"
    if any(x in t for x in ["tarjouspyyntö", "jätä tarjous", "määräaika", "kilpailutus", "hankintailmoitus"]):
        return "käynnissä oleva hankinta"
    if any(x in t for x in ["valittu toimittaja", "hankintapäätös", "päätös", "myönnetty", "sopimus tehty"]):
        return "mennyt kilpailutus"

    return "muu hankintatieto"

def find_cpv(text, rules):
    text_l = text.lower()
    matches = []

    for rule in rules:
        hit_count = 0
        for kw in rule["keywords"]:
            if kw.lower() in text_l:
                hit_count += 1

        if hit_count > 0:
            matches.append({
                "cpv": rule["cpv"],
                "label": rule["label"],
                "score": hit_count
            })

    matches.sort(key=lambda x: x["score"], reverse=True)

    if matches:
        primary = matches[0]
        secondary = [m["cpv"] for m in matches[1:4]]
        confidence = min(0.55 + primary["score"] * 0.12, 0.97)
        return primary["cpv"], primary["label"], secondary, round(confidence, 2)

    return "", "", [], 0.0

def extract_keywords(text, rules):
    text_l = text.lower()
    hits = []

    for rule in rules:
        for kw in rule["keywords"]:
            if kw.lower() in text_l and kw not in hits:
                hits.append(kw)

    return hits[:20]

procurements = load_json(PROCUREMENTS_FILE, [])
rules = load_json(CPV_RULES_FILE, [])

enriched = []

for item in procurements:
    title = item.get("title", "")
    source_page = item.get("source_page", "")
    url = item.get("url", "")
    type_hint = item.get("type_hint", "")
    pdf_text = item.get("pdf_text", "")

    combined_text = f"{title} {source_page} {url} {type_hint} {pdf_text}"

    cpv_primary, cpv_label, cpv_secondary, cpv_confidence = find_cpv(combined_text, rules)
    matched_keywords = extract_keywords(combined_text, rules)
    item_type = classify_type(combined_text)

    parsed = urlparse(url)
    source_domain = parsed.netloc

    ai_summary = ""
    if pdf_text and not str(pdf_text).startswith("PDF_EXTRACT_ERROR"):
        cleaned = " ".join(str(pdf_text).split())
        ai_summary = cleaned[:700]

    enriched.append({
        **item,
        "cpv_primary": cpv_primary,
        "cpv_label": cpv_label,
        "cpv_secondary": cpv_secondary,
        "cpv_confidence": cpv_confidence,
        "matched_keywords": matched_keywords,
        "item_type": item_type,
        "published_at": item.get("found_at", ""),
        "deadline_at": item.get("deadline_at", ""),
        "document_file_name": url.split("/")[-1] if url else "",
        "source_domain": source_domain,
        "ai_summary": ai_summary,
        "search_text": " ".join([
            item.get("title", ""),
            item.get("entity", ""),
            item.get("unit_name", ""),
            item.get("area", ""),
            item.get("source_name", ""),
            item_type,
            cpv_primary,
            cpv_label,
            " ".join(matched_keywords),
            str(pdf_text)
        ]).lower()
    })

with open(PROCUREMENTS_FILE, "w", encoding="utf-8") as f:
    json.dump(enriched, f, ensure_ascii=False, indent=2)
