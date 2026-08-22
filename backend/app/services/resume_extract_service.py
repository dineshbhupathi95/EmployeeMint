"""Extract plain text from resume uploads with clear errors."""

from __future__ import annotations

import os

from app.services.policy_file_extract import extract_policy_text

RESUME_EXTENSIONS = (".pdf", ".docx", ".txt", ".md", ".markdown")
LEGACY_DOC_EXT = ".doc"


def normalize_resume_filename(filename: str | None) -> str:
    name = (filename or "resume.pdf").strip()
    if not os.path.splitext(name)[1]:
        return f"{name}.pdf"
    return name


def validate_resume_upload(filename: str, content: bytes) -> None:
    if not content:
        raise ValueError("Uploaded file is empty")
    lower = filename.lower()
    if lower.endswith(LEGACY_DOC_EXT):
        raise ValueError(
            "Legacy .doc files are not supported. Save as .docx or .pdf and upload again."
        )
    if not any(lower.endswith(ext) for ext in RESUME_EXTENSIONS):
        raise ValueError(
            f"Unsupported resume format. Use one of: {', '.join(RESUME_EXTENSIONS)}"
        )


def extract_resume_text(filename: str | None, content: bytes) -> str:
    """Extract text from a resume file; raises ValueError with a user-facing message."""
    normalized = normalize_resume_filename(filename)
    validate_resume_upload(normalized, content)
    try:
        text = extract_policy_text(normalized, content)
    except ValueError:
        raise
    except Exception as exc:
        lower = normalized.lower()
        if lower.endswith(".pdf"):
            raise ValueError(
                "Could not read this PDF. It may be scanned/image-only — try a text-based PDF or DOCX."
            ) from exc
        if lower.endswith(".docx"):
            raise ValueError(
                "Could not read this DOCX file. Re-save it in Word or upload a PDF instead."
            ) from exc
        raise ValueError(f"Could not read resume file: {exc}") from exc

    if not text.strip():
        raise ValueError(
            "No text could be extracted from this file. Use a text-based PDF or DOCX, not a scanned image."
        )
    return text.strip()
