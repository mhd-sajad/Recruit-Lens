"""Section-aware sliding-window chunker for resumes."""

from app.core.models import ResumeChunk, ResumeParseResult

# Configuration parameters for section chunking
EXPERIENCE_CHUNK_SIZE = 200
EXPERIENCE_OVERLAP = 40

PROJECT_CHUNK_SIZE = 200
PROJECT_OVERLAP = 40

GENERIC_CHUNK_SIZE = 150
GENERIC_OVERLAP = 20


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
    summary_text = sections.get("summary", "").strip()
    if summary_text:
        for text in word_sliding_window(summary_text, GENERIC_CHUNK_SIZE, GENERIC_OVERLAP):
            chunks.append(
                ResumeChunk(
                    chunk_id=f"{resume_id}_{chunk_index:03d}",
                    resume_id=resume_id,
                    section="summary",
                    text=text,
                    metadata={"chunk_index": chunk_index, "word_count": len(text.split())},
                )
            )
            chunk_index += 1

    # 2. Skills Chunk
    skills_text = sections.get("skills", "").strip()
    if not skills_text and parsed_resume.skills:
        skills_text = ", ".join(parsed_resume.skills)

    if skills_text:
        for text in word_sliding_window(skills_text, GENERIC_CHUNK_SIZE, GENERIC_OVERLAP):
            chunks.append(
                ResumeChunk(
                    chunk_id=f"{resume_id}_{chunk_index:03d}",
                    resume_id=resume_id,
                    section="skills",
                    text=text,
                    metadata={"chunk_index": chunk_index, "word_count": len(text.split())},
                )
            )
            chunk_index += 1

    # 3. Education Chunk
    education_text = sections.get("education", "").strip()
    if not education_text and parsed_resume.educations:
        education_text = "\n".join(e.raw_text for e in parsed_resume.educations if e.raw_text)

    if education_text:
        for text in word_sliding_window(education_text, GENERIC_CHUNK_SIZE, GENERIC_OVERLAP):
            chunks.append(
                ResumeChunk(
                    chunk_id=f"{resume_id}_{chunk_index:03d}",
                    resume_id=resume_id,
                    section="education",
                    text=text,
                    metadata={"chunk_index": chunk_index, "word_count": len(text.split())},
                )
            )
            chunk_index += 1

    # 4. Work Experience Chunks
    experience_text = sections.get("experience", "").strip()
    if experience_text:
        for text in word_sliding_window(experience_text, EXPERIENCE_CHUNK_SIZE, EXPERIENCE_OVERLAP):
            chunks.append(
                ResumeChunk(
                    chunk_id=f"{resume_id}_{chunk_index:03d}",
                    resume_id=resume_id,
                    section="experience",
                    text=text,
                    metadata={"chunk_index": chunk_index, "word_count": len(text.split())},
                )
            )
            chunk_index += 1

    # 5. Project Chunks
    project_text = sections.get("projects", "").strip()
    if project_text:
        for text in word_sliding_window(project_text, PROJECT_CHUNK_SIZE, PROJECT_OVERLAP):
            chunks.append(
                ResumeChunk(
                    chunk_id=f"{resume_id}_{chunk_index:03d}",
                    resume_id=resume_id,
                    section="projects",
                    text=text,
                    metadata={"chunk_index": chunk_index, "word_count": len(text.split())},
                )
            )
            chunk_index += 1

    # 6. Additional Sections (certifications, awards, highlights, etc.)
    for sec_name in ["certifications", "highlights", "awards", "additional"]:
        sec_text = sections.get(sec_name, "").strip()
        if sec_text:
            for text in word_sliding_window(sec_text, GENERIC_CHUNK_SIZE, GENERIC_OVERLAP):
                chunks.append(
                    ResumeChunk(
                        chunk_id=f"{resume_id}_{chunk_index:03d}",
                        resume_id=resume_id,
                        section=sec_name,
                        text=text,
                        metadata={"chunk_index": chunk_index, "word_count": len(text.split())},
                    )
                )
                chunk_index += 1

    # Fallback: if no section chunks generated (e.g. unsectioned text),
    # chunk the scoring text
    if not chunks and parsed_resume.scoring_text.strip():
        for text in word_sliding_window(
            parsed_resume.scoring_text, EXPERIENCE_CHUNK_SIZE, EXPERIENCE_OVERLAP
        ):
            chunks.append(
                ResumeChunk(
                    chunk_id=f"{resume_id}_{chunk_index:03d}",
                    resume_id=resume_id,
                    section="general",
                    text=text,
                    metadata={"chunk_index": chunk_index, "word_count": len(text.split())},
                )
            )
            chunk_index += 1

    return chunks
