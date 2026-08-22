"""Parse resume text into candidate field suggestions."""

from __future__ import annotations

import re
from decimal import Decimal


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}")
EXPERIENCE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:\+?\s*)?(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)?",
    re.IGNORECASE,
)


def parse_resume_text(text: str) -> dict:
    """Extract likely candidate fields from resume plain text."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    preview = text[:8000]

    emails = EMAIL_RE.findall(preview)
    phones = PHONE_RE.findall(preview)

    first_name = ""
    last_name = ""
    if lines:
        name_line = lines[0]
        if "@" not in name_line and not name_line.lower().startswith(("resume", "curriculum")):
            parts = re.split(r"\s+", name_line)
            if 1 <= len(parts) <= 4 and all(p.replace(".", "").isalpha() for p in parts[:2]):
                first_name = parts[0].title()
                last_name = " ".join(p.title() for p in parts[1:])

    current_company = None
    current_designation = None
    for i, line in enumerate(lines[:30]):
        lower = line.lower()
        if any(k in lower for k in ("experience", "work history", "employment")):
            if i + 1 < len(lines):
                current_designation = lines[i + 1][:255]
            if i + 2 < len(lines):
                current_company = lines[i + 2][:255]
            break

    exp_match = EXPERIENCE_RE.search(preview)
    total_experience = Decimal(exp_match.group(1)) if exp_match else None

    skills: list[str] = []
    for i, line in enumerate(lines):
        if line.lower().startswith("skills"):
            block = " ".join(lines[i : i + 5])
            skills = [s.strip() for s in re.split(r"[,|•·]", block) if s.strip()][:15]
            break

    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": emails[0] if emails else "",
        "phone": phones[0] if phones else "",
        "current_company": current_company,
        "current_designation": current_designation,
        "total_experience_years": float(total_experience) if total_experience else None,
        "parsed_profile": {"skills": skills, "emails_found": emails[:3], "phones_found": phones[:3]},
    }
