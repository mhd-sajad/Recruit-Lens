"""
Tests for structured output JSON extraction, syntax cleanup, and repair loop.
"""

import pytest
from pydantic import BaseModel

from app.llm.provider import BaseLLMProvider, LLMResponse
from app.llm.repair import clean_json_string, extract_json_from_text, parse_and_repair_json


class SampleOutputModel(BaseModel):
    name: str
    count: int
    items: list[str]


class MockRepairProvider(BaseLLMProvider):
    def __init__(self, repaired_text: str):
        self.repaired_text = repaired_text
        self.repair_calls = 0

    @property
    def provider_name(self) -> str:
        return "mock_repair"

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = True,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> LLMResponse:
        self.repair_calls += 1
        return LLMResponse(content=self.repaired_text, model="mock_repair")


def test_extract_json_from_markdown_blocks() -> None:
    """Verify markdown fences and text commentary are stripped."""
    raw = (
        "Here is the evaluation result in requested JSON:\n"
        "```json\n"
        '{\n  "name": "Cloud Engineer",\n  "count": 3,\n  "items": ["docker", "k8s"]\n}\n'
        "```\n"
        "Hope this helps!"
    )
    extracted = extract_json_from_text(raw)
    assert extracted.startswith("{")
    assert extracted.endswith("}")


def test_clean_json_trailing_commas() -> None:
    """Verify trailing commas before closing braces/brackets are cleaned."""
    bad_syntax = '{"name": "test", "items": ["a", "b",],}'
    cleaned = clean_json_string(bad_syntax)
    assert cleaned == '{"name": "test", "items": ["a", "b"]}'


@pytest.mark.asyncio
async def test_parse_and_repair_json_direct_and_repair() -> None:
    """Verify clean parse works directly, and broken parse invokes repair provider."""
    # 1. Direct clean parse
    valid_text = '{"name": "Candidate A", "count": 5, "items": ["python", "sql"]}'
    res = await parse_and_repair_json(valid_text, SampleOutputModel)
    assert res.name == "Candidate A"
    assert res.count == 5

    # 2. Broken JSON repaired via provider
    broken_text = "Invalid non-json: candidate missing fields"
    repaired_text = '{"name": "Repaired Candidate", "count": 2, "items": ["fastapi"]}'
    repair_provider = MockRepairProvider(repaired_text)

    res_repaired = await parse_and_repair_json(
        broken_text,
        SampleOutputModel,
        provider=repair_provider,
        original_prompt="Evaluate candidate",
    )
    assert res_repaired.name == "Repaired Candidate"
    assert repair_provider.repair_calls == 1
