"""Education level and career chronology extraction module."""

import re

from app.core.models import EducationEntry

# Ordinal ranking for degrees: 4=Doctorate, 3=Master's, 2=Bachelor's, 1=Associate, 0=High School
DEGREE_PATTERNS: list[tuple[str, int, str]] = [
    # Doctorate (Rank 4)
    (r"\b(?:ph\.?d|doctorate|doctor of philosophy|m\.?d\.?|ed\.?d\.?|d\.?sc\.?)\b", 4, "Doctorate"),
    # Master's (Rank 3)
    (
        r"\b(?:master(?:'s)?(?:\s+of\s+science|\s+of\s+arts|\s+of\s+engineering|\s+of\s+business)?"
        r"|m\.?s\.?|m\.?a\.?|m\.?sc\.?|m\.?tech\.?|mtech|mba|mca|m\.?com|m\.?eng|dipl\.?-ing\.?)\b",
        3,
        "Master's Degree",
    ),
    # Bachelor's (Rank 2)
    (
        r"\b(?:bachelor(?:'s)?(?:\s+of\s+science|\s+of\s+arts|\s+of\s+engineering|\s+of\s+technology)?"
        r"|b\.?s\.?|b\.?a\.?|b\.?sc\.?|b\.?tech\.?|btech|b\.?e\.?|b\.?eng|bca|bba|b\.?com|llb|mbbs)\b",
        2,
        "Bachelor's Degree",
    ),
    # Associate (Rank 1)
    (r"\b(?:associate(?:'s)?(?:\s+degree)?|a\.?s\.?|a\.?a\.?|aas)\b", 1, "Associate Degree"),
    # High School / Secondary (Rank 0)
    (
        r"\b(?:high\s+school|ged|secondary\s+school|higher\s+secondary|matriculation|10\+2)\b",
        0,
        "High School",
    ),
]

YEAR_REGEX = re.compile(r"\b(19[7-9]\d|20[0-2]\d)\b")


def extract_highest_education_level(text: str) -> int:
    """Extract highest ordinal education rank found in text."""
    if not text:
        return 0

    text_lower = text.lower()
    highest_rank = 0

    for pattern, rank, _ in DEGREE_PATTERNS:
        if re.search(pattern, text_lower):
            if rank > highest_rank:
                highest_rank = rank

    return highest_rank


def extract_education_entries(education_section_text: str) -> list[EducationEntry]:
    """Parse structured education entries from education section text."""
    if not education_section_text or not education_section_text.strip():
        return []

    entries: list[EducationEntry] = []
    lines = [line.strip() for line in education_section_text.split("\n") if line.strip()]

    current_entry_lines: list[str] = []

    for line in lines:
        # Detect if line starts a new degree block
        has_degree = any(re.search(pat, line.lower()) for pat, _, _ in DEGREE_PATTERNS)
        if has_degree and current_entry_lines:
            entry = _build_education_entry("\n".join(current_entry_lines))
            if entry:
                entries.append(entry)
            current_entry_lines = [line]
        else:
            current_entry_lines.append(line)

    if current_entry_lines:
        entry = _build_education_entry("\n".join(current_entry_lines))
        if entry:
            entries.append(entry)

    return entries


def _build_education_entry(block_text: str) -> EducationEntry | None:
    """Construct an EducationEntry from an extracted block of text."""
    block_lower = block_text.lower()

    detected_rank = 0
    detected_degree_name = None

    for pattern, rank, degree_name in DEGREE_PATTERNS:
        if re.search(pattern, block_lower):
            if rank >= detected_rank:
                detected_rank = rank
                detected_degree_name = degree_name

    year_match = YEAR_REGEX.findall(block_text)
    graduation_year = int(year_match[-1]) if year_match else None

    # Institution heuristics: lines or segments containing University, College, Institute, School
    lines = [raw_line.strip() for raw_line in block_text.split("\n") if raw_line.strip()]
    institution = None
    field_of_study = None

    inst_regex = re.compile(
        r"(?:university|college|institute|polytechnic|academy|school|faculty)", re.IGNORECASE
    )

    for line in lines:
        if inst_regex.search(line):
            institution = line.split(",")[0].strip()
            break

    # Field of study: e.g. "in Computer Science", "of Science in Economics"
    field_match = re.search(
        r"(?:in|of)\s+([A-Za-z\s&]+?)(?:,|\n|–|-|\d{4}|$)", block_text, re.IGNORECASE
    )
    if field_match:
        cand_field = field_match.group(1).strip()
        if len(cand_field) > 2 and len(cand_field.split()) <= 5:
            field_of_study = cand_field

    return EducationEntry(
        degree=detected_degree_name,
        institution=institution,
        field_of_study=field_of_study,
        graduation_year=graduation_year,
        ordinal_rank=detected_rank,
        raw_text=block_text.strip(),
    )


def detect_career_gap(experience_text: str, threshold_months: int = 6) -> int:
    """
    Detect significant gaps between consecutive employment date intervals.
    Returns the maximum gap duration in months (or 0 if no gap >= threshold_months).
    """
    if not experience_text:
        return 0

    range_regex = re.compile(
        r"(?P<start>(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(?:19[7-9]\d|20[0-2]\d))\s*"
        r"(?:to|-|–|—)\s*"
        r"(?P<end>(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(?:19[7-9]\d|20[0-2]\d)|current|present)",
        re.IGNORECASE,
    )

    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    year_regex = re.compile(r"\b(19[7-9]\d|20[0-2]\d)\b")
    month_regex = re.compile(
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", re.IGNORECASE
    )

    def _parse_month_year(date_str: str, default_month: int) -> int | None:
        years = year_regex.findall(date_str)
        if not years:
            return None
        year = int(years[0])
        m_match = month_regex.findall(date_str)
        month = month_map.get(m_match[0].lower(), default_month) if m_match else default_month
        return year * 12 + month

    intervals: list[tuple[int, int]] = []
    for m in range_regex.finditer(experience_text):
        start_str = m.group("start")
        end_str = m.group("end")

        start_val = _parse_month_year(start_str, default_month=1)
        if start_val is None:
            continue

        end_val: int | None = None
        if re.search(r"current|present", end_str, re.IGNORECASE):
            end_val = 2026 * 12 + 10
        else:
            end_val = _parse_month_year(end_str, default_month=12)

        if end_val is not None:
            intervals.append((start_val, end_val))

    if len(intervals) < 2:
        return 0

    # Sort intervals chronologically by start date
    intervals.sort(key=lambda x: x[0])

    max_gap = 0
    # Measure gap between end of job i and start of job i+1
    for i in range(len(intervals) - 1):
        prev_end = intervals[i][1]
        next_start = intervals[i + 1][0]
        gap = next_start - prev_end
        if gap >= threshold_months:
            if gap > max_gap:
                max_gap = gap

    return max_gap
