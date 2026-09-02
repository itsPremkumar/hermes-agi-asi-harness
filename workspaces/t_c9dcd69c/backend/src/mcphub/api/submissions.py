"""Submissions API router."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from mcphub.db.database import get_db_session
from mcphub.schemas import SubmissionCreate, SubmissionReview, SubmissionResponse
from mcphub.services import servers as svc

router = APIRouter()


async def get_session():
    async for session in get_db_session():
        yield session


@router.get("", response_model=list[SubmissionResponse])
async def list_submissions(
    status_filter: Optional[str] = None,
    limit: int = 50,
    session=Depends(get_session),
):
    submissions = await svc.list_submissions(session, status_filter=status_filter, limit=limit)
    return [SubmissionResponse.model_validate(s) for s in submissions]


@router.post("", response_model=SubmissionResponse, status_code=201)
async def create_submission(data: SubmissionCreate, session=Depends(get_session)):
    sub = await svc.create_submission(session, data)
    return sub


@router.post("/{sub_id}/review", response_model=SubmissionResponse)
async def review_submission(sub_id: str, data: SubmissionReview, session=Depends(get_session)):
    sub = await svc.review_submission(
        session, sub_id, data.status, data.review_notes or "", "admin"
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub
