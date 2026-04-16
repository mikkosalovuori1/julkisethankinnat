from bs4 import BeautifulSoup
from urllib.parse import urljoin

def normalize_link(base_url, href):
    try:
        return urljoin(base_url, href)
    except:
        return href

def is_relevant(text, href):
    blob = f"{text} {href}".lower()
    return any(token in blob for token in [
        "hank", "tarjous", "kilpailu", "sopimus",
        ".pdf", "invest", "budjet", "suunnitelma",
        "kalenteri", "urakka"
    ])

# ---------- GENERIC FALLBACK ----------
def parse_generic(url, html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True)
        full_url = normalize_link(url, href)

        if is_relevant(text, href):
            results.append({
                "title": text or href,
                "url": full_url,
                "document_url": full_url if full_url.lower().endswith(".pdf") else "",
                "type_hint": ""
            })

    return results

# ---------- AKAA ----------
def parse_akaa(url, html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for a in soup.select("a"):
        href = a.get("href")
        if not href:
            continue

        text = a.get_text(" ", strip=True)
        full_url = normalize_link(url, href)

        if "hank" in text.lower() or ".pdf" in href.lower():
            results.append({
                "title": text,
                "url": full_url,
                "document_url": full_url if ".pdf" in full_url else "",
                "type_hint": "hankinta"
            })

    return results

# ---------- HELSINKI ----------
def parse_helsinki(url, html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        href = a["href"]
        full_url = normalize_link(url, href)

        if any(x in text.lower() for x in ["hankinta", "tarjous", "kilpailu"]):
            results.append({
                "title": text,
                "url": full_url,
                "document_url": full_url if full_url.endswith(".pdf") else "",
                "type_hint": "kilpailutus"
            })

    return results

# ---------- ESPOO ----------
def parse_espoo(url, html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for a in soup.select("a"):
        href = a.get("href")
        text = a.get_text(" ", strip=True)
        full_url = normalize_link(url, href)

        if is_relevant(text, href):
            results.append({
                "title": text,
                "url": full_url,
                "document_url": full_url if ".pdf" in full_url else "",
                "type_hint": ""
            })

    return results

# ---------- VANTAA ----------
def parse_vantaa(url, html):
    return parse_generic(url, html)

# ---------- TAMPERE ----------
def parse_tampere(url, html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True)
        full_url = normalize_link(url, href)

        if any(x in text.lower() for x in ["hankinta", "tarjouspyyntö", "urakka"]):
            results.append({
                "title": text,
                "url": full_url,
                "document_url": full_url if ".pdf" in full_url else "",
                "type_hint": "urakka"
            })

    return results

# ---------- ROUTER ----------
def route_parser(url):
    url_l = url.lower()

    if "akaa.fi" in url_l:
        return parse_akaa
    if "hel.fi" in url_l:
        return parse_helsinki
    if "espoo.fi" in url_l:
        return parse_espoo
    if "vantaa.fi" in url_l:
        return parse_vantaa
    if "tampere.fi" in url_l:
        return parse_tampere

    return parse_generic
