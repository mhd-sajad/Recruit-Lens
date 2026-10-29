"""
Official Python SDK MCP Server for Recruit Lens.

Provides scoped, secure tools for LLM agent interaction:
- Read-only tools: list_jobs, search_candidates, get_candidate_report
- Action preparation: draft_email
- Protected mutation: make_decision (requires valid, one-time confirmation token from Web UI)
"""

from datetime import UTC, datetime
from typing import Any

from mcp.server.mcpserver import MCPServer
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import (
    AuditLog,
    Evaluation,
    Job,
    McpConfirmationToken,
    Resume,
    User,
)
from app.db.session import AsyncSessionLocal
from app.logging import get_logger

logger = get_logger("mcp.server")

# Instantiate official MCP Server
mcp_server = MCPServer("recruit-lens-mcp")


async def _authenticate_user(api_key: str) -> User | None:
    """Validate scoped API key against active user accounts."""
    if not api_key or len(api_key.strip()) < 16:
        return None
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.api_key == api_key, User.is_active == True)  # noqa: E712
        res = await session.execute(stmt)
        return res.scalars().first()


@mcp_server.tool()
async def list_jobs(api_key: str) -> list[dict[str, Any]]:
    """List all active job requisitions for the authenticated user."""
    user = await _authenticate_user(api_key)
    if not user:
        return [{"error": "Authentication failed. Invalid or expired API key."}]

    async with AsyncSessionLocal() as session:
        stmt = (
            select(Job)
            .options(selectinload(Job.resumes))
            .where(Job.user_id == user.id)
            .order_by(Job.created_at.desc())
        )
        res = await session.execute(stmt)
        jobs = res.scalars().all()

        return [
            {
                "job_id": j.id,
                "title": j.title,
                "department": j.department,
                "status": j.status,
                "candidates_count": len(j.resumes),
                "created_at": j.created_at.isoformat(),
            }
            for j in jobs
        ]


@mcp_server.tool()
async def search_candidates(
    api_key: str, job_id: str, query: str = "", tier: str = ""
) -> list[dict[str, Any]]:
    """Search and filter evaluated candidates for a specific job requisition."""
    user = await _authenticate_user(api_key)
    if not user:
        return [{"error": "Authentication failed. Invalid or expired API key."}]

    async with AsyncSessionLocal() as session:
        stmt = (
            select(Evaluation)
            .options(selectinload(Evaluation.resume))
            .where(Evaluation.user_id == user.id, Evaluation.job_id == job_id)
        )
        if tier:
            stmt = stmt.where(Evaluation.tier == tier)

        res = await session.execute(stmt)
        evaluations = res.scalars().all()

        results: list[dict[str, Any]] = []
        q_lower = query.lower().strip()

        for ev in evaluations:
            raw_text = ev.resume.raw_text.lower() if ev.resume else ""
            if q_lower and q_lower not in raw_text:
                continue

            results.append(
                {
                    "evaluation_id": ev.id,
                    "candidate_id": ev.resume_id,
                    "tier": ev.tier,
                    "stage": ev.stage,
                    "total_score": round(ev.total_score, 2),
                    "confidence": ev.confidence,
                }
            )

        return results


@mcp_server.tool()
async def get_candidate_report(api_key: str, evaluation_id: str) -> dict[str, Any]:
    """Retrieve full evaluation breakdown and grounded explanation for a candidate."""
    user = await _authenticate_user(api_key)
    if not user:
        return {"error": "Authentication failed. Invalid or expired API key."}

    async with AsyncSessionLocal() as session:
        stmt = (
            select(Evaluation)
            .options(selectinload(Evaluation.resume).selectinload(Resume.chunks))
            .where(Evaluation.user_id == user.id, Evaluation.id == evaluation_id)
        )
        res = await session.execute(stmt)
        ev = res.scalars().first()
        if not ev:
            return {"error": f"Evaluation record {evaluation_id} not found."}

        return {
            "evaluation_id": ev.id,
            "candidate_id": ev.resume_id,
            "tier": ev.tier,
            "stage": ev.stage,
            "total_score": round(ev.total_score, 2),
            "confidence": ev.confidence,
            "breakdown": ev.breakdown_json,
            "explanation": ev.explanation_json,
            "evidence_hash": ev.evidence_hash,
            "citations_available": len(ev.resume.chunks) if ev.resume else 0,
        }


@mcp_server.tool()
async def draft_email(
    api_key: str, evaluation_id: str, email_type: str = "interview_invitation"
) -> dict[str, Any]:
    """
    Generate or inspect a grounded email draft for a candidate.
    Does NOT send emails; requires recruiter review and explicit dispatch.
    """
    user = await _authenticate_user(api_key)
    if not user:
        return {"error": "Authentication failed. Invalid or expired API key."}

    async with AsyncSessionLocal() as session:
        stmt = select(Evaluation).where(
            Evaluation.user_id == user.id, Evaluation.id == evaluation_id
        )
        res = await session.execute(stmt)
        ev = res.scalars().first()
        if not ev:
            return {"error": f"Evaluation record {evaluation_id} not found."}

        drafts = ev.email_drafts_json or {}
        draft = drafts.get(email_type) or {
            "subject": f"Regarding your application - {email_type.replace('_', ' ').title()}",
            "body": "Thank you for taking the time to speak with our recruiting team.",
        }

        return {
            "evaluation_id": ev.id,
            "email_type": email_type,
            "subject": draft.get("subject", ""),
            "body": draft.get("body", ""),
            "status": "draft",
            "dispatch_mode": "Human review required before live send",
        }


@mcp_server.tool()
async def make_decision(
    api_key: str, evaluation_id: str, decision: str, confirmation_token: str
) -> dict[str, Any]:
    """
    Apply a stage transition decision (e.g. shortlisted, interview_scheduled, held, rejected, hired).
    CRITICAL: Requires a valid, one-time confirmation token generated from the Web UI.
    """
    user = await _authenticate_user(api_key)
    if not user:
        return {"error": "Authentication failed. Invalid or expired API key."}

    async with AsyncSessionLocal() as session:
        # 1. Verify confirmation token
        token_stmt = select(McpConfirmationToken).where(
            McpConfirmationToken.user_id == user.id,
            McpConfirmationToken.token == confirmation_token,
            McpConfirmationToken.target_id == evaluation_id,
            McpConfirmationToken.decision == decision,
            McpConfirmationToken.is_used == False,  # noqa: E712
        )
        token_res = await session.execute(token_stmt)
        token_record = token_res.scalars().first()

        now = datetime.now(UTC)
        if not token_record:
            return {
                "error": "Decision rejected: Confirmation token is invalid or already consumed. Human confirmation in Web UI is strictly required.",
                "success": False,
            }

        expires = token_record.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)

        if expires < now:
            return {
                "error": "Decision rejected: Confirmation token is expired. Human confirmation in Web UI is strictly required.",
                "success": False,
            }

        # 2. Locate evaluation and update stage
        eval_stmt = select(Evaluation).where(
            Evaluation.user_id == user.id, Evaluation.id == evaluation_id
        )
        eval_res = await session.execute(eval_stmt)
        ev = eval_res.scalars().first()
        if not ev:
            return {"error": f"Evaluation record {evaluation_id} not found.", "success": False}

        prev_stage = ev.stage
        ev.stage = decision

        # 3. Mark token consumed
        token_record.is_used = True

        # 4. Append immutable audit log
        audit = AuditLog(
            user_id=user.id,
            action="mcp_stage_decision",
            target_type="evaluation",
            target_id=ev.id,
            details_json={
                "previous_stage": prev_stage,
                "new_stage": decision,
                "via": "mcp_server",
                "confirmation_token_id": token_record.id,
            },
        )
        session.add(audit)
        await session.commit()

        logger.info(
            "MCP stage transition executed for evaluation %s: %s -> %s (token %s)",
            ev.id,
            prev_stage,
            decision,
            token_record.id,
        )

        return {
            "success": True,
            "evaluation_id": ev.id,
            "previous_stage": prev_stage,
            "new_stage": decision,
            "audit_log_id": audit.id,
            "status": "Stage updated successfully.",
        }
