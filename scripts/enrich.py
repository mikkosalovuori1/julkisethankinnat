import json
import re
from pathlib import Path
from urllib.parse import urlparse

PROCUREMENTS_FILE = "data/procurements.json"
TMP_PROCUREMENTS_FILE = "data/procurements.enriched.tmp.json"
CPV_RULES_FILE = "data/cpv_rules.json"
KEYWORD_RULES_FILE = "data/keyword_rules.json"

def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def atomic_write_json(path, data):
    path = Path(path)
    tmp_path = path.with_suffix(path.suffix + ".writing")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)

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

    trigger_words = [
        "budjetti", "määräraha", "arvioitu arvo", "kustannusarvio",
        "budjetoitu", "investointi", "hinta", "arvo", "eur", "€"
    ]
    tl = t.lower()

    if not any(w in tl for w in trigger_words):
        return ""

    for pattern in patterns:
        m = re.search(pattern, t, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()

    return ""

def extract_keyword_tags(text, keyword_rules):
    text_l = text.lower()

    matched_keywords = []
    theme_tags = []
    signal_tags = []

    for rule in keyword_rules:
        kw = rule.get("keyword", "").lower()
        if not kw:
            continue

        if kw in text_l:
            original_kw = rule.get("keyword", "")
            if original_kw and original_kw not in matched_keywords:
                matched_keywords.append(original_kw)

            for theme in rule.get("themes", []):
                if theme not in theme_tags:
                    theme_tags.append(theme)

            for signal in rule.get("signals", []):
                if signal not in signal_tags:
                    signal_tags.append(signal)

    return matched_keywords[:25], theme_tags[:10], signal_tags[:10]

def fallback_tags(text, item_type):
    text_l = text.lower()
    theme_tags = []
    signal_tags = []

    if any(x in text_l for x in ["it", "ict", "ohjelmisto", "järjestelmä", "api", "digitaal", "pilvipalvelu"]):
        theme_tags.append("IT ja digitalisaatio")

    if any(x in text_l for x in [
        "rakentaminen", "urakka", "saneeraus", "peruskorjaus", "silta",
        "katu", "maanrakennus", "suunnittelu", "keittiö", "kaluste",
        "piha", "remontti"
    ]):
        theme_tags.append("Rakentaminen ja infra")

    if any(x in text_l for x in ["kulunvalvonta", "kamera", "vartiointi", "paloilmoitin", "turvallisuus"]):
        theme_tags.append("Turvallisuus")

    if any(x in text_l for x in ["siivous", "kiinteistöhuolto", "ylläpito", "kunnossapito"]):
        theme_tags.append("Kiinteistö ja ylläpito")

    if any(x in text_l for x in ["terveys", "sairaala", "hoiva", "potilas"]):
        theme_tags.append("Terveydenhuolto")

    if any(x in text_l for x in ["koulu", "päiväkoti", "oppilaitos"]):
        theme_tags.append("Koulutus")

    if item_type == "budjetti":
        signal_tags.append("budjetoitu")
    if item_type == "investointipäätös":
        signal_tags.append("investointivihje")
    if item_type == "hankintasuunnitelma":
        signal_tags.append("kilpailutus tulossa")
    if item_type == "hankintakalenteritieto":
        signal_tags.append("kalenterimerkintä")
    if item_type == "käynnissä oleva hankinta":
        signal_tags.append("käynnissä")
    if item_type == "mennyt kilpailutus":
        signal_tags.append("mennyt kilpailutus")
    if item_type == "sopimus päättymässä":
        signal_tags.extend(["sopimus päättymässä", "uusintahankinta"])

    return theme_tags, signal_tags

items = load_json(PROCUREMENTS_FILE, [])
cpv_rules = load_json(CPV_RULES_FILE, [])
keyword_rules = load_json(KEYWORD_RULES_FILE, [])

out = []

for item in items:
    text = " ".join([
        item.get("title", ""),
        item.get("pdf_text", ""),
        item.get("type_hint", ""),
        item.get("source_page", ""),
        item.get("url", "")
    ])

    cpv, cpv_label = find_cpv(text, cpv_rules)
    contract_end = extract_contract_end(text)
    deadline_at = extract_deadline(text)
    budget_value = extract_budget_value(text)
    item_type = classify_type(text)

    matched_keywords, theme_tags, signal_tags = extract_keyword_tags(text, keyword_rules)
    fb_themes, fb_signals = fallback_tags(text, item_type)

    for t in fb_themes:
        if t not in theme_tags:
            theme_tags.append(t)
    for s in fb_signals:
        if s not in signal_tags:
            signal_tags.append(s)

    if not theme_tags:
        theme_tags = ["Muut hankinnat"]
    if not signal_tags:
        signal_tags = ["ei erityistä signaalia"]

    source_domain = urlparse(item.get("url", "")).netloc

    out.append({
        **item,
        "cpv_primary": cpv,
        "cpv_label": cpv_label,
        "item_type": item_type,
        "contract_end_date": contract_end,
        "deadline_at": deadline_at,
        "estimated_budget_value": budget_value,
        "matched_keywords": matched_keywords,
        "theme_tags": theme_tags,
        "signal_tags": signal_tags,
        "source_domain": source_domain,
        "search_text": " ".join([
            text,
            " ".join(matched_keywords),
            " ".join(theme_tags),
            " ".join(signal_tags),
            cpv,
            cpv_label,
            item_type,
            budget_value
        ]).lower()
    })

atomic_write_json(TMP_PROCUREMENTS_FILE, out)
atomic_write_json(PROCUREMENTS_FILE, out)
