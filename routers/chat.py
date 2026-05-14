from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import User, ChatSession, ChatMessage, MessageFeedback
from routers.auth import get_current_user
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from collections import Counter

router = APIRouter()

class ChatSessionCreate(BaseModel):
    title: str = "New Chat"

class ChatSessionRename(BaseModel):
    new_title: str

class ChatSessionUpdateTitle(BaseModel):
    title: str

class ChatMessageCreate(BaseModel):
    session_id: int
    sender: str
    content: str

class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    sender: str
    content: str
    timestamp: datetime
    feedback: Optional[str] = None

    class Config:
        orm_mode = True

class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    messages: List[ChatMessageResponse] = []

    class Config:
        orm_mode = True

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(session_data: ChatSessionCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    base_title = session_data.title
    existing_sessions = await db.execute(
        select(ChatSession.title).where(
            ChatSession.user_id == user.id,
            ChatSession.title.startswith(base_title)
        )
    )
    existing_titles = {t[0] for t in existing_sessions.all()}

    new_title = base_title
    counter = 1
    while new_title in existing_titles:
        new_title = f"{base_title} ({counter})"
        counter += 1
    
    new_session = ChatSession(user_id=user.id, title=new_title)
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    # Manually construct the response to avoid lazy loading issues
    response_session = ChatSessionResponse(
        id=new_session.id,
        user_id=new_session.user_id,
        title=new_session.title,
        created_at=new_session.created_at,
        messages=[]
    )
    return response_session

class ChatSessionInfo(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    messages: List[ChatMessageResponse] = []

    class Config:
        orm_mode = True

@router.get("/sessions", response_model=List[ChatSessionInfo])
async def get_chat_sessions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Gets a list of all chat sessions for the current user, without loading the messages.
    This is used to quickly populate the session list in the UI.
    """
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
    )
    sessions = result.scalars().unique().all()
    
    # Return only session info, not the full message history
    return [ChatSessionInfo.from_orm(s) for s in sessions]

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(session_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    session = await db.scalar(select(ChatSession).options(selectinload(ChatSession.messages)).where(ChatSession.id == session_id, ChatSession.user_id == user.id))
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or not owned by user")
    
    messages = await db.execute(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp))
    messages = messages.scalars().all()

    response_messages = []
    for msg in messages:
        feedback = await db.scalar(select(MessageFeedback).where(MessageFeedback.message_id == msg.id, MessageFeedback.user_id == user.id))
        response_messages.append(
            ChatMessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                sender=msg.sender,
                content=msg.content,
                timestamp=msg.timestamp,
                feedback=feedback.feedback_type if feedback else None
            )
        )
    
    return response_messages

@router.post("/messages", response_model=ChatMessageResponse)
async def create_chat_message(message_data: ChatMessageCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    session = await db.scalar(select(ChatSession).where(ChatSession.id == message_data.session_id, ChatSession.user_id == user.id))
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or not owned by user")
    
    new_message = ChatMessage(session_id=message_data.session_id, sender=message_data.sender, content=message_data.content)
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    return new_message

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(session_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    session = await db.scalar(select(ChatSession).options(selectinload(ChatSession.messages)).where(ChatSession.id == session_id, ChatSession.user_id == user.id))
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or not owned by user")
    
    await db.delete(session)
    await db.commit()
    return

@router.put("/sessions/{session_id}/rename", response_model=ChatSessionResponse)
async def rename_chat_session(session_id: int, rename_data: ChatSessionRename, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    session = await db.scalar(select(ChatSession).options(selectinload(ChatSession.messages)).where(ChatSession.id == session_id, ChatSession.user_id == user.id))
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or not owned by user")
    
    new_title = rename_data.new_title.strip()
    if not new_title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title cannot be empty")

    # Check for duplicate titles and append index if necessary
    existing_sessions = await db.execute(
        select(ChatSession.title)
        .where(ChatSession.user_id == user.id, ChatSession.id != session_id)
    )
    existing_titles = [t[0] for t in existing_sessions.all()]

    final_title = new_title
    counter = 1
    while final_title in existing_titles:
        final_title = f"{new_title} ({counter})"
        counter += 1

    session.title = final_title
    await db.commit()
    await db.refresh(session)
    return session

@router.patch("/sessions/{session_id}/update_title", response_model=ChatSessionResponse)
async def update_chat_session_title(session_id: int, update_data: ChatSessionUpdateTitle, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    session = await db.scalar(select(ChatSession).options(selectinload(ChatSession.messages)).where(ChatSession.id == session_id, ChatSession.user_id == user.id))
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or not owned by user")
    
    # Only update if the current title is the default "New Chat" or similar
    # This prevents overwriting user-defined titles
    if session.title.startswith("New Chat") or session.title.startswith("Chat "):
        new_title = update_data.title.strip()
        if not new_title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title cannot be empty")

        # Check for duplicate titles and append index if necessary
        existing_sessions = await db.execute(
            select(ChatSession.title)
            .where(ChatSession.user_id == user.id, ChatSession.id != session_id)
        )
        existing_titles = [t[0] for t in existing_sessions.all()]

        final_title = new_title
        counter = 1
        while final_title in existing_titles:
            final_title = f"{new_title} ({counter})"
            counter += 1

        session.title = final_title
        await db.commit()
        await db.refresh(session)
    
    return session

class FeedbackCreate(BaseModel):
    message_id: int
    feedback_type: str # 'like' or 'dislike'

@router.post("/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def create_feedback(feedback_data: FeedbackCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    message = await db.scalar(select(ChatMessage).where(ChatMessage.id == feedback_data.message_id))
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    # Ensure the user owns the session this message belongs to
    session = await db.scalar(select(ChatSession).where(ChatSession.id == message.session_id, ChatSession.user_id == user.id))
    if not session:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have permission to give feedback for this message")

    existing_feedback = await db.scalar(select(MessageFeedback).where(MessageFeedback.message_id == feedback_data.message_id, MessageFeedback.user_id == user.id))

    if feedback_data.feedback_type == 'none':
        if existing_feedback:
            await db.delete(existing_feedback)
            await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if existing_feedback:
        # If feedback of the same type is submitted again, do nothing.
        # If feedback_type is different, update it.
        if existing_feedback.feedback_type != feedback_data.feedback_type:
            existing_feedback.feedback_type = feedback_data.feedback_type
            await db.commit()
    else:
        # No existing feedback, create a new one
        feedback = MessageFeedback(message_id=feedback_data.message_id, user_id=user.id, feedback_type=feedback_data.feedback_type)
        db.add(feedback)
        await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/sessions/{session_id}/last_user_message", response_model=Optional[ChatMessageResponse])
async def get_last_user_message(session_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        session = await db.scalar(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id))
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found or not owned by user")

        last_user_message = await db.scalar(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.sender == 'user')
            .order_by(ChatMessage.timestamp.desc())
            .limit(1)
        )
        if last_user_message:
            return ChatMessageResponse(
                id=last_user_message.id,
                session_id=last_user_message.session_id,
                sender=last_user_message.sender,
                content=last_user_message.content,
                timestamp=last_user_message.timestamp,
                feedback=None # ChatMessage object does not have a feedback attribute directly
            )
        return None
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error in get_last_user_message: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error while fetching last user message")

@router.get("/faq", response_model=List[str])
async def get_frequently_asked_questions(db: AsyncSession = Depends(get_db)):
    """
    Analyzes the chat history to find the most frequently asked questions by users,
    with filtering for quality.
    วิเคราะห์ประวัติการแชทเพื่อค้นหาคำถามที่พบบ่อยที่สุดจากผู้ใช้ (ผ่านการกรอง)
    """
    try:
        # Query to get all questions (content) from users
        result = await db.execute(
            select(ChatMessage.content)
            .where(ChatMessage.sender == 'user')
        )
        all_questions = [row[0] for row in result.all()]

        # --- Filtering Logic ---
        STOP_WORDS = {
            'สวัสดี', 'ดีครับ', 'ดีค่ะ', 'ครับ', 'ค่ะ', 'ฮัลโหล', 'เทส', 'ทดสอบ', 
            'ขอบคุณ', 'ok', 'yes', 'no', 'test', 'hello', 'hi', 'thanks'
        }
        MIN_QUESTION_LENGTH = 15  # Minimum number of characters

        filtered_questions = []
        for q in all_questions:
            q_lower = q.lower().strip()
            
            # 1. Skip if question is too short
            if len(q_lower) < MIN_QUESTION_LENGTH:
                continue
            
            # 2. Skip if question is in STOP_WORDS
            if q_lower in STOP_WORDS:
                continue

            # 3. Skip if question consists of only a few stop words (simple check)
            if all(word in STOP_WORDS for word in q_lower.split()):
                continue
            
            filtered_questions.append(q)

        # Use Counter to find the most common questions from the filtered list
        if not filtered_questions:
            return []

        question_counts = Counter(filtered_questions)
        
        # Get the 5 most common questions
        most_common_questions = [question for question, count in question_counts.most_common(5)]
        
        return most_common_questions

    except Exception as e:
        # Log the error for debugging purposes
        print(f"Error fetching FAQ: {e}")
        # Return an empty list or a default set of questions in case of an error
        return []


