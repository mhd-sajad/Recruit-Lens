"""
Copilot API route for on-demand grounded candidate Q&A.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import CopilotQueryRequest, CopilotQueryResponse
from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.llm.copilot import answer_copilot_query
from app.logging import get_logger

router = APIRouter(prefix="/copilot", tags=["copilot"])
logger = get_logger("api.copilot")


@router.post("/query", response_model=CopilotQueryResponse)
async def query_copilot(
    payload: CopilotQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CopilotQueryResponse:
    """
    Execute grounded Q&A over candidate resume evidence.
    Returns citations, critic verification status, and enforces 'not found' safety.
    """
    if not payload.candidate_id and not payload.evaluation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either candidate_id or evaluation_id must be provided.",
        )

    response = await answer_copilot_query(
        query=payload.query,
        evaluation_id=payload.evaluation_id,
        candidate_id=payload.candidate_id,
        user_id=current_user.id,
        db=db,
        blind_mode=payload.blind_mode,
    )
    return response
