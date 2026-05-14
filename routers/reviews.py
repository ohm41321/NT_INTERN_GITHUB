from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from database import get_db
from models import User, UserReview, MessageFeedback
from routers.auth import get_current_user
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter()

# Pydantic Models
class ReviewCreate(BaseModel):
    comment: str

class ReviewResponse(BaseModel):
    id: int
    comment: str
    created_at: datetime
    username: str

    class Config:
        orm_mode = True

class ReviewSummaryResponse(BaseModel):
    satisfaction_percentage: int
    total_feedback_count: int
    latest_reviews: List[ReviewResponse]

# Endpoints
@router.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def submit_review(
    review_data: ReviewCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submits a new review. User must be logged in."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You must be logged in to submit a review.")

    new_review = UserReview(
        user_id=user.id,
        comment=review_data.comment
    )
    db.add(new_review)
    await db.commit()
    await db.refresh(new_review, attribute_names=['user']) # Refresh to load the user relationship

    return ReviewResponse(
        id=new_review.id,
        comment=new_review.comment,
        created_at=new_review.created_at,
        username=new_review.user.username
    )

@router.get("/review-summary", response_model=ReviewSummaryResponse)
async def get_review_summary(db: AsyncSession = Depends(get_db)):
    """
    Gets review statistics (from likes/dislikes) and the latest text reviews.
    """
    # --- Get Stats from likes/dislikes ---
    feedback_counts_query = await db.execute(
        select(MessageFeedback.feedback_type, func.count(MessageFeedback.id))
        .group_by(MessageFeedback.feedback_type)
    )
    counts = {ftype: count for ftype, count in feedback_counts_query.all()}
    likes_count = counts.get('like', 0)
    dislikes_count = counts.get('dislike', 0)
    total_feedback = likes_count + dislikes_count
    satisfaction_percentage = round((likes_count / total_feedback) * 100) if total_feedback > 0 else 0

    # --- Get Latest Text Reviews ---
    reviews_result = await db.execute(
        select(UserReview)
        .options(selectinload(UserReview.user))
        .order_by(UserReview.created_at.desc())
        .limit(6) # Fetch 6 reviews for a 2 or 3 column layout
    )
    latest_reviews = reviews_result.scalars().all()
    
    reviews_response = [
        ReviewResponse(
            id=review.id,
            comment=review.comment,
            created_at=review.created_at,
            username=review.user.username
        )
        for review in latest_reviews
    ]

    return ReviewSummaryResponse(
        satisfaction_percentage=satisfaction_percentage,
        total_feedback_count=total_feedback,
        latest_reviews=reviews_response
    )