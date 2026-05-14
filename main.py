# main.py
from sqlalchemy import select
from fastapi import HTTPException, Request, Depends, status
from app_factory import app
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()
import re

from models import User, ChatMessage
from routers.auth import get_current_user, get_current_user_or_none
from database import get_db, async_session
from sqlalchemy.ext.asyncio import AsyncSession
from routers import auth as auth_router
from routers import chat as chat_router
from routers import reviews as reviews_router
from routers import feedback as feedback_router
from routers import admin as admin_router
from routers import tool_chat as tool_chat_router
from routers import health_check as health_check_router

templates = Jinja2Templates(directory="templates")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY"),
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuration --
OPENWEBUI_API_URL = os.getenv("OPENWEBUI_API_URL", "http://localhost:8080/api/chat/completions")
OPENWEBUI_API_KEY = os.getenv("OPENWEBUI_API_KEY")

# --- Helper Functions ---
async def save_message_to_db(session_id: int, sender: str, content: str) -> int:
    async with async_session() as db:
        message = ChatMessage(session_id=session_id, sender=sender, content=content)
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message.id

# --- API Endpoints ---
# Define page routes before mounting static files
@app.get("/")
def read_root(request: Request, user: User = Depends(get_current_user_or_none)):
    return templates.TemplateResponse("main/welcome_main.html", {"request": request, "user": user})

@app.get("/chat")
def read_chat(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("main/index.html", {"request": request, "user": user})

@app.get("/privacy-policy")
def privacy_policy(request: Request):
    return templates.TemplateResponse("main/privacy_policy.html", {"request": request})

@app.get("/terms-of-service")
def terms_of_service(request: Request):
    return templates.TemplateResponse("main/terms_of_service.html", {"request": request})

# --- Include Routers ---
app.include_router(auth_router.router)
app.include_router(chat_router.router, prefix="/chat", tags=["chat"])
app.include_router(reviews_router.router, prefix="/api", tags=["reviews"])
app.include_router(feedback_router.router, prefix="/api", tags=["feedback"])
app.include_router(tool_chat_router.router, prefix="/api", tags=["tool_chat"])
app.include_router(health_check_router.router, prefix="/api", tags=["health"])
app.include_router(admin_router.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8008, reload=True)