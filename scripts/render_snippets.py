import io
import json
import re
from pathlib import Path

import pytesseract
import requests
from pdf2image import convert_from_bytes
from PIL import Image

PROCUREMENTS_FILE = "data/procurements.json"
SNIPPETS_DIR = Path("data/snippets")

SNIPPETS_DIR.mkdir(parents=True, exist_ok=True)

def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def safe_filename(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "_", value)
    return value[:120]

def pick_target_phrase(item):
    title = (item.get("title") or "").strip()
    if title and len(title) >= 4:
        return title

    kws = item.get("matched_keywords") or []
    if kws:
        return kws[0]

    return ""

def crop_with_padding(img: Image.Image, box, pad=30):
    left, top, right, bottom = box
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(img.width, right + pad)
    bottom = min(img.height, bottom + pad)
    return img.crop((left, top, right, bottom))

def ocr_words_with_boxes(img: Image.Image):
    data = pytesseract.image_to_data(
        img,
        lang="fin+eng",
        output_type=pytesseract.Output.DICT
    )

    words = []
    n = len(data["text"])
    for i in range(n):
        text = (data["text"][i] or "").strip()
        if not text:
            continue
        left = int(data["left"][i])
        top = int(data["top"][i])
        width = int(data["width"][i])
        height = int(data["height"][i])
        words.append({
            "text": text,
            "norm": re.sub(r"\s+", " ", text.lower()).strip(),
            "left": left,
            "top": top,
            "right": left + width,
            "bottom": top + height,
        })
    return words

def find_phrase_box(words, phrase):
    phrase_words = [re.sub(r"[^a-zåäö0-9-]+", "", w.lower()) for w in phrase.split()]
    phrase_words = [w for w in phrase_words if w]
    if not phrase_words:
        return None

    norms = [re.sub(r"[^a-zåäö0-9-]+", "", w["norm"]) for w in words]

    best = None

    for i in range(len(norms)):
        matched = 0
        for j, target in enumerate(phrase_words):
            if i + j >= len(norms):
                break
            if target and target in norms[i + j]:
                matched += 1
            else:
                break

        if matched >= max(1, min(2, len(phrase_words))):
            start = i
            end = i + matched - 1
            left = min(words[k]["left"] for k in range(start, end + 1))
            top = min(words[k]["top"] for k in range(start, end + 1))
            right = max(words[k]["right"] for k in range(start, end + 1))
            bottom = max(words[k]["bottom"] for k in range(start, end + 1))
            best = (left, top, right, bottom)
            break

    if best:
        return best

    phrase_l = phrase.lower()
    for w in words:
        if phrase_l in w["norm"]:
            return (w["left"], w["top"], w["right"], w["bottom"])

    return None

def render_pdf_snippet(document_url, phrase, out_path):
    try:
        r = requests.get(
            document_url,
            timeout=60,
            headers={"User-Agent": "Mozilla/5.0 HankintaSeurantaBot/1.0"}
        )
        r.raise_for_status()

        pages = convert_from_bytes(r.content, dpi=170, first_page=1, last_page=6)

        for page_index, img in enumerate(pages, start=1):
            words = ocr_words_with_boxes(img)
            box = find_phrase_box(words, phrase)
            if box:
                snippet = crop_with_padding(img, box, pad=80)
                snippet.save(out_path, format="PNG")
                return {
                    "snippet_image": str(out_path).replace("\\", "/"),
                    "snippet_page": page_index
                }

        return {}
    except Exception:
        return {}

def render_image_snippet(document_url, phrase, out_path):
    try:
        r = requests.get(
            document_url,
            timeout=60,
            headers={"User-Agent": "Mozilla/5.0 HankintaSeurantaBot/1.0"}
        )
        r.raise_for_status()

        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        words = ocr_words_with_boxes(img)
        box = find_phrase_box(words, phrase)
        if box:
            snippet = crop_with_padding(img, box, pad=80)
            snippet.save(out_path, format="PNG")
            return {
                "snippet_image": str(out_path).replace("\\", "/"),
                "snippet_page": 1
            }

        return {}
    except Exception:
        return {}

def looks_like_image(url: str) -> bool:
    u = (url or "").lower()
    return any(u.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"])

def main():
    items = load_json(PROCUREMENTS_FILE, [])

    for item in items:
        if not item.get("generated_from_attachment"):
            continue
        if item.get("snippet_image"):
            continue

        phrase = pick_target_phrase(item)
        document_url = item.get("document_url", "")
        if not phrase or not document_url:
            continue

        filename = safe_filename(item.get("id", "snippet")) + ".png"
        out_path = SNIPPETS_DIR / filename

        result = {}
        if document_url.lower().endswith(".pdf"):
            result = render_pdf_snippet(document_url, phrase, out_path)
        elif looks_like_image(document_url):
            result = render_image_snippet(document_url, phrase, out_path)

        if result:
            item.update(result)

    save_json(PROCUREMENTS_FILE, items)

if __name__ == "__main__":
    main()
