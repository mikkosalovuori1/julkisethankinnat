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
        score = sum(1 for kw in rule.get("keywords", []) if kw.lower() in text_l)
        if score:
            matches.append((score, rule))

    matches.sort(key=lambda x: x[0], reverse=True)

    if matches:
        best = matches[0][1]
        return best.get("cpv", ""), best.get("label", "")

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

def extract_deadline(text):
    if not text:
        return ""

    t = " ".join(str(text).split())
    t_l = t.lower()

    trigger_words = [
        "määräaika", "tarjoukset tulee jättää", "tarjousten jättöaika",
        "viimeistään", "jättöaika", "tarjous tulee jättää", "deadline"
    ]

    if not any(w in t_l for w in trigger_words):
        return ""

    patterns = [
        r"(?:määräaika|tarjoukset tulee jättää|tarjousten jättöaika|viimeistään|jättöaika|deadline)[^0-9]{0,25}(\d{1,2}\.\d{1,2}\.\d{4})",
        r"(?:määräaika|tarjoukset tulee jättää|tarjousten jättöaika|viimeistään|jättöaika|deadline)[^0-9]{0,25}(\d{4}-\d{2}-\d{2})",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, t_l, flags=re.IGNORECASE)
        if matches:
            return matches[0]

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

    if any(x in text_l for x in ["rakentaminen", "urakka", "saneeraus", "peruskorjaus", "silta", "katu", "maanrakennus"]):
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
        signal_tags.append("kilpailutus tulossa")
    if item_type == "käynnissä oleva hankinta":
        signal_tags.append("käynnissä")
    if item_type == "mennyt kilpailutus":
        signal_tags.append("mennyt kilpailutus")
    if item_type == "sopimus päättymässä":
        signal_tags.extend(["sopimus päättymässä", "uusintahankinta"])

    return theme_tags, signal_tags

def build_ai_summary(item_type, cpv_label, matched_keywords, signal_tags, pdf_text):
    parts = []

    if item_type:
        parts.append(f"Tyyppi: {item_type}.")
    if cpv_label:
        parts.append(f"CPV-luokka: {cpv_label}.")
    if matched_keywords:
        parts.append(f"Avainsanat: {', '.join(matched_keywords[:8])}.")
    if signal_tags:
        parts.append(f"Signaalit: {', '.join(signal_tags[:6])}.")

    cleaned_pdf = " ".join((pdf_text or "").split())
    if cleaned_pdf and not cleaned_pdf.startswith("PDF_ERROR"):
        parts.append(cleaned_pdf[:700])

    return " ".join(parts).strip()

procurements = load_json(PROCUREMENTS_FILE, [])
cpv_rules = load_json(CPV_RULES_FILE, [])
keyword_rules = load_json(KEYWORD_RULES_FILE, [])

out = []

for item in procurements:
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

    ai_summary = build_ai_summary(
        item_type=item_type,
        cpv_label=cpv_label,
        matched_keywords=matched_keywords,
        signal_tags=signal_tags,
        pdf_text=item.get("pdf_text", "")
    )

    parsed = urlparse(item.get("url", ""))
    source_domain = parsed.netloc

    out.append({
        **item,
        "cpv_primary": cpv,
        "cpv_label": cpv_label,
        "item_type": item_type,
        "contract_end_date": contract_end,
        "deadline_at": deadline_at,
        "matched_keywords": matched_keywords,
        "theme_tags": theme_tags,
        "signal_tags": signal_tags,
        "source_domain": source_domain,
        "ai_summary": ai_summary,
        "search_text": " ".join([
            text,
            " ".join(matched_keywords),
            " ".join(theme_tags),
            " ".join(signal_tags),
            cpv,
            cpv_label,
            item_type
        ]).lower()
    })

with open(PROCUREMENTS_FILE, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
