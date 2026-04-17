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
    if cleaned_pdf:
        parts.append(cleaned_pdf[:700])

    return " ".join(parts).strip()

def normalize_text(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()

def split_paragraphs(text):
    raw = str(text or "")
    parts = re.split(r"\n\s*\n+", raw)
    parts = [normalize_text(p) for p in parts if normalize_text(p)]
    return parts

def split_lines(text):
    raw = str(text or "")
    lines = [normalize_text(line) for line in raw.splitlines()]
    return [line for line in lines if line]

def looks_like_procurement_candidate(text):
    t = normalize_text(text)
    tl = t.lower()

    if len(t) < 6:
        return False
    if len(t) > 320:
        return False

    keyword_hits = [
        "hankinta", "suunnittelu", "urakka", "palvelu", "järjestelmä",
        "uusinta", "rakentaminen", "siivous", "kulunvalvonta", "keittiö",
        "saneeraus", "peruskorjaus", "toimitus", "kilpailutus", "laite",
        "kaluste", "remontti", "piha", "koulu", "päiväkoti", "valaistus",
        "kameravalvonta", "kiinteistöhuolto", "kunnossapito", "ohjelmisto",
        "ict", "it", "maisemasuunnittelu", "vihersuunnittelu"
    ]

    value_patterns = [
        r"\d[\d\s]{1,15},\d{2}\s?€",
        r"\d[\d\s]{1,15}\s?€",
        r"\d[\d\s]{1,15}\s?eur",
        r"\d[\d\s]{1,15}\s?milj\.?\s?€",
        r"\d[\d\s]{1,15}\s?m€"
    ]

    has_keyword = any(w in tl for w in keyword_hits)
    has_money = any(re.search(p, t, flags=re.IGNORECASE) for p in value_patterns)
    has_deadline = bool(extract_deadline(t))
    has_contract_end = bool(extract_contract_end(t))

    return has_keyword or has_money or has_deadline or has_contract_end

def refine_title(title):
    t = normalize_text(title)

    # Poista selviä loppuhäntiä
    t = re.sub(r"\b\d[\d\s]{1,15},\d{2}\s?€\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\b\d[\d\s]{1,15}\s?€\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\b\d[\d\s]{1,15}\s?eur\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\b\d[\d\s]{1,15}\s?milj\.?\s?€\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\b\d[\d\s]{1,15}\s?m€\b", "", t, flags=re.IGNORECASE)

    t = re.sub(r"\b(talousarvio|budjetti|määräraha|investointiohjelma|liite|pdf|sivu \d+)\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip(" -–—:;,.")
    return t[:140].strip()

def split_attachment_candidate(text):
    t = normalize_text(text)
    if not t:
        return None

    value_patterns = [
        r"(\d[\d\s]{1,15},\d{2}\s?€)",
        r"(\d[\d\s]{1,15}\s?€)",
        r"(\d[\d\s]{1,15}\s?eur)",
        r"(\d[\d\s]{1,15}\s?milj\.?\s?€)",
        r"(\d[\d\s]{1,15}\s?m€)"
    ]

    value = ""
    match = None
    for p in value_patterns:
        m = re.search(p, t, flags=re.IGNORECASE)
        if m:
            value = m.group(1).strip()
            match = m
            break

    title = t
    desc = ""

    if match:
        before = t[:match.start()].strip(" -–—:;,.")
        after = t[match.end():].strip(" -–—:;,.")
        if before:
            title = before
        if after:
            desc = after

    if ":" in title and len(title.split(":")[0]) > 3:
        left, right = title.split(":", 1)
        if len(left.strip()) >= 4 and len(left.strip()) < 140:
            title = left.strip()
            if not desc:
                desc = right.strip()

    title = refine_title(title)

    if len(title) < 4:
        return None

    if not desc:
        desc = f"Poimittu liitetiedostosta: {title}"
    desc = normalize_text(desc)[:350]

    return {
        "title": title,
        "description": desc,
        "value": value
    }

def estimate_extraction_confidence(text, title, value, cpv, matched_keywords):
    score = 0

    if len(title.split()) >= 2:
        score += 2
    if value:
        score += 3
    if cpv:
        score += 2
    if matched_keywords:
        score += min(len(matched_keywords), 3)
    if extract_deadline(text):
        score += 2
    if extract_contract_end(text):
        score += 1
    if "hankinta" in text.lower():
        score += 1

    if score >= 8:
        return "korkea"
    if score >= 5:
        return "keskitaso"
    return "matala"

def extract_attachment_items(item, cpv_rules, keyword_rules):
    source_text = item.get("pdf_text", "") or ""
    if not source_text:
        return []

    lines = split_lines(source_text)
    paragraphs = split_paragraphs(source_text)

    candidates = []

    for idx, line in enumerate(lines):
        if looks_like_procurement_candidate(line):
            context_lines = lines[max(0, idx-1):min(len(lines), idx+2)]
            context = normalize_text(" ".join(context_lines))
            candidates.append(("line", idx, context))

    for idx, para in enumerate(paragraphs):
        if looks_like_procurement_candidate(para):
            candidates.append(("paragraph", idx, para[:500]))

    generated = []
    seen_titles = set()

    for source_kind, idx, context_text in candidates:
        parsed_line = split_attachment_candidate(context_text)
        if not parsed_line:
            continue

        title_key = parsed_line["title"].lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        cpv, cpv_label = find_cpv(context_text, cpv_rules)
        item_type = classify_type(context_text)
        deadline_at = extract_deadline(context_text)
        contract_end = extract_contract_end(context_text)
        budget_value = parsed_line["value"] or extract_budget_value(context_text)

        matched_keywords, theme_tags, signal_tags = extract_keyword_tags(context_text, keyword_rules)
        fb_themes, fb_signals = fallback_tags(context_text, item_type)

        for t in fb_themes:
            if t not in theme_tags:
                theme_tags.append(t)
        for s in fb_signals:
            if s not in signal_tags:
                signal_tags.append(s)

        if "poimittu liitetiedostosta" not in signal_tags:
            signal_tags.append("poimittu liitetiedostosta")

        if not theme_tags:
            theme_tags = ["Muut hankinnat"]

        confidence = estimate_extraction_confidence(
            text=context_text,
            title=parsed_line["title"],
            value=budget_value,
            cpv=cpv,
            matched_keywords=matched_keywords
        )

        if confidence == "matala" and not budget_value and len(parsed_line["title"].split()) < 3:
            continue

        child_id = f"{item.get('id','attachment')}-{source_kind}-item-{idx}"

        generated.append({
            "id": child_id,
            "entity": item.get("entity", ""),
            "unit_name": item.get("unit_name", ""),
            "area": item.get("area", ""),
            "source_name": item.get("source_name", ""),
            "source_page": item.get("source_page", ""),
            "title": parsed_line["title"],
            "url": item.get("url", ""),
            "document_url": item.get("document_url", ""),
            "type_hint": "liitepoiminta",
            "pdf_text": item.get("pdf_text", ""),
            "found_at": item.get("found_at", ""),
            "last_seen_at": item.get("last_seen_at", ""),
            "is_new": item.get("is_new", False),
            "published_at": item.get("published_at", item.get("found_at", "")),
            "deadline_at": deadline_at,
            "contract_end_date": contract_end,
            "estimated_budget_value": budget_value,
            "cpv_primary": cpv,
            "cpv_label": cpv_label,
            "item_type": item_type if item_type != "muu hankintatieto" else "poimittu hankinta",
            "matched_keywords": matched_keywords,
            "theme_tags": theme_tags,
            "signal_tags": signal_tags,
            "source_domain": item.get("source_domain", ""),
            "ai_summary": parsed_line["description"],
            "search_text": " ".join([
                parsed_line["title"],
                parsed_line["description"],
                context_text,
                budget_value,
                " ".join(matched_keywords),
                " ".join(theme_tags),
                " ".join(signal_tags),
                cpv,
                cpv_label,
                item_type
            ]).lower(),
            "generated_from_attachment": True,
            "parent_attachment_id": item.get("id", ""),
            "parent_attachment_title": item.get("title", ""),
            "extraction_confidence": confidence,
            "extraction_source_kind": source_kind,
            "snippet_image": item.get("snippet_image", ""),
            "snippet_page": item.get("snippet_page", "")
        })

    return generated[:120]

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
        "generated_from_attachment": item.get("generated_from_attachment", False),
        "parent_attachment_id": item.get("parent_attachment_id", ""),
        "parent_attachment_title": item.get("parent_attachment_title", ""),
        "extraction_confidence": item.get("extraction_confidence", ""),
        "extraction_source_kind": item.get("extraction_source_kind", ""),
        "snippet_image": item.get("snippet_image", ""),
        "snippet_page": item.get("snippet_page", ""),
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

    for child in extract_attachment_items(base_item, cpv_rules, keyword_rules):
        out.append(child)

unique = {}
for item in out:
    key = item.get("id") or item.get("url")
    if key not in unique:
        unique[key] = item

final_items = list(unique.values())

with open(PROCUREMENTS_FILE, "w", encoding="utf-8") as f:
    json.dump(final_items, f, ensure_ascii=False, indent=2)
