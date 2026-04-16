import json
import re
from pathlib import Path

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

    if any(x in t for x in [
        "sopimus päättyy", "sopimus päätty", "voimassa asti",
        "voimassa saakka", "sopimuskausi päättyy", "optiokausi päättyy"
    ]):
        return "sopimus päättymässä"

    if any(x in t for x in ["talousarvio", "budjetti", "määräraha"]):
        return "budjetti"
    if any(x in t for x in ["investointi", "investointiohjelma", "investointipäätös"]):
        return "investointipäätös"
    if any(x in t for x in ["hankintasuunnitelma", "kilpailutetaan vuonna", "suunnitelma"]):
        return "hankintasuunnitelma"
    if any(x in t for x in ["hankintakalenteri", "kalenteri"]):
        return "hankintakalenteritieto"
    if any(x in t for x in ["tarjouspyyntö", "jätä tarjous", "määräaika", "kilpailutus", "hankintailmoitus"]):
        return "käynnissä oleva hankinta"
    if any(x in t for x in ["valittu toimittaja", "hankintapäätös", "myönnetty", "sopimus tehty", "päätös"]):
        return "mennyt kilpailutus"

    return "muu hankintatieto"

def find_cpv(text, rules):
    text_l = text.lower()
    matches = []

    for rule in rules:
        score = sum(1 for kw in rule["keywords"] if kw.lower() in text_l)
        if score:
            matches.append((score, rule))

    matches.sort(reverse=True)

    if matches:
        best = matches[0][1]
        return best["cpv"], best["label"]

    return "", ""

def extract_contract_end(text):
    if not text:
        return ""

    t = " ".join(str(text).split())
    t_l = t.lower()

    trigger_words = [
        "päättyy", "voimassa asti", "voimassa saakka", "sopimuskausi",
        "optiokausi", "sopimus päättyy", "voimassa", "päättyminen"
    ]

    if not any(w in t_l for w in trigger_words):
        return ""

    patterns = [
        r"(?:päättyy|voimassa asti|voimassa saakka|sopimuskausi päättyy|optiokausi päättyy)[^0-9]{0,25}(\d{1,2}\.\d{1,2}\.\d{4})",
        r"(?:päättyy|voimassa asti|voimassa saakka|sopimuskausi päättyy|optiokausi päättyy)[^0-9]{0,25}(\d{4}-\d{2}-\d{2})",
        r"(\d{1,2}\.\d{1,2}\.\d{4})",
        r"(\d{4}-\d{2}-\d{2})"
    ]

    for pattern in patterns:
        matches = re.findall(pattern, t_l, flags=re.IGNORECASE)
        if matches:
            return matches[0]

    return ""

def extract_keywords(text, rules):
    text_l = text.lower()
    hits = []

    for rule in rules:
        for kw in rule["keywords"]:
            if kw.lower() in text_l and kw not in hits:
                hits.append(kw)

    extra = [
        "sopimus", "optiokausi", "voimassa", "päättyy",
        "maisema", "rakennus", "it", "siivous", "kulunvalvonta"
    ]
    for kw in extra:
        if kw in text_l and kw not in hits:
            hits.append(kw)

    return hits[:20]

procurements = load_json(PROCUREMENTS_FILE, [])
rules = load_json(CPV_RULES_FILE, [])

out = []

for item in procurements:
    text = " ".join([
        item.get("title", ""),
        item.get("pdf_text", ""),
        item.get("type_hint", ""),
        item.get("source_page", ""),
        item.get("url", "")
    ])

    cpv, cpv_label = find_cpv(text, rules)
    contract_end = extract_contract_end(text)
    item_type = classify_type(text)
    keywords = extract_keywords(text, rules)

    out.append({
        **item,
        "cpv_primary": cpv,
        "cpv_label": cpv_label,
        "item_type": item_type,
        "contract_end_date": contract_end,
        "matched_keywords": keywords,
        "search_text": text.lower()
    })

with open(PROCUREMENTS_FILE, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
