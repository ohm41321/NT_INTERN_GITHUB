from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Date
from sqlalchemy.orm import joinedload
from collections import Counter
import re
from starlette.testclient import TestClient
from app_factory import app
import time

from database import get_db
from models import User, GeneralFeedback, ChatSession, ChatMessage, MessageFeedback, UserReview
from routers.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

async def get_admin_user(user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user

@router.get("/dashboard", response_class=HTMLResponse)
async def get_admin_dashboard(
    request: Request, 
    admin: User = Depends(get_admin_user), 
    db: AsyncSession = Depends(get_db),
    feedback_page: int = Query(1, ge=1),
    feedback_size: int = Query(5, ge=1, le=20) # Smaller size for dashboard widget
):
    # --- Fetch Feedback with Pagination ---
    total_feedback_result = await db.execute(select(func.count(GeneralFeedback.id)))
    total_feedback = total_feedback_result.scalar_one()
    total_feedback_pages = (total_feedback + feedback_size - 1) // feedback_size

    offset = (feedback_page - 1) * feedback_size
    feedback_result = await db.execute(
        select(GeneralFeedback)
        .options(joinedload(GeneralFeedback.user))
        .order_by(GeneralFeedback.created_at.desc())
        .offset(offset)
        .limit(feedback_size)
    )
    feedback_list = feedback_result.scalars().all()

    # Analyze package popularity with basic sentiment filtering
    package_mappings = {
        "NT Fiber Plus": ["fiber", "ไฟเบอร์", "เน็ตบ้าน", "nt fiber plus"],
        "NT Mesh Gigabit Fiber V.2": ["mesh", "เมช", "กิกะบิต", "gigabit", "nt mesh gigabit fiber"],
        "NT SME Plus Series": ["sme", "ธุรกิจ", "sme plus", "nt sme plus series"],
        "NT SME Plus Fixed IP": ["fixed ip", "ฟิกไอพี", "fix ip", "nt sme plus fixed"],
        "NT Mobile": ["mobile", "มือถือ", "ซิม", "sim", "เน็ตมือถือ", "nt mobile"]
    }
    NEGATIVE_KEYWORDS = {
        'ไม่เอา', 'ไม่ต้องการ', 'ยกเลิก', 'แพง', 'ช้า', 'แย่', 'ปัญหา', 'ห่วย'
    }
    package_counts = {name: 0 for name in package_mappings.keys()}

    user_messages_result = await db.execute(select(ChatMessage.content).where(ChatMessage.sender == 'user'))
    user_messages = [msg[0] for msg in user_messages_result.all()]

    for message in user_messages:
        message_lower = message.lower()
        # Simple check for negative words in the message
        has_negative_sentiment = any(keyword in message_lower for keyword in NEGATIVE_KEYWORDS)

        # If the message has negative sentiment, we can skip counting mentions in it
        if has_negative_sentiment:
            continue

        for name, keywords in package_mappings.items():
            if any(keyword in message_lower for keyword in keywords):
                package_counts[name] += 1

    # Analyze busiest hours
    hourly_messages_result = await db.execute(
        select(func.extract('hour', ChatMessage.timestamp), func.count(ChatMessage.id))
        .group_by(func.extract('hour', ChatMessage.timestamp))
        .order_by(func.extract('hour', ChatMessage.timestamp))
    )
    hourly_counts = {hour: count for hour, count in hourly_messages_result.all()}
    # Fill in missing hours with 0
    for hour in range(24):
        if hour not in hourly_counts:
            hourly_counts[hour] = 0

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, 
        "user": admin, 
        "feedback_list": feedback_list,
        "feedback_page": feedback_page,
        "feedback_size": feedback_size,
        "total_feedback_pages": total_feedback_pages,
        "total_feedback": total_feedback,
        "package_counts": package_counts,
        "hourly_counts": hourly_counts
    })

@router.get("/feedback", response_class=HTMLResponse)
async def get_all_feedback(
    request: Request,
    admin: User = Depends(get_admin_user), 
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    # Get total for pagination
    total_feedback_result = await db.execute(select(func.count(GeneralFeedback.id)))
    total_feedback = total_feedback_result.scalar_one()
    total_pages = (total_feedback + size - 1) // size

    # Get feedback for the current page
    offset = (page - 1) * size
    result = await db.execute(
        select(GeneralFeedback)
        .options(joinedload(GeneralFeedback.user))
        .order_by(GeneralFeedback.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    feedback = result.scalars().all()

    # Assuming you have a template named 'feedback.html' or similar
    # You might need to create or adjust this template to display the feedback and pagination controls
    return templates.TemplateResponse("admin/feedback.html", {
        "request": request,
        "user": admin,
        "feedback_list": feedback,
        "page": page,
        "size": size,
        "total_pages": total_pages,
        "total_feedback": total_feedback
    })

@router.get("/api-status-page", response_class=HTMLResponse)
async def get_api_status_page(request: Request, admin: User = Depends(get_admin_user)):
    return templates.TemplateResponse("admin/api_status.html", {"request": request, "user": admin})

@router.get("/users", response_class=HTMLResponse)
async def get_user_management_page(
    request: Request, 
    admin: User = Depends(get_admin_user), 
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    # Get total number of users for pagination
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar_one()
    total_pages = (total_users + size - 1) // size

    # Get users for the current page
    offset = (page - 1) * size
    users_result = await db.execute(
        select(User).order_by(User.id).offset(offset).limit(size)
    )
    user_list = users_result.scalars().all()

    return templates.TemplateResponse("admin/users.html", {
        "request": request, 
        "user": admin, 
        "user_list": user_list,
        "page": page,
        "size": size,
        "total_pages": total_pages,
        "total_users": total_users
    })

@router.post("/users/{user_id}/make-admin")
async def make_admin(user_id: int, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = True
    await db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)

@router.post("/users/{user_id}/revoke-admin")
async def revoke_admin(user_id: int, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = False
    await db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)

@router.post("/users/{user_id}/delete")
async def delete_user(user_id: int, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)

@router.post("/reviews/{review_id}/delete", status_code=303)
async def delete_review(review_id: int, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    review = await db.get(UserReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    await db.delete(review)
    await db.commit()
    
    return RedirectResponse(url="/admin/review-analysis", status_code=303)

@router.get("/chat-analytics", response_class=HTMLResponse)
async def get_chat_analytics_page(request: Request, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    # Chat sessions per day
    sessions_per_day_result = await db.execute(
        select(func.cast(ChatSession.created_at, Date), func.count(ChatSession.id))
        .group_by(func.cast(ChatSession.created_at, Date))
        .order_by(func.cast(ChatSession.created_at, Date))
    )
    sessions_per_day = sessions_per_day_result.all()

    # Most common questions (with filtering)
    questions_result = await db.execute(select(ChatMessage.content).where(ChatMessage.sender == 'user'))
    all_questions = [q[0] for q in questions_result.all()]

    STOP_WORDS = {
        'สวัสดี', 'ดีครับ', 'ดีค่ะ', 'ครับ', 'ค่ะ', 'ฮัลโหล', 'เทส', 'ทดสอบ',
        'ขอบคุณ', 'ok', 'yes', 'no', 'test', 'hello', 'hi', 'thanks'
    }
    MIN_QUESTION_LENGTH = 15

    filtered_questions = []
    for q in all_questions:
        q_lower = q.lower().strip()
        if len(q_lower) < MIN_QUESTION_LENGTH or q_lower in STOP_WORDS or all(word in STOP_WORDS for word in q_lower.split()):
            continue
        filtered_questions.append(q)

    if filtered_questions:
        question_counts = Counter(filtered_questions)
        most_common_questions = question_counts.most_common(10)
    else:
        most_common_questions = []

    # Feedback summary
    feedback_result = await db.execute(select(MessageFeedback.feedback_type, func.count(MessageFeedback.id)).group_by(MessageFeedback.feedback_type))
    feedback_summary = {ftype: count for ftype, count in feedback_result.all()}

    return templates.TemplateResponse("admin/chat_analytics.html", {
        "request": request,
        "user": admin,
        "sessions_per_day": sessions_per_day,
        "most_common_questions": most_common_questions,
        "feedback_summary": feedback_summary
    })

@router.get("/review-analysis", response_class=HTMLResponse)
async def get_review_analysis_page(
    request: Request, 
    admin: User = Depends(get_admin_user), 
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    # Get total for pagination
    total_reviews_result = await db.execute(select(func.count(UserReview.id)))
    total_reviews = total_reviews_result.scalar_one()
    total_pages = (total_reviews + size - 1) // size

    # Get reviews for the current page
    offset = (page - 1) * size
    reviews_result = await db.execute(
        select(UserReview)
        .options(joinedload(UserReview.user))
        .order_by(UserReview.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    all_reviews = reviews_result.scalars().all()

    return templates.TemplateResponse("admin/review_analysis.html", {
        "request": request,
        "user": admin,
        "reviews": all_reviews,
        "page": page,
        "size": size,
        "total_pages": total_pages,
        "total_reviews": total_reviews
    })

@router.get("/user-analytics", response_class=HTMLResponse)
async def get_user_analytics_page(request: Request, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    # Most active users (by chat sessions)
    most_active_users_result = await db.execute(
        select(User.username, func.count(ChatSession.id).label("session_count"))
        .join(ChatSession, User.id == ChatSession.user_id)
        .group_by(User.username)
        .order_by(func.count(ChatSession.id).desc())
        .limit(10)
    )
    most_active_users = most_active_users_result.all()

    # New users per day
    new_users_per_day_result = await db.execute(
        select(func.cast(User.created_at, Date), func.count(User.id))
        .group_by(func.cast(User.created_at, Date))
        .order_by(func.cast(User.created_at, Date))
    )
    new_users_per_day = new_users_per_day_result.all()

    return templates.TemplateResponse("admin/user_analytics.html", {
        "request": request,
        "user": admin,
        "most_active_users": most_active_users,
        "new_users_per_day": new_users_per_day
    })

from starlette.testclient import TestClient
from app_factory import app
import time


@router.get("/internal-status")
async def check_internal_status(admin: User = Depends(get_admin_user)):
    # This endpoint tests a curated list of key internal GET endpoints.
    client = TestClient(app)
    status_results = []
    endpoints_to_test = ["/", "/docs", "/api/health"] # Stable, public, parameter-less GET endpoints

    for path in endpoints_to_test:
        start_time = time.time()
        try:
            response = client.get(path, allow_redirects=False)
            end_time = time.time()
            status_results.append({
                "path": path,
                "status_code": response.status_code,
                "response_time": round((end_time - start_time) * 1000, 2)
            })
        except Exception as e:
            end_time = time.time()
            status_results.append({
                "path": path,
                "status_code": "Error",
                "error_message": str(e),
                "response_time": round((end_time - start_time) * 1000, 2)
            })
            
    return JSONResponse(content=status_results)
