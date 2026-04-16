import json
import re
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

# 🔥 UUSI: päivämäärän tunnistus
def extract_contract_end(text):
    if not text:
        return ""

    patterns = [
        r"(\d{1,2}\.\d{1,2}\.\d{4})",
        r"(\d{4}-\d{2}-\d{2})"
    ]

    for p in patterns:
        matches = re.findall(p, text)
        for m in matches:
            if any(x in text.lower() for x in ["päättyy", "voimassa", "sopimus", "asti"]):
                return m

    return ""

def classify_type(text):
    t = text.lower()

    if "sopimus" in t and "päätty" in t:
        return "sopimus päättymässä"

    if any(x in t for x in ["budjetti","määräraha"]):
        return "budjetti"
    if "investointi" in t:
        return "investointipäätös"
    if "suunnitelma" in t:
        return "hankintasuunnitelma"
    if "kalenteri" in t:
        return "hankintakalenteritieto"
    if any(x in t for x in ["tarjous","kilpailutus"]):
        return "käynnissä oleva hankinta"
    if any(x in t for x in ["päätös","valittu"]):
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

procurements = load_json(PROCUREMENTS_FILE, [])
rules = load_json(CPV_RULES_FILE, [])

out = []

for item in procurements:

    text = " ".join([
        item.get("title",""),
        item.get("pdf_text",""),
        item.get("type_hint","")
    ])

    cpv, cpv_label = find_cpv(text, rules)

    contract_end = extract_contract_end(text)

    item_type = classify_type(text)

    out.append({
        **item,
        "cpv_primary": cpv,
        "cpv_label": cpv_label,
        "item_type": item_type,
        "contract_end_date": contract_end,
        "search_text": text.lower()
    })

with open(PROCUREMENTS_FILE,"w",encoding="utf-8") as f:
    json.dump(out,f,ensure_ascii=False,indent=2)
