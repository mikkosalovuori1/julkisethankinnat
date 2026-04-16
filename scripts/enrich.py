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

    trigger_words = ["budjetti", "määräraha", "arvioitu arvo", "kustannusarvio", "budjetoitu", "investointi"]
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
        signal_tags.append("kalenterimerkintä")
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

def extract_budget_line_items(item, cpv_rules, keyword_rules):
    pdf_text = item.get("pdf_text", "") or ""
    if not pdf_text or str(pdf_text).startswith("PDF_ERROR"):
        return []

    item_type = item.get("item_type", "")
    if item_type not in ["budjetti", "investointipäätös", "hankintasuunnitelma"]:
        return []

    lines = [re.sub(r"\s+", " ", line).strip() for line in pdf_text.splitlines()]
    lines = [line for line in lines if line]

    generated = []
    seen = set()

    value_patterns = [
        r"(\d[\d\s]{1,15},\d{2}\s?€)",
        r"(\d[\d\s]{1,15}\s?€)",
        r"(\d[\d\s]{1,15}\s?eur)",
        r"(\d[\d\s]{1,15}\s?milj\.?\s?€)",
        r"(\d[\d\s]{1,15}\s?m€)"
    ]

    for idx, line in enumerate(lines):
        if len(line) < 10:
            continue

        value = ""
        for pattern in value_patterns:
            m = re.search(pattern, line, flags=re.IGNORECASE)
            if m:
                value = m.group(1).strip()
                break

        if not value:
            continue

        title = re.sub(r"(\d[\d\s]{1,15},\d{2}\s?€|\d[\d\s]{1,15}\s?€|\d[\d\s]{1,15}\s?eur|\d[\d\s]{1,15}\s?milj\.?\s?€|\d[\d\s]{1,15}\s?m€)", "", line, flags=re.IGNORECASE).strip(" -–—:;,.")
        title = re.sub(r"\s+", " ", title).strip()

        if len(title) < 4:
            continue
        if len(title) > 180:
            continue

        lower_title = title.lower()
        if lower_title in seen:
            continue
        seen.add(lower_title)

        context_lines = lines[max(0, idx-1):min(len(lines), idx+2)]
        context_text = " ".join(context_lines)

        cpv, cpv_label = find_cpv(context_text, cpv_rules)
        matched_keywords, theme_tags, signal_tags = extract_keyword_tags(context_text, keyword_rules)
        fb_themes, fb_signals = fallback_tags(context_text, item_type)

        for t in fb_themes:
            if t not in theme_tags:
                theme_tags.append(t)
        for s in fb_signals:
            if s not in signal_tags:
                signal_tags.append(s)

        if "poimittu budjettidokumentista" not in signal_tags:
            signal_tags.append("poimittu budjettidokumentista")
        if "budjetoitu" not in signal_tags:
            signal_tags.append("budjetoitu")

        if not theme_tags:
            theme_tags = ["Muut hankinnat"]

        child_id = f"{item.get('id','budget')}-budget-item-{idx}"

        generated.append({
            "id": child_id,
            "entity": item.get("entity", ""),
            "unit_name": item.get("unit_name", ""),
            "area": item.get("area", ""),
            "source_name": item.get("source_name", ""),
            "source_page": item.get("source_page", ""),
            "title": title,
            "url": item.get("url", ""),
            "document_url": item.get("document_url", ""),
            "type_hint": "budjettirivi",
            "pdf_text": item.get("pdf_text", ""),
            "found_at": item.get("found_at", ""),
            "last_seen_at": item.get("last_seen_at", ""),
            "is_new": item.get("is_new", False),
            "published_at": item.get("published_at", item.get("found_at", "")),
            "deadline_at": extract_deadline(context_text),
            "contract_end_date": "",
            "estimated_budget_value": value,
            "cpv_primary": cpv,
            "cpv_label": cpv_label,
            "item_type": "budjetti",
            "matched_keywords": matched_keywords,
            "theme_tags": theme_tags,
            "signal_tags": signal_tags,
            "source_domain": item.get("source_domain", ""),
            "ai_summary": f"Poimittu budjettidokumentista. {context_text[:350]}",
            "search_text": " ".join([
                title,
                context_text,
                value,
                " ".join(matched_keywords),
                " ".join(theme_tags),
                " ".join(signal_tags),
                cpv,
                cpv_label,
                "budjetti"
            ]).lower(),
            "generated_from_budget": True,
            "parent_budget_id": item.get("id", ""),
            "parent_budget_title": item.get("title", "")
        })

    return generated[:40]

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

    ai_summary = build_ai_summary(
        item_type=item_type,
        cpv_label=cpv_label,
        matched_keywords=matched_keywords,
        signal_tags=signal_tags,
        pdf_text=item.get("pdf_text", "")
    )

    parsed = urlparse(item.get("url", ""))
    source_domain = parsed.netloc

    base_item = {
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
        "ai_summary": ai_summary,
        "generated_from_budget": item.get("generated_from_budget", False),
        "parent_budget_id": item.get("parent_budget_id", ""),
        "parent_budget_title": item.get("parent_budget_title", ""),
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
    }

    out.append(base_item)

    for child in extract_budget_line_items(base_item, cpv_rules, keyword_rules):
        out.append(child)

# poistetaan duplikaatit id:n perusteella
unique = {}
for item in out:
    key = item.get("id") or item.get("url")
    if key not in unique:
        unique[key] = item

final_items = list(unique.values())

with open(PROCUREMENTS_FILE, "w", encoding="utf-8") as f:
    json.dump(final_items, f, ensure_ascii=False, indent=2)
