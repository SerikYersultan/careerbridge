import io
import pdfplumber


class PDFExtractionError(Exception):
    pass


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise PDFExtractionError("No text found (scanned PDF? OCR not supported)")
        return text
    except PDFExtractionError:
        raise
    except Exception as e:
        raise PDFExtractionError(f"Failed to parse PDF: {e}")
