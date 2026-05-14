from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models import GeneralFeedback, User
from routers.auth import get_current_user_or_none

router = APIRouter()

class FeedbackCreate(BaseModel):
    feedback_type: str
    message: str
    page_url: Optional[str] = None

@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback_data: FeedbackCreate,
    request: Request, # To get user's IP, etc. if needed in future
    user: User = Depends(get_current_user_or_none),
    db: AsyncSession = Depends(get_db)
):
    """Receives feedback from users and stores it in the database."""
    
    user_id = user.id if user else None

    new_feedback = GeneralFeedback(
        user_id=user_id,
        feedback_type=feedback_data.feedback_type,
        message=feedback_data.message,
        page_url=feedback_data.page_url
    )

    db.add(new_feedback)
    await db.commit()

    return {"message": "Feedback received successfully. Thank you!"}
