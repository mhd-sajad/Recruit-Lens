"""Section-aware sliding-window chunker for resumes."""

import re

import ftfy

from app.core.models import ResumeChunk, ResumeParseResult

# Configuration parameters for section chunking
EXPERIENCE_CHUNK_SIZE = 200
EXPERIENCE_OVERLAP = 40

PROJECT_CHUNK_SIZE = 200
PROJECT_OVERLAP = 40

GENERIC_CHUNK_SIZE = 150
GENERIC_OVERLAP = 20


def clean_chunk_text(text: str) -> str:
    """
    Clean raw resume text before windowing:
    - Fix UTF-8 mojibake (Â, â€, etc.) via ftfy and targeted replacements
    - Strip placeholder redactions ('Name City , State', 'Phone', 'Email')
    - Normalize whitespace
    """
    if not text:
        return ""
    # 1. ftfy fix
    t = ftfy.fix_text(text)

    # 2. Known mojibake mappings
    moji_map = {
        "Â\xa0": " ",
        "Â": " ",
        "â€¢": "* ",
        "â—": "* ",
        "â—†": "* ",
        "â€\u009d": '"',
        "â€œ": '"',
        "â€": '"',
        "â€™": "'",
        "â€˜": "'",
        "â€“": "-",
        "â€”": "-",
        "â€\x94": "-",
        "â€\x93": "-",
        "ï¼": ": ",
        "\u200b": "",
        "\xa0": " ",
        "\ufeff": "",
    }
    for k, v in moji_map.items():
        t = t.replace(k, v)

    # Attempt latin1 -> utf8 repair for any remaining sequences like \xe2...
    try:
        if re.search(r"[\xe0-\xef][\x80-\xbf]", t):
            t = t.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
    except Exception:
        pass

    # Clean residual isolated non-ascii control / mojibake artifacts
    t = re.sub(r"Â+", " ", t)
    t = re.sub(r"â\S*", " ", t)
    t = re.sub(r"[\x80-\x9f]", " ", t)
    t = re.sub(r"ï\S*", " ", t)

    # 3. Strip placeholder headers: "Name City , State", "Phone", "Email"
    t = re.sub(r"(?i)\b(?:Company\s+)?Name\s+City\s*,\s*State\b", "", t)
    t = re.sub(r"(?i)\bCity\s*,\s*State(?:\s*,\s*[A-Z]{2}|\s*,\s*India)?\b", "", t)
    t = re.sub(r"(?i)\bPhone\s*:\s*[^\n,;]+", "", t)
    t = re.sub(r"(?i)\bEmail\s*:\s*[^\n,;]+", "", t)
    t = re.sub(r"(?im)^\s*(?:Phone|Email)\s*$", "", t)
    t = re.sub(r"(?i)\b(?:Phone|Email)\s*:\s*", "", t)

    # 4. Normalize spaces
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


def word_sliding_window(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping windows based on whitespace word boundaries."""
    words = text.split()
    if not words:
        return []

    if len(words) <= chunk_size:
        return [" ".join(words)]

    chunks: list[str] = []
    start = 0
    step = max(1, chunk_size - overlap)

    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk_words = words[start:end]
        if chunk_words:
            chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
        start += step

    return chunks


def chunk_resume(parsed_resume: ResumeParseResult) -> list[ResumeChunk]:
    """
    Convert a parsed resume into section-aware retrieval chunks.

    Retains section provenance and metadata for each chunk.
    """
    resume_id = parsed_resume.resume_id
    chunks: list[ResumeChunk] = []
    chunk_index = 1

    sections = parsed_resume.sections

    # 1. Summary Chunk
    summary_text = clean_chunk_text(sections.get("summary", ""))
    if summary_text:
        for text in word_sliding_window(summary_text, GENERIC_CHUNK_SIZE, GENERIC_OVERLAP):
            cleaned_window = clean_chunk_text(text)
            if cleaned_window:
                chunks.append(
                    ResumeChunk(
                        chunk_id=f"{resume_id}_{chunk_index:03d}",
                        resume_id=resume_id,
                        section="summary",
                        text=cleaned_window,
                        metadata={
                            "chunk_index": chunk_index,
                            "word_count": len(cleaned_window.split()),
                        },
                    )
                )
                chunk_index += 1

    # 2. Skills Chunk
    skills_text = sections.get("skills", "").strip()
    if not skills_text and parsed_resume.skills:
        skills_text = ", ".join(parsed_resume.skills)
    skills_text = clean_chunk_text(skills_text)

    if skills_text:
        for text in word_sliding_window(skills_text, GENERIC_CHUNK_SIZE, GENERIC_OVERLAP):
            cleaned_window = clean_chunk_text(text)
            if cleaned_window:
                chunks.append(
                    ResumeChunk(
                        chunk_id=f"{resume_id}_{chunk_index:03d}",
                        resume_id=resume_id,
                        section="skills",
                        text=cleaned_window,
                        metadata={
                            "chunk_index": chunk_index,
                            "word_count": len(cleaned_window.split()),
                        },
                    )
                )
                chunk_index += 1

    # 3. Education Chunk
    education_text = sections.get("education", "").strip()
    if not education_text and parsed_resume.educations:
        education_text = "\n".join(e.raw_text for e in parsed_resume.educations if e.raw_text)
    education_text = clean_chunk_text(education_text)

    if education_text:
        for text in word_sliding_window(education_text, GENERIC_CHUNK_SIZE, GENERIC_OVERLAP):
            cleaned_window = clean_chunk_text(text)
            if cleaned_window:
                chunks.append(
                    ResumeChunk(
                        chunk_id=f"{resume_id}_{chunk_index:03d}",
                        resume_id=resume_id,
                        section="education",
                        text=cleaned_window,
                        metadata={
                            "chunk_index": chunk_index,
                            "word_count": len(cleaned_window.split()),
                        },
                    )
                )
                chunk_index += 1

    # 4. Work Experience Chunks
    experience_text = clean_chunk_text(sections.get("experience", ""))
    if experience_text:
        for text in word_sliding_window(experience_text, EXPERIENCE_CHUNK_SIZE, EXPERIENCE_OVERLAP):
            cleaned_window = clean_chunk_text(text)
            if cleaned_window:
                chunks.append(
                    ResumeChunk(
                        chunk_id=f"{resume_id}_{chunk_index:03d}",
                        resume_id=resume_id,
                        section="experience",
                        text=cleaned_window,
                        metadata={
                            "chunk_index": chunk_index,
                            "word_count": len(cleaned_window.split()),
                        },
                    )
                )
                chunk_index += 1

    # 5. Project Chunks
    project_text = clean_chunk_text(sections.get("projects", ""))
    if project_text:
        for text in word_sliding_window(project_text, PROJECT_CHUNK_SIZE, PROJECT_OVERLAP):
            cleaned_window = clean_chunk_text(text)
            if cleaned_window:
                chunks.append(
                    ResumeChunk(
                        chunk_id=f"{resume_id}_{chunk_index:03d}",
                        resume_id=resume_id,
                        section="projects",
                        text=cleaned_window,
                        metadata={
                            "chunk_index": chunk_index,
                            "word_count": len(cleaned_window.split()),
                        },
                    )
                )
                chunk_index += 1

    # 6. Additional Sections (certifications, awards, highlights, etc.)
    for sec_name in ["certifications", "highlights", "awards", "additional"]:
        sec_text = clean_chunk_text(sections.get(sec_name, ""))
        if sec_text:
            for text in word_sliding_window(sec_text, GENERIC_CHUNK_SIZE, GENERIC_OVERLAP):
                cleaned_window = clean_chunk_text(text)
                if cleaned_window:
                    chunks.append(
                        ResumeChunk(
                            chunk_id=f"{resume_id}_{chunk_index:03d}",
                            resume_id=resume_id,
                            section=sec_name,
                            text=cleaned_window,
                            metadata={
                                "chunk_index": chunk_index,
                                "word_count": len(cleaned_window.split()),
                            },
                        )
                    )
                    chunk_index += 1

    # Fallback: if no section chunks generated (e.g. unsectioned text),
    # chunk the scoring text
    if not chunks and parsed_resume.scoring_text.strip():
        fallback_text = clean_chunk_text(parsed_resume.scoring_text)
        for text in word_sliding_window(fallback_text, EXPERIENCE_CHUNK_SIZE, EXPERIENCE_OVERLAP):
            cleaned_window = clean_chunk_text(text)
            if cleaned_window:
                chunks.append(
                    ResumeChunk(
                        chunk_id=f"{resume_id}_{chunk_index:03d}",
                        resume_id=resume_id,
                        section="general",
                        text=cleaned_window,
                        metadata={
                            "chunk_index": chunk_index,
                            "word_count": len(cleaned_window.split()),
                        },
                    )
                )
                chunk_index += 1

    return chunks
