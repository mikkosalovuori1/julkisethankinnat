import io
import requests
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

MAX_PDF_PAGES = 8
MAX_TEXT_CHARS = 20000

def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang="fin+eng")
        return text[:MAX_TEXT_CHARS]
    except Exception as e:
        return f"OCR_IMAGE_ERROR: {str(e)}"

def extract_text_from_pdf_ocr(url: str) -> str:
    try:
        r = requests.get(
            url,
            timeout=60,
            headers={"User-Agent": "Mozilla/5.0 HankintaSeurantaBot/1.0"}
        )
        r.raise_for_status()

        images = convert_from_bytes(r.content, dpi=200, first_page=1, last_page=MAX_PDF_PAGES)
        texts = []

        for img in images[:MAX_PDF_PAGES]:
            try:
                page_text = pytesseract.image_to_string(img, lang="fin+eng")
                if page_text and page_text.strip():
                    texts.append(page_text.strip())
            except Exception:
                continue

        full_text = "\n\n".join(texts).strip()
        return full_text[:MAX_TEXT_CHARS]

    except Exception as e:
        return f"OCR_PDF_ERROR: {str(e)}"
