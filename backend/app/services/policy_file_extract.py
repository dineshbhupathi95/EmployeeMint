"""Extract plain text from uploaded policy files."""

from __future__ import annotations

from io import BytesIO


def extract_policy_text(filename: str, data: bytes) -> str:
    name = (filename or "document").lower()
    if name.endswith((".txt", ".md", ".markdown", ".csv", ".log")):
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                text = data.decode(encoding)
                break
            except UnicodeDecodeError:
                text = ""
        else:
            text = data.decode("utf-8", errors="ignore")
        return text.strip()

    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = "\n".join(pages).strip()
        if not text:
            raise ValueError("Could not extract text from this PDF (it may be scanned/image-only).")
        return text

    if name.endswith((".docx",)):
        try:
            from docx import Document  # type: ignore
        except ImportError as exc:
            raise ValueError("DOCX support requires python-docx. Upload TXT/MD/PDF instead.") from exc
        doc = Document(BytesIO(data))
        text = "\n".join(p.text for p in doc.paragraphs if p.text).strip()
        if not text:
            raise ValueError("DOCX file has no extractable text.")
        return text

    raise ValueError("Unsupported file type. Use .txt, .md, .csv, .pdf, or .docx")
