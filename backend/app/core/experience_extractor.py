"""Experience, seniority, and structured work history extractor."""

import logging
import re

import ftfy

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
    "cashier",
    "attendant",
    "teller",
    "cook",
    "laborer",
    "worker",
    "mechanic",
    "machinist",
    "salesman",
    "salesperson",
    "estimator",
    "controller",
    "cfo",
    "vp",
    "president",
    "superintendent",
    "partner",
    "founder",
    "head",
}

# Common action verbs starting bullet points / sentences (not job entries)
ACTION_VERBS = re.compile(
    r"^(?:completed|managed|supervised|provided|prepared|assisted|led|developed|designed|"
    r"implemented|created|responsible for|handled|conducted|coordinated|resolved|reviewed|"
    r"oversaw|monitored|maintained|built|formulated|executed|organized|generated|facilitated|"
    r"analyzed|operated|scheduled|achieved|promoted|collaborated|administered|performed|"
    r"consistently|billed|instructed|trained|enforced|negotiated|inspected|strengthened|"
    r"relayed|assessed|logged|introduced|aided|fulfilled|properly|accumulated|emptied|"
    r"moved|lifted|stood|walked|supported|worked|partnered|located|spearheaded|conceptualized|"
    r"revitalized|encouraged|defined|upheld|represented|set|acted as|reported|ensured|"
    r"served|established|helped|delivered|directed|participated|identified|verified|"
    r"forwarded|underwrote|drafted|collaborates|spearheads|leads|supervises|manages|"
    r"as\s+[a-z\s]+,\s*(?:i\b|my\b|responsibilities\b|was\b))\b",
    re.IGNORECASE,
)

SPANISH_TEMPLATE_REGEX = re.compile(
    r"\b(?:puesto que solicita|nombre de la organizaci|t[ií]tulo del puesto|fechas de\s*/\s*a|"
    r"por favor escriba|solicitud de empleo|informaci[oó]n de contacto|por que dejo|"
    r"referencias profesionales|habilidades:|agencia de empleo|distinci[oó]n de raza)\b",
    re.IGNORECASE,
)

PLACEHOLDER_REGEX = re.compile(
    r"\[(?:machine type|number|analysis type|company name|city|state)[^\]]*\]|"
    r"\bcompany name\b|\bcity\s*,\s*state\b|\bcity\s*state\b|ï¼\u200b|ï¼",
    re.IGNORECASE,
)

METRIC_BULLET_REGEX = re.compile(
    r"\b(?:\d+%\s*(?:increase|growth|reduction|improvement)|"
    r"\$\d+[\d,.]*\s*(?:million|billion|gross|revenue|budget|operating|expenses|monthly)?|"
    r"YoY|MoM)\b",
    re.IGNORECASE,
)

SECTION_NOISE_TOKENS = {
    "interests",
    "hobbies",
    "codes",
    "affiliations",
    "publications",
    "activities",
    "honors",
    "awards",
    "references",
    "accomplishments",
    "certifications",
    "skills",
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


def clean_header_text(text: str) -> str:
    """Clean broken encoding, placeholders, and noisy prefixes from text."""
    t = ftfy.fix_text(text)
    t = t.replace("\u200b", "").replace("ï¼", " - ")
    t = PLACEHOLDER_REGEX.sub("", t)
    t = re.sub(r"^(?:city\s*,\s*)?state\s+", "", t.strip(" ,–-—|"), flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip(" ,–-—|")
    return t


def is_bullet_or_description(line: str) -> bool:
    """Check if a line represents a bullet point or action sentence instead of a job header."""
    strip_pattern = r"^[ •*\-–—·\u2022\u25cf\u25cb\u25aa\t]+|[ •*\-–—·\u2022\u25cf\u25cb\u25aa\t]+$"
    line_clean = re.sub(strip_pattern, "", line)
    if not line_clean:
        return True
    if line_clean[0] in "•*-–—·\u2022\u25cf\u25cb\u25aa":
        return True
    if ACTION_VERBS.match(line_clean):
        return True
    if SPANISH_TEMPLATE_REGEX.search(line_clean):
        return True
    if re.search(
        r"\b(?:salary:|hours per week:|supervisor:|pay:|hourly rate:)\b", line_clean, re.I
    ):
        return True
    if METRIC_BULLET_REGEX.search(line_clean) and (
        len(line_clean) > 35 or line_clean.endswith(".")
    ):
        return True
    if line_clean.endswith((".", "!", ";")) and len(line_clean) > 30:
        return True
    if line_clean[0].islower() and not line_clean.startswith(("to ", "and ")):
        return True
    return False


def extract_date_range_safely(line: str) -> tuple[str | None, str | None, bool]:
    """Extract job tenure date interval safely, avoiding software version or description dates."""
    if re.search(r"\b(?:server|windows|sql|version|python|stat suite)\s+\d{4}", line, re.I):
        return None, None, False
    m = DATE_RANGE_REGEX.search(line)
    if not m:
        return None, None, False
    start_date = m.group("start").strip()
    end_date = m.group("end").strip()
    is_current = bool(re.search(r"current|present", end_date, re.I))
    return start_date, end_date, is_current


def is_valid_title(title: str | None) -> bool:
    """Validate that candidate string is a plausible job title rather than a sentence or noise."""
    if not title:
        return False
    t = title.strip(" ,–-—|.")
    t_lower = t.lower()
    if t_lower in SECTION_NOISE_TOKENS or len(t) < 3 or len(t) > 60:
        return False
    if t.endswith((".", "!", ";")):
        return False
    if ACTION_VERBS.match(t):
        return False
    if re.search(r"\b(?:salary|hours per week|supervisor)\b", t, re.I):
        return False
    if DATE_RANGE_REGEX.search(t):
        return False
    words = t.split()
    has_marker = any(re.search(r"\b" + m + r"\b", t_lower) for m in COMMON_TITLE_MARKERS)
    all_capitalized = len(words) <= 5 and all(w[0].isupper() for w in words if w and w[0].isalpha())
    return has_marker or all_capitalized


def extract_structured_experiences(experience_text: str) -> list[WorkExperienceEntry]:
    """
    Decompose unstructured work experience text into structured job entries
    (title, company, start, end, bullets).
    """
    if not experience_text or not experience_text.strip():
        return []

    raw_lines = [line.strip() for line in experience_text.split("\n") if line.strip()]
    lines = [clean_header_text(line) for line in raw_lines]
    lines = [line for line in lines if line]

    entries: list[WorkExperienceEntry] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        if is_bullet_or_description(line):
            if entries:
                entries[-1].bullets.append(line)
            i += 1
            continue

        start_date, end_date, is_cur = extract_date_range_safely(line)
        has_title_marker = any(
            re.search(r"\b" + m + r"\b", line.lower()) for m in COMMON_TITLE_MARKERS
        )
        is_short_title = len(line) < 50 and line[0].isupper() and not line.endswith(".")

        if start_date or has_title_marker or is_short_title:
            header_lines = [line]
            curr_title = None
            curr_company = None
            c_start, c_end, c_cur = start_date, end_date, is_cur

            j = i + 1
            while j < min(len(lines), i + 4):
                next_line = lines[j]
                if is_bullet_or_description(next_line):
                    break
                n_start, n_end, n_cur = extract_date_range_safely(next_line)
                if n_start and not c_start:
                    c_start, c_end, c_cur = n_start, n_end, n_cur
                    header_lines.append(next_line)
                    j += 1
                elif not n_start and len(next_line) < 45 and not next_line.endswith("."):
                    header_lines.append(next_line)
                    j += 1
                else:
                    break

            for h in header_lines:
                h_no_date = DATE_RANGE_REGEX.sub("", h)
                h_no_date = clean_header_text(h_no_date)
                if not h_no_date:
                    continue

                delims = [" at ", " @ ", " - ", " – ", " — ", " | ", " , "]
                found = False
                for d in delims:
                    if d in h_no_date:
                        parts = [
                            clean_header_text(p) for p in h_no_date.split(d) if clean_header_text(p)
                        ]
                        if len(parts) >= 2:
                            p1, p2 = parts[0], parts[1]
                            p1_is_title = any(
                                re.search(r"\b" + m + r"\b", p1.lower())
                                for m in COMMON_TITLE_MARKERS
                            )
                            p2_is_title = any(
                                re.search(r"\b" + m + r"\b", p2.lower())
                                for m in COMMON_TITLE_MARKERS
                            )
                            if p1_is_title and not p2_is_title:
                                curr_title = curr_title or p1
                                curr_company = curr_company or p2
                            elif p2_is_title and not p1_is_title:
                                curr_title = curr_title or p2
                                curr_company = curr_company or p1
                            elif curr_title:
                                curr_company = curr_company or p1
                            else:
                                curr_title = p1
                                curr_company = p2

                            found = True
                            break
                if not found:
                    h_is_title = any(
                        re.search(r"\b" + m + r"\b", h_no_date.lower())
                        for m in COMMON_TITLE_MARKERS
                    )
                    if h_is_title and not curr_title:
                        curr_title = h_no_date
                    elif not curr_company:
                        curr_company = h_no_date

            if curr_title:
                curr_title = clean_header_text(curr_title)
            if curr_company:
                curr_company = clean_header_text(curr_company)

            if curr_title and DATE_RANGE_REGEX.search(curr_title):
                curr_title = None

            if not is_valid_title(curr_title):
                first_clean = DATE_RANGE_REGEX.sub("", header_lines[0]).strip(" ,–-—|")
                first_clean = clean_header_text(first_clean)
                if is_valid_title(first_clean):
                    curr_title = first_clean
                else:
                    if entries:
                        entries[-1].bullets.extend(header_lines)
                    i = j
                    continue

            entry = WorkExperienceEntry(
                title=curr_title,
                company=curr_company or "Organization",
                start_date=c_start,
                end_date=c_end,
                is_current=c_cur,
                bullets=[],
                raw_text="\n".join(header_lines),
            )
            entries.append(entry)
            i = j
            continue

        if entries:
            entries[-1].bullets.append(line)
        i += 1

    return entries
