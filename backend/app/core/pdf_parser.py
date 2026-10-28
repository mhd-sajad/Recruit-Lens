"""Production-grade PDF resume parser with layout handling, gate heuristics, and PII isolation."""

import logging
import re
from pathlib import Path
from typing import Any, Literal

import ftfy
import pdfplumber
from pypdf import PdfReader

from app.core.education_extractor import extract_education_entries
from app.core.experience_extractor import extract_structured_experiences
from app.core.models import ContactPII, ResumeParseResult

logger = logging.getLogger(__name__)

# Canonical Section Header Patterns
SECTION_HEADERS: dict[str, list[str]] = {
    "summary": [
        "summary",
        "professional summary",
        "career summary",
        "executive summary",
        "profile",
        "professional profile",
        "objective",
        "career objective",
        "about me",
    ],
    "experience": [
        "experience",
        "work experience",
        "employment history",
        "professional experience",
        "career history",
        "work history",
        "relevant experience",
        "positions held",
    ],
    "education": [
        "education",
        "educational background",
        "academic background",
        "academics",
        "qualifications",
        "academic qualifications",
        "degrees",
    ],
    "skills": [
        "skills",
        "technical skills",
        "core competencies",
        "key skills",
        "skills & competencies",
        "technologies",
        "proficiencies",
        "areas of expertise",
    ],
    "projects": [
        "projects",
        "personal projects",
        "academic projects",
        "key projects",
        "notable projects",
    ],
    "certifications": [
        "certifications",
        "certificates",
        "licenses",
        "courses",
        "professional certifications",
    ],
}

# Negative document signatures (invoices, academic papers, cover letters, meeting minutes,
# job postings, brochures, certificates)
NEGATIVE_SIGNALS = [
    r"\binvoice\s*(?:#|no|number)?\b",
    r"\bbill\s+to\b",
    r"\btax\s+invoice\b",
    r"\btotal\s+amount\s+due\b",
    r"\bpayment\s+terms\b",
    r"\babstract\b(?:\s*\n|\s*:)",
    r"\bproceedings\s+of\b",
    r"\bieee\s+transactions\b",
    r"\barxiv:\d{4}\b",
    r"\bbibliography\b",
    r"\b(?:dear\s+(?:hiring|recruitment|selection|search|sir|madam)|to\s+the\s+recruitment|to\s+whom\s+it\s+may\s+concern)\b",
    r"\b(?:sincerely|respectfully|yours\s+faithfully|warm\s+regards),?\s*\n",
    r"\b(?:meeting\s+minutes|board\s+of\s+directors\s+meeting|steering\s+committee\s+minutes)\b",
    r"\b(?:job\s+posting|hiring\s+organization|role\s+overview\s+and\s+responsibilities)\b",
    r"\b(?:product\s+brochure|solution\s+overview|technical\s+specifications\s+&\s+features)\b",
    r"\b(?:certificate\s+of\s+completion|has\s+successfully\s+completed|continuing\s+education\s+units)\b",
]


EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\b\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
LINK_REGEX = re.compile(r"https?://(?:www\.)?[a-zA-Z0-9./\-_]+")


def parse_resume_pdf(pdf_path: str | Path, resume_id: str | None = None) -> ResumeParseResult:
    """Parse a resume PDF into structured sections, PII, and clean scoring text."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF file does not exist at '{pdf_path}'")

    rid = resume_id or path.stem

    # 1. Primary extraction with pdfplumber (with multi-column reordering)
    extracted_text, page_count, layout_type = _extract_with_pdfplumber(path)

    # 2. Fallback to pypdf if pdfplumber yields empty or malformed text
    if not extracted_text.strip():
        extracted_text, page_count = _extract_with_pypdf(path)
        layout_type = "unknown"

    cleaned_text = ftfy.fix_text(extracted_text.strip())
    cleaned_text = cleaned_text.replace("\u200b", "").replace("ï¼", " - ")
    raw_text = cleaned_text

    # 3. Resume Gate Evaluation (rule-based, no LLM)
    is_resume, gate_confidence, gate_signals = evaluate_resume_gate(raw_text, page_count)

    # 4. Parse Quality Confidence Score
    parse_confidence = calculate_parse_confidence(raw_text, page_count, is_resume)

    # 5. Extract PII and construct sanitized scoring text
    pii, scoring_text = extract_and_isolate_pii(raw_text)

    # 6. Segment text into canonical sections
    sections = segment_sections(raw_text)

    # 7. Extract structured experiences and educations
    experiences = extract_structured_experiences(sections.get("experience", raw_text))
    educations = extract_education_entries(sections.get("education", raw_text))

    # 8. Extract list of skills from skills section
    skills_list = _extract_skills_list(sections.get("skills", ""))

    return ResumeParseResult(
        resume_id=rid,
        is_resume=is_resume,
        gate_confidence=gate_confidence,
        gate_signals=gate_signals,
        parse_confidence=parse_confidence,
        page_count=page_count,
        layout_type=layout_type,
        pii=pii,
        scoring_text=scoring_text,
        raw_text=raw_text,
        sections=sections,
        experiences=experiences,
        educations=educations,
        skills=skills_list,
    )


def _extract_with_pdfplumber(
    pdf_path: Path,
) -> tuple[str, int, Literal["single_column", "multi_column", "unknown"]]:
    """Extract text from PDF pages with multi-column layout detection and reordering."""
    all_pages_text: list[str] = []
    detected_layouts: list[str] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                page_text, layout = _extract_page_layout_aware(page)
                all_pages_text.append(page_text)
                detected_layouts.append(layout)

        overall_layout: Literal["single_column", "multi_column", "unknown"] = (
            "multi_column" if "multi_column" in detected_layouts else "single_column"
        )
        return "\n\n".join(all_pages_text), page_count, overall_layout
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed for {pdf_path}: {e}")
        return "", 0, "unknown"


def _extract_page_layout_aware(page: pdfplumber.page.Page) -> tuple[str, str]:
    """Detect columns on a page and order words cleanly."""
    words = page.extract_words()
    if not words:
        # Fallback to plain text extract
        plain = page.extract_text() or ""
        return plain, "single_column"

    width = page.width or 612.0
    midpoint = width / 2.0

    # Count words strictly in left half vs right half
    left_words = [w for w in words if w["x1"] <= midpoint + 20]
    right_words = [w for w in words if w["x0"] >= midpoint - 20]

    # If substantial words exist in both halves and overlap vertically, treat as 2-column
    is_multi_column = (
        len(left_words) > 25
        and len(right_words) > 25
        and abs(len(left_words) - len(right_words)) < len(words) * 0.7
    )

    if is_multi_column:
        # Sort left column top-to-bottom, then right column top-to-bottom
        left_words_sorted = sorted(left_words, key=lambda w: (w["top"], w["x0"]))
        right_words_sorted = sorted(right_words, key=lambda w: (w["top"], w["x0"]))

        left_text = _assemble_words_into_lines(left_words_sorted)
        right_text = _assemble_words_into_lines(right_words_sorted)

        return f"{left_text}\n\n{right_text}", "multi_column"

    # Single column layout: standard top-to-bottom reading order
    sorted_words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    return _assemble_words_into_lines(sorted_words), "single_column"


def _assemble_words_into_lines(words: list[dict[str, Any]], line_tolerance: float = 3.5) -> str:
    """Group words with similar 'top' coordinates into coherent lines."""
    if not words:
        return ""

    lines: list[list[dict[str, Any]]] = []
    current_line: list[dict[str, Any]] = []
    current_top = float(words[0]["top"])

    for word in words:
        word_top = float(word["top"])
        if abs(word_top - current_top) <= line_tolerance:
            current_line.append(word)
        else:
            if current_line:
                lines.append(sorted(current_line, key=lambda w: float(w["x0"])))
            current_line = [word]
            current_top = word_top

    if current_line:
        lines.append(sorted(current_line, key=lambda w: float(w["x0"])))

    line_strings = [" ".join(str(w.get("text", "")) for w in line) for line in lines]
    return "\n".join(line_strings)


def _extract_with_pypdf(pdf_path: Path) -> tuple[str, int]:
    """Fallback extraction using pypdf."""
    try:
        reader = PdfReader(str(pdf_path))
        page_count = len(reader.pages)
        pages_text = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages_text), page_count
    except Exception as e:
        logger.error(f"pypdf fallback failed for {pdf_path}: {e}")
        return "", 0


def evaluate_resume_gate(text: str, page_count: int) -> tuple[bool, float, dict[str, bool]]:
    """
    Deterministic rule-based resume gate.
    Evaluates whether a document is an authentic resume vs non-resume.
    """
    if not text or len(text.strip()) < 80:
        return False, 0.0, {"has_content": False}

    text_lower = text.lower()

    # Positive signals
    has_experience_section = any(
        re.search(r"\b" + re.escape(h) + r"\b", text_lower) for h in SECTION_HEADERS["experience"]
    )
    has_education_section = any(
        re.search(r"\b" + re.escape(h) + r"\b", text_lower) for h in SECTION_HEADERS["education"]
    )
    has_skills_section = any(
        re.search(r"\b" + re.escape(h) + r"\b", text_lower) for h in SECTION_HEADERS["skills"]
    )
    has_dates = bool(re.search(r"\b(?:19[8-9]\d|20[0-2]\d)\b", text))
    has_contact = bool(EMAIL_REGEX.search(text) or PHONE_REGEX.search(text))
    valid_length = 1 <= page_count <= 8

    # Negative signals
    negative_hits = [sig for sig in NEGATIVE_SIGNALS if re.search(sig, text_lower)]
    is_negative = len(negative_hits) >= 2 or (
        len(negative_hits) >= 1 and not has_experience_section
    )

    # Check distinct canonical section count (experience, education, skills)
    distinct_sections = sum(
        [bool(has_experience_section), bool(has_education_section), bool(has_skills_section)]
    )
    has_sufficient_sections = distinct_sections >= 2

    signals: dict[str, bool] = {
        "experience_section": has_experience_section,
        "education_section": has_education_section,
        "skills_section": has_skills_section,
        "distinct_sections_count": has_sufficient_sections,
        "date_ranges": has_dates,
        "contact_info": has_contact,
        "valid_page_length": valid_length,
        "negative_document_markers": not is_negative,
    }

    # Weight positive signals
    score = 0.0
    if has_experience_section:
        score += 0.35
    if has_education_section:
        score += 0.25
    if has_skills_section:
        score += 0.15
    if has_dates:
        score += 0.15
    if has_contact:
        score += 0.10

    if is_negative:
        score = max(0.0, score - 0.6)

    is_resume = score >= 0.40 and not is_negative and has_sufficient_sections
    return is_resume, round(score, 2), signals


def calculate_parse_confidence(text: str, page_count: int, is_resume: bool) -> float:
    """Calculate 0.0 - 1.0 confidence in the text extraction fidelity."""
    if not text or page_count == 0:
        return 0.0

    chars = len(text)
    chars_per_page = chars / page_count

    confidence = 1.0

    # Penalize suspiciously low character counts (scanned PDF / bad OCR)
    if chars_per_page < 150:
        confidence -= 0.5
    elif chars_per_page < 300:
        confidence -= 0.2

    # Penalize non-printable / replacement character corruption
    unprintable_chars = len(re.findall(r"[^\x20-\x7E\t\n\r]", text))
    unprintable_ratio = unprintable_chars / max(1, chars)
    if unprintable_ratio > 0.08:
        confidence -= 0.3

    # Penalize form template boilerplate or non-English application forms
    form_matches = len(
        re.findall(
            r"\b(?:puesto que solicita|nombre de la organizaci|t[ií]tulo del puesto|"
            r"fechas de\s*/\s*a|por favor escriba|solicitud de empleo|"
            r"informaci[oó]n de contacto|por que dejo|referencias profesionales|"
            r"habilidades:|agencia de empleo|distinci[oó]n de raza)\b",
            text,
            re.IGNORECASE,
        )
    )
    if form_matches >= 2:
        confidence = min(confidence, 0.35)

    if not is_resume:
        confidence = min(confidence, 0.3)

    return max(0.0, min(1.0, round(confidence, 2)))


def extract_and_isolate_pii(text: str) -> tuple[ContactPII, str]:
    """
    Extract personal contact information into an isolated PII object
    and return sanitized scoring text for blind review and unbiased matching.
    """
    emails = EMAIL_REGEX.findall(text)
    phones = PHONE_REGEX.findall(text)
    links = LINK_REGEX.findall(text)

    email = emails[0] if emails else None
    phone = phones[0] if phones else None

    # Name heuristic: inspect first 3 non-empty lines before section headers
    lines = [raw_line.strip() for raw_line in text.split("\n") if raw_line.strip()]
    candidate_name = None
    for line in lines[:4]:
        # Filter lines that look like headers or emails
        if EMAIL_REGEX.search(line) or PHONE_REGEX.search(line) or LINK_REGEX.search(line):
            continue
        if any(h in line.lower() for h in ("resume", "curriculum", "vitae", "summary", "profile")):
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(re.match(r"^[A-Za-z.'-]+$", w) for w in words):
            candidate_name = line
            break

    pii = ContactPII(
        name=candidate_name,
        email=email,
        phone=phone,
        links=links[:5],
    )

    # Sanitize text for unbiased scoring
    sanitized = text
    if email:
        sanitized = re.sub(re.escape(email), "[CANDIDATE_EMAIL]", sanitized)
    if phone:
        sanitized = re.sub(re.escape(phone), "[CANDIDATE_PHONE]", sanitized)
    if candidate_name:
        sanitized = re.sub(r"\b" + re.escape(candidate_name) + r"\b", "[CANDIDATE_NAME]", sanitized)

    return pii, sanitized


def segment_sections(text: str) -> dict[str, str]:
    """Segment raw resume text into named section blocks based on header matches."""
    lines = text.split("\n")
    sections: dict[str, list[str]] = {}
    current_section = "summary"
    sections[current_section] = []

    # Map header strings to section keys
    header_map: dict[str, str] = {}
    for sec_key, headers in SECTION_HEADERS.items():
        for h in headers:
            header_map[h] = sec_key

    for line in lines:
        stripped = line.strip().lower()
        cleaned_header = re.sub(r"[:\-_|•*]", "", stripped).strip()

        matched_section = None
        for h_str, sec_key in header_map.items():
            if cleaned_header == h_str or cleaned_header.startswith(h_str + " "):
                matched_section = sec_key
                break

        if matched_section and len(cleaned_header) < 45:
            current_section = matched_section
            if current_section not in sections:
                sections[current_section] = []
        else:
            sections[current_section].append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def _extract_skills_list(skills_text: str) -> list[str]:
    """Extract individual skill keywords from the skills section."""
    if not skills_text:
        return []

    # Split on commas, bullets, newlines, or semicolons
    raw_tokens = re.split(r"[,;•\n\t|/]", skills_text)
    clean_skills: set[str] = set()

    for token in raw_tokens:
        tok = token.strip(" -–—*•")
        # Remove parenthetical descriptions like "Python (5 years)"
        tok = re.sub(r"\([^)]*\)", "", tok).strip()
        if 2 <= len(tok) <= 35 and not re.search(
            r"\b(experience|proficient|skills?|knowledge)\b", tok, re.IGNORECASE
        ):
            clean_skills.add(tok)

    return sorted(clean_skills)
