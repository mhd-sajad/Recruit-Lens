"""
Repair and retry loop for structured JSON generation with Pydantic schema validation.
"""

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.provider import BaseLLMProvider
from app.logging import get_logger

logger = get_logger("llm.repair")

T = TypeVar("T", bound=BaseModel)


def extract_json_from_text(raw_text: str) -> str:
    """Extract valid JSON string from raw LLM output even if surrounded by markdown or commentary."""
    text = raw_text.strip()

    # 1. Match code blocks ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # 2. Extract from outermost curly braces
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1].strip()

    return text


def clean_json_string(json_str: str) -> str:
    """Fix common minor JSON syntax errors like trailing commas before closing braces."""
    cleaned = re.sub(r",\s*([}\]])", r"\1", json_str)
    return cleaned


async def parse_and_repair_json(
    raw_content: str,
    schema: type[T],
    provider: BaseLLMProvider | None = None,
    system_prompt: str = "",
    original_prompt: str = "",
    max_repair_retries: int = 2,
) -> T:
    """
    Parse text into target Pydantic schema with heuristic cleaning and automated LLM repair.
    """
    json_candidate = extract_json_from_text(raw_content)
    last_error: Exception = ValueError("Unknown parse error")

    # Attempt 1: Direct parse
    try:
        data = json.loads(json_candidate)
        return schema.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        last_error = e
        logger.warning(f"Initial JSON parse failed: {e}. Attempting syntax cleanup.")

    # Attempt 2: Clean trailing commas & common formatting flaws
    try:
        cleaned = clean_json_string(json_candidate)
        data = json.loads(cleaned)
        return schema.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        last_error = e
        logger.warning(f"Cleaned JSON parse failed: {e}. Starting LLM repair loop.")

    # Attempt 3: LLM repair loop (if provider available)
    if provider is not None and max_repair_retries > 0:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        current_bad_content = json_candidate

        for attempt in range(max_repair_retries):
            repair_prompt = (
                f"Your previous response produced invalid JSON or violated schema validation.\n"
                f"Validation Error: {last_error}\n\n"
                f"Target Pydantic Schema:\n{schema_json}\n\n"
                f"Original Task Prompt:\n{original_prompt}\n\n"
                f"Invalid JSON Text:\n{current_bad_content}\n\n"
                f"Please fix the syntax and validation errors. Return ONLY the corrected valid JSON object."
            )

            try:
                resp = await provider.complete(
                    prompt=repair_prompt,
                    system_prompt=system_prompt,
                    json_mode=True,
                    max_tokens=1024,
                    temperature=0.0,
                )
                fixed_candidate = extract_json_from_text(resp.content)
                cleaned_fixed = clean_json_string(fixed_candidate)
                data = json.loads(cleaned_fixed)
                return schema.model_validate(data)
            except Exception as repair_err:
                last_error = repair_err
                logger.warning(f"Repair attempt {attempt + 1} failed: {repair_err}")

    raise ValueError(
        f"Failed to produce valid structured output for {schema.__name__}: {last_error}"
    )
