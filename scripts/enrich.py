import json
import re
from pathlib import Path
from urllib.parse import urlparse

PROCUREMENTS_FILE = "data/procurements.json"
CPV_RULES_FILE = "data/cpv_rules.json"
KEYWORD_RULES_FILE = "data/keyword_rules.json"

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

    if any(x in t for x in ["talousarvio", "budjetti", "määräraha", "budjetoitu", "taloussuunnitelma"]):
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
        score = sum(1 for kw in rule.get("keywords", []) if kw.lower() in text_l)
        if score:
            matches.append((score, rule))

    matches.sort(key=lambda x: x[0], reverse=True)

    if matches:
        best = matches[0][1]
        return best.get("cpv", ""), best.get("label", "")

    return "", ""

def extract_date_by_triggers(text, trigger_words):
    if not text:
        return ""
    t = " ".join(str(text).split())
    t_l = t.lower()

    if not any(w in t_l for w in trigger_words):
        return ""

    patterns = [
        r"(\d{1,2}\.\d{1,2}\.\d{4})",
        r"(\d{4}-\d{2}-\d{2})"
    ]

    for pattern in patterns:
        matches = re.findall(pattern, t_l, flags=re.IGNORECASE)
        if matches:
            return matches[0]
    return ""

def extract_contract_end(text):
    return extract_date_by_triggers(text, [
        "päättyy", "voimassa asti", "voimassa saakka",
        "sopimuskausi", "optiokausi", "sopimus päättyy",
        "voimassa", "päättyminen"
    ])

def extract_deadline(text):
    return extract_date_by_triggers(text, [
        "määräaika", "tarjoukset tulee jättää", "tarjousten jättöaika",
        "viimeistään", "jättöaika", "deadline", "tarjous tulee jättää"
    ])

def extract_budget_value(text):
    if not text:
        return ""

    t = " ".join(str(text).split())

    patterns = [
        r"(\d[\d\s]{1,15},\d{2}\s?€)",
        r"(\d[\d\s]{1,15}\s?€)",
        r"(\d[\d\s]{1,15}\s?eur)",
        r"(\d[\d\s]{1,15}\s?milj\.?\s?€)",
        r"(\d[\d\s]{1,15}\s?m€)"
    ]

    trigger_words = ["budjetti", "määräraha", "arvioitu arvo", "kustannusarvio", "
