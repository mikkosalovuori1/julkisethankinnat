import io
import requests
from pypdf import PdfReader

def extract_pdf_text(url):
    try:
        r = requests.get(
            url,
            timeout=45,
            headers={"User-Agent": "Mozilla/5.0 HankintaSeurantaBot/1.0"}
        )
        r.raise_for_status()

        pdf_file = io.BytesIO(r.content)
        reader = PdfReader(pdf_file)

        texts = []

        for i, page in enumerate(reader.pages):
            if i >= 10:
                break
            try:
                text = page.extract_text()
                if text:
                    texts.append(text)
            except Exception:
                continue

        full_text = "\n\n".join(texts)
        return full_text[:10000]

    except Exception as e:
        return f"PDF_ERROR: {str(e)}"
