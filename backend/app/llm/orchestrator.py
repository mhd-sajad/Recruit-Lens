"""
Agent Orchestrator and Execution State Machine.

Features:
- Formal state machine: PENDING -> EVIDENCE_PACKED -> EXPLAINING -> INTERVIEW_GEN -> EMAIL_GEN -> CRITIQUING -> COMPLETED.
- Resumable and idempotent execution via repository interface.
- Per-candidate failure isolation: a failure on candidate N never terminates the batch.
- Concurrency limiting via asyncio.Semaphore.
- Granular token accounting and latency tracking.
- Decoupled repository interface ready for Batch 4 database integration.
"""

import abc
import asyncio
import time
from collections.abc import Callable, Coroutine
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.llm.agents.emailer import generate_candidate_emails
from app.llm.agents.explainer import generate_candidate_explanation
from app.llm.agents.interviewer import generate_candidate_questions
from app.llm.critique import run_critique_and_refine
from app.llm.provider import BaseLLMProvider, FallbackLLMProvider
from app.llm.schemas import (
    CandidateAgentResult,
    EvidencePacket,
)
from app.llm.templates import (
    generate_deterministic_emails,
    generate_deterministic_explanation,
    generate_deterministic_questions,
)
from app.logging import get_logger

logger = get_logger("llm.orchestrator")


class AgentState(StrEnum):
    """Lifecycle states of the multi-agent generation pipeline."""

    PENDING = "PENDING"
    EVIDENCE_PACKED = "EVIDENCE_PACKED"
    EXPLAINING = "EXPLAINING"
    INTERVIEW_GEN = "INTERVIEW_GEN"
    EMAIL_GEN = "EMAIL_GEN"
    CRITIQUING = "CRITIQUING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentExecutionRecord(BaseModel):
    """Persisted execution audit record for a single candidate."""

    run_id: str
    candidate_id: str
    state: AgentState
    result: CandidateAgentResult | None = None
    error_message: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    latency_ms: float = 0.0
    started_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class AgentExecutionRepository(abc.ABC):
    """Abstract repository decoupling state storage from execution logic."""

    @abc.abstractmethod
    async def save_record(self, record: AgentExecutionRecord) -> None:
        pass

    @abc.abstractmethod
    async def get_record(self, run_id: str, candidate_id: str) -> AgentExecutionRecord | None:
        pass

    @abc.abstractmethod
    async def list_records(self, run_id: str) -> list[AgentExecutionRecord]:
        pass


class InMemoryAgentRepository(AgentExecutionRepository):
    """Thread-safe in-memory execution repository."""

    def __init__(self) -> None:
        self._storage: dict[str, dict[str, AgentExecutionRecord]] = {}
        self._lock = asyncio.Lock()

    async def save_record(self, record: AgentExecutionRecord) -> None:
        async with self._lock:
            record.updated_at = time.time()
            if record.run_id not in self._storage:
                self._storage[record.run_id] = {}
            self._storage[record.run_id][record.candidate_id] = record

    async def get_record(self, run_id: str, candidate_id: str) -> AgentExecutionRecord | None:
        async with self._lock:
            return self._storage.get(run_id, {}).get(candidate_id)

    async def list_records(self, run_id: str) -> list[AgentExecutionRecord]:
        async with self._lock:
            return list(self._storage.get(run_id, {}).values())


ProgressCallback = Callable[[str, str, AgentState, float], Coroutine[Any, Any, None]]


class AgentOrchestrator:
    """Multi-agent pipeline orchestrator managing state transitions and concurrency."""

    def __init__(
        self,
        provider: BaseLLMProvider | None = None,
        repository: AgentExecutionRepository | None = None,
        max_concurrency: int = 4,
    ):
        self.provider = provider or FallbackLLMProvider()
        self.repository = repository or InMemoryAgentRepository()
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def run_candidate(
        self,
        packet: EvidencePacket,
        run_id: str = "default_run",
        progress_callback: ProgressCallback | None = None,
    ) -> CandidateAgentResult:
        """
        Execute full multi-agent generation for a candidate with isolation and state persistence.
        If previously completed, returns cached result (idempotent / resumable).
        """
        async with self.semaphore:
            # 1. Idempotency check
            existing = await self.repository.get_record(run_id, packet.candidate_id)
            if existing and existing.state == AgentState.COMPLETED and existing.result:
                logger.info(f"Resuming candidate {packet.candidate_id} from saved completed state.")
                return existing.result

            record = AgentExecutionRecord(
                run_id=run_id,
                candidate_id=packet.candidate_id,
                state=AgentState.PENDING,
            )
            await self.repository.save_record(record)

            start_time = time.monotonic()
            prompt_toks = 0
            comp_toks = 0
            cached_toks = 0
            is_fallback_used = False

            async def _transition(new_state: AgentState) -> None:
                record.state = new_state
                await self.repository.save_record(record)
                if progress_callback:
                    try:
                        elapsed = (time.monotonic() - start_time) * 1000.0
                        await progress_callback(run_id, packet.candidate_id, new_state, elapsed)
                    except Exception as pe:
                        logger.warning(f"Progress callback error: {pe}")

            try:
                # 2. State: EVIDENCE_PACKED
                await _transition(AgentState.EVIDENCE_PACKED)

                # 3. State: EXPLAINING
                await _transition(AgentState.EXPLAINING)
                explanation, exp_fb, p_t, c_t = await generate_candidate_explanation(
                    packet, self.provider
                )
                prompt_toks += p_t
                comp_toks += c_t
                if exp_fb:
                    is_fallback_used = True

                # 4. State: INTERVIEW_GEN
                await _transition(AgentState.INTERVIEW_GEN)
                questions, q_fb, p_t, c_t = await generate_candidate_questions(
                    packet, self.provider
                )
                prompt_toks += p_t
                comp_toks += c_t
                if q_fb:
                    is_fallback_used = True

                # 5. State: EMAIL_GEN
                await _transition(AgentState.EMAIL_GEN)
                emails, em_fb, p_t, c_t = await generate_candidate_emails(packet, self.provider)
                prompt_toks += p_t
                comp_toks += c_t
                if em_fb:
                    is_fallback_used = True

                # 6. State: CRITIQUING (Self-RAG claim check)
                await _transition(AgentState.CRITIQUING)
                verified_explanation, critique_result = await run_critique_and_refine(
                    explanation=explanation,
                    packet=packet,
                    provider=self.provider,
                    max_rewrites=2,
                )
                if critique_result.is_fallback:
                    is_fallback_used = True

                # 7. State: COMPLETED
                latency_ms = (time.monotonic() - start_time) * 1000.0
                result = CandidateAgentResult(
                    candidate_id=packet.candidate_id,
                    explanation=verified_explanation,
                    interview_questions=questions,
                    emails=emails,
                    critique=critique_result,
                    is_fallback=is_fallback_used,
                    prompt_tokens=prompt_toks,
                    completion_tokens=comp_toks,
                    cached_tokens=cached_toks,
                    latency_ms=latency_ms,
                    injection_detected=packet.injection_detected,
                )

                record.state = AgentState.COMPLETED
                record.result = result
                record.prompt_tokens = prompt_toks
                record.completion_tokens = comp_toks
                record.latency_ms = latency_ms
                await self.repository.save_record(record)
                await _transition(AgentState.COMPLETED)

                return result

            except Exception as e:
                # Per-candidate failure isolation: Fallback to full deterministic template
                logger.error(
                    f"Per-candidate pipeline failure for {packet.candidate_id}: {e}. Falling back to deterministic outputs."
                )
                latency_ms = (time.monotonic() - start_time) * 1000.0

                fallback_explanation = generate_deterministic_explanation(packet)
                fallback_questions = generate_deterministic_questions(packet)
                fallback_emails = generate_deterministic_emails(packet)

                fallback_result = CandidateAgentResult(
                    candidate_id=packet.candidate_id,
                    explanation=fallback_explanation,
                    interview_questions=fallback_questions,
                    emails=fallback_emails,
                    critique=critique_result if "critique_result" in locals() else None,  # type: ignore
                    is_fallback=True,
                    prompt_tokens=prompt_toks,
                    completion_tokens=comp_toks,
                    cached_tokens=0,
                    latency_ms=latency_ms,
                    injection_detected=packet.injection_detected,
                )

                record.state = AgentState.COMPLETED
                record.result = fallback_result
                record.error_message = str(e)
                record.latency_ms = latency_ms
                await self.repository.save_record(record)
                return fallback_result

    async def run_batch(
        self,
        packets: list[EvidencePacket],
        run_id: str = "batch_run",
        progress_callback: ProgressCallback | None = None,
    ) -> list[CandidateAgentResult]:
        """Process batch of candidates concurrently under configured concurrency semaphore."""
        tasks = [
            self.run_candidate(packet, run_id=run_id, progress_callback=progress_callback)
            for packet in packets
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results
