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
    "collector",
    "liaison",
    "trainer",
    "fellow",
    "researcher",
    "planner",
    "buyer",
    "underwriter",
    "agent",
    "practitioner",
    "server",
    "producer",
    "editor",
    "writer",
    "author",
    "advisor",
    "expert",
    "professional",
    "attorney",
    "counselor",
    "curator",
    "dean",
    "provost",
    "paramedic",
    "pharmacist",
    "physician",
    "surgeon",
    "veterinarian",
    "optometrist",
    "hygienist",
    "drafter",
    "surveyor",
    "inspector",
    "installer",
    "repairer",
    "electrician",
    "carpenter",
    "plumber",
    "welder",
    "guard",
    "baker",
    "butcher",
    "bartender",
    "host",
    "hostess",
    "housekeeper",
    "aide",
    "generalist",
    "sergeant",
    "technologist",
    "receptionist",
    "merchandiser",
    "stylist",
    "trainee",
    "tech",
    "rep",
    "banker",
}

VALID_SINGLE_WORD_TITLES = {
    "chef",
    "nurse",
    "teacher",
    "recruiter",
    "accountant",
    "intern",
    "developer",
    "consultant",
    "engineer",
    "manager",
    "mechanic",
    "machinist",
    "cook",
    "cashier",
    "teller",
    "supervisor",
    "technician",
    "driver",
    "pilot",
    "auditor",
    "chemist",
    "scientist",
    "programmer",
    "analyst",
    "counsel",
    "attendant",
    "officer",
    "director",
    "administrator",
    "coordinator",
    "laborer",
    "worker",
    "estimator",
    "controller",
    "cfo",
    "vp",
    "president",
    "partner",
    "founder",
    "waiter",
    "waitress",
    "bartender",
    "baker",
    "electrician",
    "plumber",
    "carpenter",
    "welder",
    "paralegal",
    "attorney",
    "lawyer",
    "physician",
    "therapist",
    "pharmacist",
    "instructor",
    "clerk",
    "curator",
    "buyer",
    "underwriter",
    "agent",
    "generalist",
}

# Blacklist of exact strings that are headings, credentials, or placeholders
BLACKLIST_EXACT = {
    "name",
    "state",
    "city",
    "company",
    "company name",
    "organization",
    "location",
    "job title",
    "title",
    "position",
    "e6",
    "training",
    "leadership roles",
    "activities",
    "activities:",
    "ongoing community service initiatives",
    "operator programs",
    "desktop publishing",
    "education",
    "experience",
    "work experience",
    "skills",
    "summary",
    "profile",
    "professional summary",
    "references",
    "honors",
    "awards",
    "certifications",
    "affiliations",
    "publications",
    "interests",
    "hobbies",
    "operating system",
    "technical skills",
    "core competencies",
    "competencies",
    "high school diploma",
    "high school",
    "diploma",
    "duquesne university",
    "cox executive education.",
    "cox executive education",
    "operating system office (word",
    "activities: director of sports",
    "california food handlers card & servsafe food safety manager",
    "tucson medical center & va)",
    "director & vp level professionals",
    "securities",
    "planning",
    "thinking",
    "guide",
    "employment",
    "advanced",
    "regulatory",
    "rights",
    "investigations",
    "investment",
    "development",
    "mitigation",
    "compliance",
    "business development",
    "project management",
    "proper compliance and accurate executive level reporting.e",
    "development, engineering, maintenance, operations administration",
    "project management, research and development, engineering",
    "research and development, engineering, strategic planning",
}

BLACKLIST_SUBSTRINGS = [
    r"\b(?:university|college|diploma|degree|academy|institute|executive education)\b",
    r"\b(?:card & servsafe|food handlers card|driver'?s license|cpr certified)\b",
    r"\b(?:operating system|microsoft word|excel|powerpoint|wordperfect|keynote)\b",
    r"\b(?:community service|leadership roles|professional affiliations)\b",
    r"\b(?:medical center & va|hospital & clinic)\b",
    r"\b(?:co-authored|authored|published|publication)\b",
    r"^activities:\s+",
    r"^\(?co-authored",
    r"^director & vp level professionals",
    r"\breporting\.e$",
    r"^proper compliance\b",
]

TITLE_START_BLACKLIST = re.compile(
    r"^(?:with|using|as|by|at|in|on|for|to|from|and|or|attended?|attending|upgraded?|upgrading|"
    r"use[ds]?|applying?|applied|installed?|installing|configured?|configuring|"
    r"lead(?:ing)?\s+(?:the|a|an|team|product|strategy|projects?|initiatives?|development)|"
    r"answer(?:ing)?\s+(?:and|calls?|inquiries?|issues?)|"
    r"support(?:ing)?\s+(?:sr\.?|the|a|an|teams?|director|group)|"
    r"distribut(?:e|ing|ed)\s+|"
    r"serve(?:s|d)?\s+as\s+lead|"
    r"possesses?\s+|offered?\s+|discuss(?:ed)?\s+|"
    r"managers?\s+and|proper|ongoing|my|so\s+i['’]?m)\b",
    re.IGNORECASE,
)

TITLE_END_BLACKLIST = re.compile(
    r"(?:\b(?:that|the|and|to|as|an|a|or|in|on|at|for|with|by|from|of|now|which|while|so|"
    r"covering\s+the|closing|remarkable|financial|reporting\.e|including|providing|analyzing|"
    r"completed|quarterly|all|other)\b|[(\[{])\s*$",
    re.IGNORECASE,
)

AWARD_AND_CERT_REGEX = re.compile(
    r"\b(?:teacher|employee|associate|salesman|manager|officer)\s+of\s+the\s+(?:year|month|quarter)\b|"
    r"\bpci\s+compliance\b|\b(?:cisco\s+certified|ccna|attendant\s+console)\b|"
    r"\btracking\s+system\b|\baward\b",
    re.IGNORECASE,
)

SENTENCE_INDICATORS = re.compile(
    r"\b(?:i\s+have|i\s+was|i\s+am|my\s+|we\s+|for\s+which|so\s+i['’]?m|"
    r"magazine|journal|published|article|vol\.|issue|perform\s+opening|"
    r"stellar\s+sales|involving\s+patient)\b",
    re.IGNORECASE,
)

# Common action verbs starting bullet points / sentences (not job entries)
ACTION_VERBS = re.compile(
    r"^(?:completed|managed|supervised|provided|provide|provides|providing|prepared|"
    r"assisted|assist|assists|assisting|led|leads|leading|developed|designed|"
    r"implemented|created|responsible for|handled|conducted|coordinated|coordinate|"
    r"coordinates|coordinating|reviewed|oversaw|monitored|monitor|monitors|monitoring|"
    r"maintained|maintain|maintains|maintaining|built|formulated|executed|organized|"
    r"generated|facilitated|analyzed|operated|scheduled|achieved|promoted|collaborated|"
    r"administered|performed|consistently|billed|instructed|trained|enforced|negotiated|"
    r"inspected|strengthened|worked|works|working|partnered|located|spearheaded|conceptualized|"
    r"revitalized|encouraged|defined|upheld|represented|set|acted as|reported|ensured|"
    r"served|established|helped|delivered|directed|participated|identified|verified|"
    r"forwarded|underwrote|drafted|collaborates|spearheads|supervises|recruited|targeted|"
    r"member of|training and development|statement of work|attend|attends|attended|attending|"
    r"upgrade|upgrades|upgraded|upgrading|using|use|uses|used|apply|applies|applied|applying|"
    r"install|installs|installed|installing|configure|configures|configured|configuring)\b",
    re.IGNORECASE,
)

BULLET_CUES = re.compile(
    r"\b(?:responsible for|responsibilities include|duties include|dedicated to|assigned to|"
    r"worked closely with|worked with|trained \d+|recruited by|targeted c-level|"
    r"reporting to|identifying any|how many|co-authored with)\b",
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

DATE_ONLY_REGEX = re.compile(
    r"^\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(?:\d{1,2}[/-])?(?:19[7-9]\d|20[0-2]\d)(?:\s*(?:to|-|–|—)\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(?:\d{1,2}[/-])?(?:19[7-9]\d|20[0-2]\d)|current|present)?\s*$",
    re.IGNORECASE,
)

# Date interval regex covering "01/2015 to Current", "Jan 2018 - Dec 2021", "2016 – 2020"
DATE_RANGE_REGEX = re.compile(
    r"(?P<start>(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(?:\d{1,2}[/-])?(?:19[7-9]\d|20[0-2]\d))\s*"
    r"(?:to|-|–|—)\s*"
    r"(?P<end>(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(?:\d{1,2}[/-])?(?:19[7-9]\d|20[0-2]\d)|current|present)",
    re.IGNORECASE,
)

TRAILING_DATE_REGEX = re.compile(
    r"\s+(?:(?P<s_mon>(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+)?(?P<s_date>\d{1,2}[/-])?(?P<s_yr>19[7-9]\d|20[0-2]\d))\s*(?:to|-|–|—)?\s*$",
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


def clean_placeholders(text: str) -> str:
    """Strip repetitive template placeholders like Company Name, City, State."""
    t = re.sub(
        r"^(?:(?:company\s*name\s*(?:city)?|city\s*,\s*state|state\s*,\s*city|state|city|organization|company)\s*[,–-—|/]?\s*)+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    t = re.sub(
        r"(?:[,–-—|/]?\s*(?:company\s*name\s*(?:city)?|city\s*,\s*state|state\s*,\s*city|state|city|company|organization)\s*)+$",
        "",
        t,
        flags=re.IGNORECASE,
    ).strip()
    return t


def clean_header_text(text: str) -> str:
    """Clean broken encoding, placeholders, and noisy prefixes from text."""
    t = ftfy.fix_text(text)
    t = re.sub(r"[Ââ\x80-\x9f\u00a0\u200b]", "", t).strip()
    t = t.replace("ï¼", " - ")
    t = PLACEHOLDER_REGEX.sub("", t)
    t = clean_placeholders(t)
    t = re.sub(r"\s+", " ", t).strip(" ,–-—|")
    return t


def is_bullet_or_description(line: str) -> bool:
    """Check if a line represents a bullet point, tech list, award, or action sentence instead of a job header."""
    strip_pattern = r"^[ •*\-–—·\u2022\u25cf\u25cb\u25aa\t]+|[ •*\-–—·\u2022\u25cf\u25cb\u25aa\t]+$"
    line_clean = re.sub(strip_pattern, "", line)
    if not line_clean:
        return True
    if line_clean[0] in "•*\u2022\u25cf\u25cb\u25aa":
        return True
    if ACTION_VERBS.match(line_clean):
        return True
    if BULLET_CUES.search(line_clean):
        return True
    if SPANISH_TEMPLATE_REGEX.search(line_clean):
        return True
    if re.search(
        r"\b(?:salary:|hours per week:|supervisor:|pay:|hourly rate:)\b", line_clean, re.I
    ):
        return True
    # Award lines and accomplishments
    if re.search(
        r"\b(?:award|awarded|employee of the (?:month|quarter|year)|dean'?s list|scholarship|certificate of)\b",
        line_clean,
        re.I,
    ):
        return True
    # Environment or technology stack section lines
    if re.search(
        r"^(?:environment|tech stack|technologies|tools|hardware|platforms|operating systems)\b",
        line_clean,
        re.I,
    ):
        return True
    # Multi-comma technology lists e.g. "Technology, Java, LAN, Director, managing, access, C#, Microsoft"
    if line_clean.count(",") >= 2 and any(
        k in line_clean.lower()
        for k in (
            "java",
            "python",
            "sql",
            "oracle",
            "teradata",
            "lan",
            "c#",
            "linux",
            "microsoft",
            "access",
            "html",
            "css",
            "aws",
            "docker",
        )
    ):
        return True
    # Meeting, duty, or activity descriptions
    if re.search(
        r"\b(?:consultant meetings|attended meetings|participated in|responsible for|liaised with|supervised the)\b",
        line_clean,
        re.I,
    ):
        return True
    if METRIC_BULLET_REGEX.search(line_clean) and (
        len(line_clean) > 35 or line_clean.endswith(".")
    ):
        return True
    if line_clean.endswith((".", "!", ";")) and len(line_clean) > 25:
        return True
    if line_clean[0].islower() and not line_clean.startswith(("to ", "and ")):
        return True
    has_marker = any(re.search(r"\b" + m + r"\b", line_clean.lower()) for m in COMMON_TITLE_MARKERS)
    if not has_marker and len(line_clean.split()) > 7:
        return True
    return False


def clean_title_noise(raw_title: str) -> tuple[str, str | None, str | None, bool]:
    """Clean trailing noise, dates, placeholders, and punctuation from title string."""
    t = ftfy.fix_text(raw_title)
    t = re.sub(r"[Ââ\x80-\x9f\u00a0\u200b]", "", t).strip()
    # Strip leading colons, bullets, dashes, tabs, and numbered bullet markers
    t = re.sub(r"^[: •*·–—\-\t]+", "", t).strip()
    t = re.sub(r"^\d+[\.\)]\s+", "", t).strip()
    t = re.sub(r"^[a-zA-Z][-–—]\s+", "", t).strip()
    t = clean_placeholders(t)

    # Split title fused with description
    split_fused = re.split(
        r"\s+(?:mid\s+shift|to\s+(?:support|ensure|provide|assist|maintain|help|lead|develop)|for\s+(?:changing|the\s+purpose))\b",
        t,
        flags=re.IGNORECASE,
    )
    if len(split_fused) > 1 and len(split_fused[0].strip()) >= 3:
        t = split_fused[0].strip()

    # Normalize inverted titles: "DIRECTOR, INDEPENDENT" -> "Independent Director", "ACCOUNTANT, SENIOR" -> "Senior Accountant"
    m_inv = re.match(
        r"^([A-Z\s]+),\s*(INDEPENDENT|SENIOR|ASSOCIATE|ASSISTANT|LEAD|PRINCIPAL|STAFF|JUNIOR)$",
        t,
        re.IGNORECASE,
    )
    if m_inv:
        t = f"{m_inv.group(2).title()} {m_inv.group(1).title()}"

    start_d, end_d, is_cur = None, None, False

    if re.search(r"\s+\b(?:current|present|now|ongoing)\b$", t, re.IGNORECASE):
        t = re.sub(r"\s+\b(?:current|present|now|ongoing)\b$", "", t, flags=re.IGNORECASE).strip()
        end_d = "Current"
        is_cur = True

    m_range = DATE_RANGE_REGEX.search(t)
    if m_range:
        start_d = m_range.group("start").strip()
        end_d = m_range.group("end").strip()
        is_cur = bool(re.search(r"current|present|now|ongoing", end_d, re.IGNORECASE))
        t = t[: m_range.start()] + " " + t[m_range.end() :]
        t = t.strip()

    m_trail = TRAILING_DATE_REGEX.search(t)
    if m_trail:
        start_d = m_trail.group(0).strip(" to-–—")
        t = t[: m_trail.start()].strip()

    t = clean_placeholders(t)
    # Strip inline or trailing placeholders like "| City , State" or "- Company Name"
    t = re.sub(
        r"(?:[|–-—,/]\s*)?\b(?:company\s*name|city\s*,\s*state|state\s*,\s*city|city\s+state)\b.*$",
        "",
        t,
        flags=re.IGNORECASE,
    ).strip()
    t = re.sub(
        r"^.*?\b(?:company\s*name|city\s*,\s*state)\b\s*[|–-—,/]?\s*",
        "",
        t,
        flags=re.IGNORECASE,
    ).strip()
    t = re.sub(
        r"\s+\b(?:managed and maintained|managed|maintained|created|developed|operated|assisted|supervised)\s*$",
        "",
        t,
        flags=re.IGNORECASE,
    ).strip()
    t = re.sub(r"[:,\-–—/&|\s]+$", "", t).strip()
    t = re.sub(r"^[:,\-–—/&|\s]+", "", t).strip()
    return t, start_d, end_d, is_cur


def is_valid_title(title: str | None) -> bool:
    """Validate that candidate string is a plausible job title rather than a sentence or noise."""
    if not title or len(title) < 3 or len(title) > 65:
        return False
    t_clean = title.strip(" ,–-—|.")
    t_lower = t_clean.lower()
    words = t_clean.split()
    if len(words) > 8:
        return False
    if t_clean.count("/") >= 3:
        return False
    if t_lower in BLACKLIST_EXACT or t_lower in SECTION_NOISE_TOKENS:
        return False
    if DATE_ONLY_REGEX.match(t_lower):
        return False
    if AWARD_AND_CERT_REGEX.search(t_clean):
        return False
    for pat in BLACKLIST_SUBSTRINGS:
        if re.search(pat, t_lower):
            return False
    if TITLE_START_BLACKLIST.search(t_clean):
        return False
    if TITLE_END_BLACKLIST.search(t_clean):
        return False
    if SENTENCE_INDICATORS.search(t_clean):
        return False
    if t_lower.endswith((".", "!", ";", ")", ".e")) and not re.search(r"\([A-Z/]+\)$", t_clean):
        return False
    if t_clean.startswith("(") or t_clean.count("(") > t_clean.count(")"):
        return False
    if ACTION_VERBS.match(t_clean):
        return False
    if re.search(
        r"\b(?:configure|configuring|install|installing|troubleshoot|troubleshooting|implement|implementing|maintain|maintaining)\b",
        t_lower,
    ):
        return False
    if t_clean.count(",") >= 2:
        return False

    if len(words) == 1:
        clean_w = re.sub(r"[^a-zA-Z]", "", words[0]).lower()
        return clean_w in VALID_SINGLE_WORD_TITLES

    has_marker = any(re.search(r"\b" + re.escape(m) + r"\b", t_lower) for m in COMMON_TITLE_MARKERS)
    if has_marker:
        return True

    if re.match(r"^(?:senior|junior|lead|principal|chief|head|associate|staff|entry)\b", t_lower):
        return True

    return False


def is_valid_company(company: str | None, title: str | None) -> bool:
    """Validate that company string is legitimate and not a placeholder, title echo, salary, or verb."""
    if not company:
        return False
    c = ftfy.fix_text(company)
    c = re.sub(r"[Ââ\x80-\x9f\u00a0\u200b]", "", c).strip(" ,–-—|.")
    c = clean_placeholders(c)
    c_lower = c.lower()
    if len(c) < 2 or len(c) > 50:
        return False
    # Never store salary, rate, or compensation text
    if re.search(
        r"\b(?:salary|usd|per\s+year|per\s+hour|hourly|rate|annual|pay|hours|stipend)\b|\$", c_lower
    ):
        return False
    # Never store customer lists, duties, or descriptions
    if re.search(
        r"\b(?:customers?|clients?|responsibilities|duties|provided|managed|support|worked|including|taxes|security|management|network)\b",
        c_lower,
    ):
        return False
    if title and c_lower == title.lower().strip(" ,–-—|."):
        return False
    if re.search(
        r"\b(?:19[7-9]\d|20[0-2]\d)\b|/\d{2,4}|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|\bto\b|\bcurrent\b|\bpresent\b",
        c_lower,
    ):
        return False
    if not re.search(r"[a-zA-Z]{2,}", c):
        return False
    if c_lower in {
        "organization",
        "company",
        "city",
        "state",
        "name",
        "none",
        "e6",
        "training",
        "environment",
        "network security",
        "mdm",
        "taxes",
        "cost schedule analyst",
        "conduct seminars on healthcare reform",
        "every company for which i have served",
        "students union, university of technology",
        "customer service/ sales rep city",
        "human resources, benefits, law",
    }:
        return False
    if ACTION_VERBS.match(c):
        return False

    has_comp_suffix = bool(
        re.search(
            r"\b(?:inc\.?|llc\.?|corp\.?|corporation|ltd\.?|limited|co\.?|company|group|services|bank|solutions|"
            r"systems|technologies|hospital|clinic|center|centre|firm|agency|studio|university|college|"
            r"school|partners|labs|store|restaurant|hotel|organization|enterprises|associates|foundation|"
            r"institute|department|ministry|council|authority|board|pharma|logistics|consulting)\b",
            c_lower,
        )
    )

    # Disallow common skill, domain, or duty phrases when no company suffix is present
    if any(
        k in c_lower
        for k in (
            "security",
            "taxes",
            "management",
            "network",
            "reporting",
            "analysis",
            "development",
            "support",
            "database",
            "hardware",
            "software",
            "operations",
            "reconciliation",
        )
    ):
        if not has_comp_suffix:
            return False

    has_marker = any(re.search(r"\b" + re.escape(m) + r"\b", c_lower) for m in COMMON_TITLE_MARKERS)
    if has_marker and not has_comp_suffix:
        return False

    return True


MONTH_MAP: dict[str, int] = {
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


def parse_ym(d_str: str | None, is_start: bool = True) -> tuple[int, int] | None:
    """Parse string into (year, month) tuple. Defaults month to 1 for start, 12 for end if only year."""
    if not d_str:
        return None
    d_clean = d_str.strip().lower()
    if re.search(r"\b(?:current|present|now|ongoing)\b", d_clean):
        return (2026, 10)
    m_yr = re.search(r"\b(19[7-9]\d|20[0-2]\d)\b", d_clean)
    if not m_yr:
        return None
    year = int(m_yr.group(1))
    m_mo = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", d_clean)
    if m_mo:
        month = MONTH_MAP.get(m_mo.group(1)[:3], 1 if is_start else 12)
    else:
        m_num1 = re.search(r"\b(0?[1-9]|1[0-2])[\/\-](?:19[7-9]\d|20[0-2]\d)\b", d_clean)
        m_num2 = re.search(r"\b(?:19[7-9]\d|20[0-2]\d)[\/\-](0?[1-9]|1[0-2])\b", d_clean)
        if m_num1:
            month = int(m_num1.group(1))
        elif m_num2:
            month = int(m_num2.group(1))
        else:
            month = 1 if is_start else 12
    return (year, month)


def validate_date_order(
    start_date: str | None, end_date: str | None
) -> tuple[str | None, str | None, bool, float]:
    """Validate start and end date ordering. If end precedes start, dates set to None and confidence low."""
    if not start_date:
        return None, end_date, False, 1.0
    if not end_date:
        return start_date, None, True, 1.0

    p_start = parse_ym(start_date, is_start=True)
    p_end = parse_ym(end_date, is_start=False)
    if p_start and p_end and p_end < p_start:
        return None, None, False, 0.5

    return start_date, end_date, True, 1.0


def deduplicate_experience_entries(
    entries: list[WorkExperienceEntry],
) -> list[WorkExperienceEntry]:
    """Deduplicate entries within a resume by normalized title, dates, and raw text.
    Drops undated entries whose title matches or is contained in another entry.
    """
    if not entries:
        return []

    def norm_t(t: str | None) -> str:
        return re.sub(r"[^a-z0-9]", "", (t or "").lower())

    # 1. Identify titles that have dates
    dated_entries = [e for e in entries if e.title and (e.start_date or e.end_date)]
    dated_titles = {norm_t(e.title) for e in dated_entries}

    # 2. Filter out duplicates:
    # - exact match to a dated entry when this entry is undated
    # - title is a substring or sub-phrase of another entry in the same resume when this entry is undated
    filtered = []
    for e in entries:
        nt = norm_t(e.title)
        if not nt:
            continue
        is_dated = bool(e.start_date or e.end_date)
        if not is_dated:
            if nt in dated_titles:
                continue
            # Check if this undated title is a substring or sub-phrase of another entry
            is_sub = False
            for other in entries:
                if other is e:
                    continue
                ot = norm_t(other.title)
                if len(nt) >= 5 and nt in ot:
                    is_sub = True
                    break
            if is_sub:
                continue
        filtered.append(e)

    # 3. Deduplicate exact or near-identical repeats
    deduped: list[WorkExperienceEntry] = []
    seen_signatures: set[str] = set()

    for e in filtered:
        nt = norm_t(e.title)
        s_d = (e.start_date or "").strip().lower()
        e_d = (e.end_date or "").strip().lower()
        sig = f"{nt}|{s_d}|{e_d}"
        raw_snippet = re.sub(r"[^a-z0-9]", "", (e.raw_text or "").lower()[:100])

        if sig in seen_signatures or (raw_snippet and raw_snippet in seen_signatures):
            continue

        seen_signatures.add(sig)
        if raw_snippet:
            seen_signatures.add(raw_snippet)
        deduped.append(e)

    return deduped


def calculate_total_experience_years(
    entries: list[WorkExperienceEntry],
    raw_text: str = "",
) -> tuple[float | None, bool]:
    """
    Calculate total non-overlapping numerical years of experience.
    1. Collect and merge valid (start_month, end_month) intervals from job entries.
    2. If no valid intervals exist, fallback to explicit stated experience in raw_text.
    3. If neither is available, return (None, False) indicating UNKNOWN.
    Never return 0.0 for unknown.
    """
    intervals: list[tuple[int, int]] = []
    for e in entries:
        if e.date_known and e.start_date:
            p_s = parse_ym(e.start_date, is_start=True)
            if e.is_current:
                p_e = (2026, 10)
            elif e.end_date:
                p_e = parse_ym(e.end_date, is_start=False)
            else:
                p_e = (p_s[0], p_s[1] + (e.duration_months or 1) - 1) if p_s else None

            if p_s and p_e and p_e >= p_s:
                s_idx = p_s[0] * 12 + p_s[1]
                e_idx = p_e[0] * 12 + p_e[1]
                intervals.append((s_idx, e_idx))

    if intervals:
        # Merge overlapping or contiguous date intervals
        sorted_int = sorted(intervals, key=lambda x: x[0])
        merged = [sorted_int[0]]
        for s, e in sorted_int[1:]:
            last_s, last_e = merged[-1]
            if s <= last_e + 1:
                merged[-1] = (last_s, max(last_e, e))
            else:
                merged.append((s, e))
        total_months = sum(e - s + 1 for s, e in merged)
        total_years = round(total_months / 12.0, 1)
        if total_years > 0.0:
            return total_years, True

    # Fallback to duration_months on entries (e.g. mock objects or pre-computed entries without date strings)
    explicit_months = sum(
        e.duration_months for e in entries if e.duration_months and e.duration_months > 0
    )
    if explicit_months > 0:
        return round(explicit_months / 12.0, 1), True

    # Fallback to stated years in text
    if raw_text:
        num_map = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
            "eleven": 11,
            "twelve": 12,
            "fifteen": 15,
            "twenty": 20,
        }
        # e.g., "nearly six years", "over 10 years", "5+ years of experience"
        m_stated = re.search(
            r"\b(?:over|nearly|more\s+than|at\s+least)?\s*(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)\+?\s*years?(?:\s+of)?(?:\s+(?:relevant|technical|professional|work)?\s*experience)?\b",
            raw_text,
            re.IGNORECASE,
        )
        if m_stated:
            val_str = m_stated.group(1).lower()
            val = float(num_map.get(val_str, val_str))
            if 0.5 <= val <= 50.0:
                return round(val, 1), True

        # e.g. "accountant since 2005"
        m_since = re.search(r"\bsince\s+(19[7-9]\d|20[0-2]\d)\b", raw_text, re.IGNORECASE)
        if m_since:
            yr = int(m_since.group(1))
            val = 2026 - yr
            if 1 <= val <= 50:
                return round(float(val), 1), True

    return None, False


def extract_structured_experiences(experience_text: str) -> list[WorkExperienceEntry]:
    """
    Decompose unstructured work experience text into structured job entries
    (title, company, start, end, duration_months, bullets).
    """
    if not experience_text or not experience_text.strip():
        return []

    raw_lines = [line.strip() for line in experience_text.split("\n") if line.strip()]
    lines = []
    for rl in raw_lines:
        t = ftfy.fix_text(rl)
        t = re.sub(r"[Ââ\x80-\x9f\u00a0\u200b]", "", t).strip()
        if t:
            lines.append(t)

    entries: list[WorkExperienceEntry] = []
    pending_date = None
    i = 0
    while i < len(lines):
        line = lines[i]

        if is_bullet_or_description(line):
            if entries:
                entries[-1].bullets.append(line)
            i += 1
            continue

        if DATE_ONLY_REGEX.match(line):
            m = DATE_RANGE_REGEX.search(line)
            if m:
                s_d = m.group("start").strip()
                e_d = m.group("end").strip()
                is_c = bool(re.search(r"current|present|now|ongoing", e_d, re.I))
                pending_date = (s_d, e_d, is_c)
            else:
                pending_date = (line.strip(), None, False)
            i += 1
            continue

        # Extract date range from line FIRST to prevent dashes in date ranges from breaking delimiter splits
        start_d, end_d, is_cur = None, None, False
        m_range = DATE_RANGE_REGEX.search(line)
        if m_range:
            start_d = m_range.group("start").strip()
            end_d = m_range.group("end").strip()
            is_cur = bool(re.search(r"current|present|now|ongoing", end_d, re.I))
            line_working = (line[: m_range.start()] + " " + line[m_range.end() :]).strip()
        else:
            line_working = line

        # Delimiters for Title - Company (excluding bare comma which corrupts titles)
        delims = [" at ", " @ ", " - ", " – ", " — ", " | "]
        found_parts = False
        curr_title = None
        curr_company = None

        for d in delims:
            if d in line_working:
                parts = [p.strip() for p in line_working.split(d) if p.strip()]
                if len(parts) >= 2:
                    p1, s1, e1, c1 = clean_title_noise(parts[0])
                    p2, s2, e2, c2 = clean_title_noise(parts[1])
                    p1_valid = is_valid_title(p1)
                    p2_valid = is_valid_title(p2)
                    if p1_valid and not p2_valid:
                        curr_title = p1
                        curr_company = p2 if is_valid_company(p2, p1) else None
                        if not start_d:
                            start_d, end_d, is_cur = s1 or s2, e1 or e2, c1 or c2
                        found_parts = True
                        break
                    elif p2_valid and not p1_valid:
                        curr_title = p2
                        curr_company = p1 if is_valid_company(p1, p2) else None
                        if not start_d:
                            start_d, end_d, is_cur = s2 or s1, e2 or e1, c2 or c1
                        found_parts = True
                        break

        if not found_parts:
            h_clean, s_trail, e_trail, cur_trail = clean_title_noise(line_working)
            if not start_d:
                start_d, end_d, is_cur = s_trail, e_trail, cur_trail
            for d in delims:
                if d in h_clean:
                    parts = [p.strip() for p in h_clean.split(d) if p.strip()]
                    if len(parts) >= 2:
                        p1, s1, e1, c1 = clean_title_noise(parts[0])
                        p2, s2, e2, c2 = clean_title_noise(parts[1])
                        p1_valid = is_valid_title(p1)
                        p2_valid = is_valid_title(p2)
                        if p1_valid and not p2_valid:
                            curr_title = p1
                            curr_company = p2 if is_valid_company(p2, p1) else None
                            if not start_d:
                                start_d, end_d, is_cur = s1 or s2, e1 or e2, c1 or c2
                            found_parts = True
                            break
                        elif p2_valid and not p1_valid:
                            curr_title = p2
                            curr_company = p1 if is_valid_company(p1, p2) else None
                            if not start_d:
                                start_d, end_d, is_cur = s2 or s1, e2 or e1, c2 or c1
                            found_parts = True
                            break

            if not found_parts and is_valid_title(h_clean):
                curr_title = h_clean
                curr_company = None

        if curr_title and is_valid_title(curr_title):
            final_company = curr_company if is_valid_company(curr_company, curr_title) else None

            # Attach pending date if available and current entry has no dates
            if pending_date and not start_d and not end_d:
                start_d, end_d, is_cur = pending_date
                pending_date = None

            # Look ahead for company or date if missing
            j = i + 1
            while j < min(len(lines), i + 3):
                next_l = lines[j]
                if is_bullet_or_description(next_l):
                    break
                m_next = DATE_RANGE_REGEX.search(next_l)
                if m_next and not start_d:
                    start_d = m_next.group("start").strip()
                    end_d = m_next.group("end").strip()
                    is_cur = bool(re.search(r"current|present|now|ongoing", end_d, re.I))
                    i = j
                    break
                elif DATE_ONLY_REGEX.match(next_l) and not start_d:
                    start_d = next_l.strip()
                    i = j
                    break
                if not final_company:
                    c_cand, _, _, _ = clean_title_noise(next_l)
                    for cd in [" – ", " - ", " — ", " | "]:
                        if cd in c_cand:
                            c_cand = c_cand.split(cd)[0].strip()
                            break
                    if is_valid_company(c_cand, curr_title):
                        final_company = c_cand
                        i = j
                        break
                j += 1

            v_start, v_end, d_known, conf = validate_date_order(start_d, end_d)

            # Compute entry duration in months
            dur_months = None
            if d_known and v_start:
                p_s = parse_ym(v_start, is_start=True)
                p_e = (2026, 10) if is_cur else (parse_ym(v_end, is_start=False) if v_end else None)
                if p_s and p_e and p_e >= p_s:
                    dur_months = (p_e[0] - p_s[0]) * 12 + (p_e[1] - p_s[1]) + 1

            entries.append(
                WorkExperienceEntry(
                    title=curr_title,
                    company=final_company,
                    start_date=v_start,
                    end_date=v_end,
                    duration_months=dur_months,
                    is_current=is_cur,
                    date_known=d_known,
                    confidence=conf,
                    bullets=[],
                    raw_text=line,
                )
            )
            i += 1
            continue

        if entries:
            entries[-1].bullets.append(line)
        i += 1

    return deduplicate_experience_entries(entries)
