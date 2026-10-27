"""Experience, seniority, and structured work history extractor."""

import logging
import re

from app.core.models import WorkExperienceEntry

logger = logging.getLogger(__name__)

# Seniority level ordinal rankings
SENIORITY_LEVELS: dict[str, int] = {
    "entry-level": 0,
    "junior": 0,
    "associate": 0,
    "intern": 0,
    "trainee": 0,
    "mid-level": 1,
    "mid": 1,
    "specialist": 1,
    "senior": 2,
    "sr": 2,
    "staff": 3,
    "lead": 3,
    "team lead": 3,
    "principal": 4,
    "director": 4,
    "head": 4,
    "chief": 4,
    "vp": 4,
}

# Domain title marker tokens across industry categories
COMMON_TITLE_MARKERS = {
    "engineer",
    "developer",
    "manager",
    "lead",
    "analyst",
    "consultant",
    "specialist",
    "architect",
    "designer",
    "director",
    "officer",
    "administrator",
    "intern",
    "associate",
    "coordinator",
    "accountant",
    "chef",
    "representative",
    "nurse",
    "teacher",
    "supervisor",
    "technician",
    "executive",
    "assistant",
    "pilot",
    "driver",
    "advocate",
    "counsel",
    "operator",
    "auditor",
    "scientist",
    "programmer",
    "instructor",
    "clerk",
    "therapist",
    "recruiter",
    "strategist",
}

# Date interval regex covering "01/2015 to Current", "Jan 2018 - Dec 2021", "2016 – 2020"
DATE_RANGE_REGEX = re.compile(
    r"(?P<start>(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(?:\d{1,2}[/-])?(?:19[7-9]\d|20[0-2]\d))\s*"
    r"(?:to|-|–|—)\s*"
    r"(?P<end>(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(?:\d{1,2}[/-])?(?:19[7-9]\d|20[0-2]\d)|current|present)",
    re.IGNORECASE,
)


def extract_years_of_experience(text: str) -> float | None:
    """
    Extract total numerical years of experience.
    Combines explicit "X years of experience" statements with date interval summation.
    """
    if not text:
        return None

    explicit_years: list[float] = []

    # 1. Match explicit statements: "5+ years", "3-5 years experience"
    explicit_pat = (
        r"(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\+?\s*years?(?:\s+of)?(?:\s+experience)?"
    )
    for m in re.finditer(explicit_pat, text, re.IGNORECASE):
        after_context = text[m.end() : min(len(text), m.end() + 30)].lower()
        if any(
            w in after_context for w in ("college", "university", "degree", "school", "old", "age")
        ):
            continue
        val1 = float(m.group(1))
        val2 = float(m.group(2)) if m.group(2) else val1
        if 0 < val1 <= 50:
            explicit_years.append(max(val1, val2))

    # 2. Date interval summation across work experience text
    summed_years = _calculate_years_from_date_ranges(text)

    candidates = explicit_years + ([summed_years] if summed_years > 0 else [])
    return max(candidates) if candidates else None


def _calculate_years_from_date_ranges(text: str) -> float:
    """Calculate approximate cumulative experience from date range patterns."""
    year_regex = re.compile(r"\b(19[7-9]\d|20[0-2]\d)\b")
    total_months = 0

    for m in DATE_RANGE_REGEX.finditer(text):
        start_str = m.group("start")
        end_str = m.group("end")

        start_years = year_regex.findall(start_str)
        if not start_years:
            continue
        start_year = int(start_years[0])

        if re.search(r"current|present", end_str, re.IGNORECASE):
            end_year = 2026
        else:
            end_years = year_regex.findall(end_str)
            if not end_years:
                continue
            end_year = int(end_years[0])

        diff_years = max(0, min(30, end_year - start_year))
        total_months += diff_years * 12

    return round(total_months / 12.0, 1)


def extract_seniority_level(title_text: str, years: float | None = None) -> int:
    """
    Extract ordinal seniority level (0-4) from a title string with fallback to years.
    0=Junior/Entry, 1=Mid, 2=Senior, 3=Lead, 4=Principal/Staff.
    """
    if title_text:
        title_lower = title_text.lower()
        for keyword, level in sorted(SENIORITY_LEVELS.items(), key=lambda x: -len(x[0])):
            if re.search(r"\b" + re.escape(keyword) + r"\b", title_lower):
                return level

    if years is not None:
        if years < 2.0:
            return 0
        elif years < 5.0:
            return 1
        elif years < 8.0:
            return 2
        elif years < 12.0:
            return 3
        else:
            return 4

    return 0


def extract_structured_experiences(experience_text: str) -> list[WorkExperienceEntry]:
    """
    Decompose unstructured work experience text into structured job entries
    (title, company, start, end, bullets).
    """
    if not experience_text or not experience_text.strip():
        return []

    lines = [line.strip() for line in experience_text.split("\n") if line.strip()]
    if not lines:
        return []

    entries: list[WorkExperienceEntry] = []
    current_block: list[str] = []

    for line in lines:
        # Check if line contains a job date interval, marking a new employment block
        is_date_line = bool(DATE_RANGE_REGEX.search(line))
        has_title_marker = any(
            re.search(r"\b" + m + r"\b", line.lower()) for m in COMMON_TITLE_MARKERS
        )

        if (is_date_line or has_title_marker) and current_block and len(current_block) >= 2:
            # Parse accumulated block
            entry = _parse_single_experience_block(current_block)
            if entry and (entry.title or entry.company):
                entries.append(entry)
            current_block = [line]
        else:
            current_block.append(line)

    if current_block:
        entry = _parse_single_experience_block(current_block)
        if entry and (entry.title or entry.company):
            entries.append(entry)

    return entries


def _parse_single_experience_block(lines: list[str]) -> WorkExperienceEntry | None:
    """Extract fields from lines forming a single employment block."""
    full_block = "\n".join(lines)
    date_match = DATE_RANGE_REGEX.search(full_block)

    start_date = None
    end_date = None
    is_current = False

    if date_match:
        start_date = date_match.group("start").strip()
        end_date = date_match.group("end").strip()
        is_current = bool(re.search(r"current|present", end_date, re.IGNORECASE))

    # Identify header lines (first 1-3 lines usually contain title, company, dates)
    header_candidates = lines[:3]
    detected_title = None
    detected_company = None
    bullet_lines: list[str] = []

    for _idx, line in enumerate(header_candidates):
        # Remove date segment from header text to isolate title and company
        cleaned_line = DATE_RANGE_REGEX.sub("", line).strip()
        cleaned_line = re.sub(r"\s+", " ", cleaned_line).strip(" ,|–-—")

        if not cleaned_line:
            continue

        # Check delimiters like "Title , Company" or "Company - Title" or "Title at Company"
        delims = [" at ", " @ ", " - ", " – ", " — ", " | ", " , "]
        found_split = False
        for d in delims:
            if d in cleaned_line:
                parts = [p.strip() for p in cleaned_line.split(d) if p.strip()]
                if len(parts) >= 2:
                    p1, p2 = parts[0], parts[1]
                    # Disambiguate which part is the title vs company
                    p1_is_title = any(
                        re.search(r"\b" + m + r"\b", p1.lower()) for m in COMMON_TITLE_MARKERS
                    )
                    p2_is_title = any(
                        re.search(r"\b" + m + r"\b", p2.lower()) for m in COMMON_TITLE_MARKERS
                    )

                    if p1_is_title and not p2_is_title:
                        detected_title = p1
                        detected_company = p2
                    elif p2_is_title and not p1_is_title:
                        detected_title = p2
                        detected_company = p1
                    elif detected_title:
                        # Existing title already recognized; treat first part as company
                        detected_company = p1
                    else:
                        detected_title = p1
                        detected_company = p2

                    found_split = True
                    break

        if not found_split:
            # Check if standalone line is a title or company
            if not detected_title and any(
                re.search(r"\b" + m + r"\b", cleaned_line.lower()) for m in COMMON_TITLE_MARKERS
            ):
                detected_title = cleaned_line
            elif not detected_company:
                detected_company = cleaned_line

    # Collect bullet points (remaining lines or lines with bullet characters)
    start_bullet_idx = 1 if detected_title and detected_company else 2
    for line in lines[start_bullet_idx:]:
        stripped = line.strip(" •*-–—\t")
        if len(stripped) > 10:
            bullet_lines.append(stripped)

    # Clean extracted company name from noisy city/state suffixes
    if detected_company:
        detected_company = re.sub(
            r"(?:city|state|location|remote|incorporated|llc)\b",
            "",
            detected_company,
            flags=re.IGNORECASE,
        ).strip(" ,–-—")

    return WorkExperienceEntry(
        title=detected_title,
        company=detected_company if detected_company else "Organization",
        start_date=start_date,
        end_date=end_date,
        is_current=is_current,
        bullets=bullet_lines,
        raw_text=full_block,
    )
