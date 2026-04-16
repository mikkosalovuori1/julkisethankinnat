import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

import json
import requests
from datetime import datetime
from parsers import route_parser
from pdf_extract import extract_pdf_text
from ocr_extract import extract_text_from_pdf_ocr, extract_text_from_image_bytes

SOURCES_FILE = "data/sources.json"
PROCUREMENTS_FILE = "data/procurements.json"

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"]

def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def looks_like_image(url: str) -> bool:
    url_l = (url or "").lower()
    return any(url_l.endswith(ext) for ext in IMAGE_EXTENSIONS)

def download_image_bytes(url: str) -> bytes:
    r = requests.get(
        url,
        timeout=45,
        headers={"User-Agent": "Mozilla/5.0 HankintaSeurantaBot/1.0"}
    )
    r.raise_for_status()
    return r.content

with open(SOURCES_FILE, "r", encoding="utf-8") as f:
    sources = json.load(f)

old_items = load_json(PROCUREMENTS_FILE, [])
old_by_url = {item.get("url"): item for item in old_items if item.get("url")}

results = []

for source in sources:
    entity_name = source["name"]
    area_name = source.get("area", "")
    source_name = source.get("source_name", "Website")

    for url in source["urls"]:
        try:
            r = requests.get(
                url,
                timeout=30,
                headers={"User-Agent": "Mozilla/5.0 HankintaSeurantaBot/1.0"}
            )
            r.raise_for_status()

            parser = route_parser(url)
            items = parser(url, r.text)

            for p in items:
                full_url = p["url"]
                old_item = old_by_url.get(full_url)

                document_url = p.get("document_url", "")
                pdf_text = old_item.get("pdf_text", "") if old_item else ""

                if document_url and document_url.lower().endswith(".pdf"):
                    normal_text = extract_pdf_text(document_url)
                    pdf_text = normal_text

                    normalized = (normal_text or "").strip()
                    # Jos tavallista tekstiä ei juuri tullut, ajetaan OCR
                    if (
                        not normalized
                        or normalized.startswith("PDF_ERROR")
                        or normalized.startswith("PDF_EXTRACT_ERROR")
                        or len(normalized) < 300
                    ):
                        ocr_text = extract_text_from_pdf_ocr(document_url)
                        if ocr_text and not ocr_text.startswith("OCR_PDF_ERROR"):
                            if normalized and not normalized.startswith("PDF_ERROR") and not normalized.startswith("PDF_EXTRACT_ERROR"):
                                pdf_text = (normalized + "\n\n--- OCR ---\n\n" + ocr_text)[:30000]
                            else:
                                pdf_text = ocr_text

                elif document_url and looks_like_image(document_url):
                    try:
                        img_bytes = download_image_bytes(document_url)
                        img_text = extract_text_from_image_bytes(img_bytes)
                        pdf_text = img_text
                    except Exception as e:
                        pdf_text = f"OCR_IMAGE_DOWNLOAD_ERROR: {str(e)}"

                results.append({
                    "id": full_url,
                    "entity": entity_name,
                    "unit_name": entity_name,
                    "area": area_name,
                    "source_name": source_name,
                    "source_page": url,
                    "title": p.get("title") or full_url,
                    "url": full_url,
                    "document_url": document_url,
                    "type_hint": p.get("type_hint", ""),
                    "pdf_text": pdf_text,
                    "found_at": old_item.get("found_at") if old_item else datetime.utcnow().isoformat() + "Z",
                    "last_seen_at": datetime.utcnow().isoformat() + "Z",
                    "is_new": old_item is None
                })

        except Exception as e:
            results.append({
                "id": f"{entity_name}-{url}",
                "entity": entity_name,
                "unit_name": entity_name,
                "area": area_name,
                "source_name": source_name,
                "source_page": url,
                "title": f"ERROR: {e}",
                "url": url,
                "document_url": "",
                "type_hint": "",
                "pdf_text": "",
                "found_at": datetime.utcnow().isoformat() + "Z",
                "last_seen_at": datetime.utcnow().isoformat() + "Z",
                "is_new": False
            })

unique = {}
for item in results:
    key = item["url"]
    if key not in unique:
        unique[key] = item

results = list(unique.values())

with open(PROCUREMENTS_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
