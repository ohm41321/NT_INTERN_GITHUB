from fastapi import APIRouter, Request, Depends, Form, status, HTTPException, Response, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import User
from auth import hash_password, verify_password
import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
import secrets
from urllib.parse import quote
from google_auth import configure_google_oauth
from line_auth import oauth as line_oauth


oauth = configure_google_oauth()

# Email Configuration
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", 'True').lower() in ('true', '1', 't'),
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", 'False').lower() in ('true', '1', 't'),
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user_or_none(token: str = Cookie(None), db: AsyncSession = Depends(get_db)) -> User | None:
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    user = await db.scalar(select(User).where(User.username == username))
    return user

async def get_current_user(user: User = Depends(get_current_user_or_none)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )
    return user

@router.get("/register")
async def get_register_form(request: Request):
    return templates.TemplateResponse("main/register.html", {"request": request})

@router.post("/register")
async def register_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    # Check if a user with this email already exists
    user = await db.scalar(select(User).where(User.email == email))

    if user:
        # If the user exists and already has a password, it's a conflict.
        if user.hashed_password:
            return templates.TemplateResponse("main/register.html", {
                "request": request,
                "error": "อีเมลนี้ถูกใช้งานในระบบแล้ว กรุณาเข้าสู่ระบบหรือใช้ตัวเลือก \"ลืมรหัสผ่าน\""
            }, status_code=status.HTTP_409_CONFLICT)
        
        # If the user exists from a Google login but has no password, 
        # we can add the password to their account.
        else:
            user.hashed_password = hash_password(password)
            # Optionally, update the username if they provide a new one
            # and it's not taken by another user.
            existing_username = await db.scalar(select(User).where(User.username == username))
            if not existing_username or existing_username.email == email:
                user.username = username
            
            db.add(user)
            await db.commit()
            # Redirect to login so they can try their new credentials
            return RedirectResponse(url="/login?message=Password+set+successfully", status_code=status.HTTP_303_SEE_OTHER)

    # If no user with that email exists, create a new one.
    # First, check if the desired username is already taken.
    existing_username = await db.scalar(select(User).where(User.username == username))
    if existing_username:
        return templates.TemplateResponse("main/register.html", {
            "request": request,
            "error": f'ชื่อผู้ใช้ "{username}" ถูกใช้งานแล้ว กรุณาเลือกชื่ออื่น'
        }, status_code=status.HTTP_409_CONFLICT)

    # Create the new user
    hashed_pwd = hash_password(password)
    new_user = User(username=username, email=email, hashed_password=hashed_pwd)
    db.add(new_user)
    await db.commit()
    
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/login")
async def get_login_form(request: Request):
    return templates.TemplateResponse("main/login.html", {"request": request})

@router.get("/login-success")
def login_success(request: Request):
    return templates.TemplateResponse("main/login-success.html", {"request": request})

@router.post("/login")
async def login_user(request: Request, response: Response, username: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.username == username))
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("main/login.html", {
            "request": request,
            "error": "Incorrect username or password"
        }, status_code=status.HTTP_401_UNAUTHORIZED)

    if user.is_google_2fa_enabled:
        response = RedirectResponse(url="/2fa/verify", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="2fa_user", value=username, httponly=True)
        return response
    else:
        access_token = create_access_token(data={"sub": user.username})
        response = RedirectResponse(url="/login-success", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="token", value=access_token, httponly=True)
        return response

@router.get("/profile")
async def get_profile_page(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("main/profile.html", {"request": request, "user": user})

@router.get("/2fa/setup")
async def get_2fa_setup_page(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    secret = pyotp.random_base32()
    user.google_2fa_secret = secret
    await db.commit()

    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="YourAppName")
    
    img = qrcode.make(otp_uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_code_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return templates.TemplateResponse("main/2fa_setup.html", {"request": request, "qr_code": qr_code_b64, "secret_key": secret, "user": user})

@router.post("/2fa/setup")
async def setup_2fa(request: Request, response: Response, otp: str = Form(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user or not user.google_2fa_secret:
        return templates.TemplateResponse("main/2fa_setup.html", {"request": request, "error": "2FA not set up"}, status_code=400)

    totp = pyotp.TOTP(user.google_2fa_secret)
    if totp.verify(otp):
        user.is_google_2fa_enabled = True
        await db.commit()
        message = quote("2FA has been successfully enabled!")
        return RedirectResponse(url=f"/profile?message={message}&type=success", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return templates.TemplateResponse("main/2fa_setup.html", {"request": request, "error": "Invalid OTP"}, status_code=400)

@router.post("/2fa/disable")
async def disable_2fa(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    user.is_google_2fa_enabled = False
    user.google_2fa_secret = None
    await db.commit()
    message = quote("2FA has been successfully disabled.")
    return RedirectResponse(url=f"/profile?message={message}&type=warning", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/2fa/verify")
async def get_2fa_verify_page(request: Request, username: str = Cookie(None, alias="2fa_user")):
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("main/2fa_verify.html", {"request": request, "username": username})

@router.post("/2fa/verify")
async def verify_2fa(response: Response, request: Request, otp: str = Form(...), username: str = Cookie(None, alias="2fa_user"), db: AsyncSession = Depends(get_db)):
    if not username:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    user = await db.scalar(select(User).where(User.username == username))
    if not user or not user.is_google_2fa_enabled or not user.google_2fa_secret:
        return templates.TemplateResponse("main/2fa_verify.html", {
            "request": request,
            "username": username,
            "error": "2FA is not properly configured for your account."
        })

    totp = pyotp.TOTP(user.google_2fa_secret)
    if totp.verify(otp):
        access_token = create_access_token(data={"sub": user.username})
        response = RedirectResponse(url="/login-success", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="token", value=access_token, httponly=True)
        response.delete_cookie("2fa_user")
        return response
    else:
        return templates.TemplateResponse("main/2fa_verify.html", {
            "request": request,
            "username": username,
            "error": "Invalid OTP. Please try again."
        })

@router.post("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("token")
    return response

@router.get("/forgot-password")
async def forgot_password_form(request: Request):
    return templates.TemplateResponse("main/forgot_password.html", {"request": request})

@router.post("/forgot-password")
async def forgot_password(request: Request, email: str = Form(...), db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == email))
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_password_token = token
        user.reset_password_token_expires = datetime.utcnow() + timedelta(hours=1)
        await db.commit()

        reset_link = request.url_for('reset_password_form', token=token)
        
        message = MessageSchema(
            subject="Password Reset Request",
            recipients=[user.email],
            body=f"Please use the following link to reset your password: {reset_link}",
            subtype=MessageType.html
        )
        
        fm = FastMail(conf)
        await fm.send_message(message)

    return templates.TemplateResponse("main/forgot_password.html", {"request": request, "message": "If an account with that email exists, a password reset link has been sent."})

@router.get("/reset-password/{token}")
async def reset_password_form(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.reset_password_token == token))
    if not user or user.reset_password_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return templates.TemplateResponse("main/reset_password.html", {"request": request, "token": token})

@router.post("/reset-password")
async def reset_password(request: Request, token: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.reset_password_token == token))
    if not user or user.reset_password_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user.hashed_password = hash_password(password)
    user.reset_password_token = None
    user.reset_password_token_expires = None
    await db.commit()
    
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/profile-modal")
async def get_profile_modal(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("main/_profile_modal.html", {"request": request, "user": user})

@router.get("/change-password")
async def change_password_form(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("main/change_password.html", {"request": request})

@router.post("/change-password")
async def change_password(request: Request, current_password: str = Form(...), new_password: str = Form(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    if not user.hashed_password or not verify_password(current_password, user.hashed_password):
        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse(status_code=400, content={"error": "Incorrect current password"})
        return templates.TemplateResponse("main/change_password.html", {"request": request, "error": "Incorrect current password"})

    user.hashed_password = hash_password(new_password)
    db.add(user)
    await db.commit()

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(content={"message": "Password updated successfully"})
    
    message = quote("Password changed successfully!")
    return RedirectResponse(url=f"/profile?message={message}&type=success", status_code=status.HTTP_303_SEE_OTHER)

@router.get('/login/google')
async def login_google(request: Request):
    redirect_uri = str(request.url_for('auth_google'))
    if "ngrok-free.app" in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/auth/google')
async def auth_google(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        # Log the error for debugging
        print(f"Error authorizing access token: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not authorize Google account")

    user_info = token.get('userinfo')
    if not user_info or not user_info.get('email'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not retrieve user info from Google")

    email = user_info.get('email')
    user = await db.scalar(select(User).where(User.email == email))

    if user:
        # User exists. If they don't have a google_id, link it.
        if not user.google_id:
            user.google_id = user_info.get('sub')
            db.add(user)
            await db.commit()
    else:
        # New user, create one with Google info.
        user = User(
            username=user_info.get('name', email), # Use email as fallback for username
            email=email,
            google_id=user_info.get('sub'),
            # Password is not set for Google-based accounts initially
            hashed_password=None 
        )
        db.add(user)
        await db.commit()
        await db.refresh(user) # Refresh to get the new user object with ID

    # Create access token and log the user in
    access_token = create_access_token(data={"sub": user.username})
    
    # Redirect admin users to the admin dashboard
    if user.is_admin:
        response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    else:
        response = RedirectResponse(url="/login-success", status_code=status.HTTP_303_SEE_OTHER)
    
    response.set_cookie(key="token", value=access_token, httponly=True)
    return response

@router.get('/login/line')
async def login_line(request: Request):
    redirect_uri = str(request.url_for('auth_line'))
    if "ngrok-free.app" in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")
    return await line_oauth.line.authorize_redirect(request, redirect_uri)

import httpx

@router.get('/login/line/callback', name='auth_line')
async def auth_line(request: Request, db: AsyncSession = Depends(get_db)):
    code = request.query_params.get('code')
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authorization code not found in callback")

    # Manually exchange the authorization code for an access token
    token_url = 'https://api.line.me/oauth2/v2.1/token'
    redirect_uri = str(request.url_for('auth_line'))
    
    # ngrok can sometimes mess with the scheme, force it to https
    if "ngrok-free.app" in redirect_uri:
        redirect_uri = redirect_uri.replace("http://", "https://")

    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': os.getenv("LINE_CHANNEL_ID"),
        'client_secret': os.getenv("LINE_CHANNEL_SECRET"),
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=payload)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            token_data = response.json()

        # Manually decode the id_token using the 'jose' library
        user_info = jwt.decode(
            token_data['id_token'],
            os.getenv("LINE_CHANNEL_SECRET"),
            algorithms=['HS256'],
            audience=os.getenv("LINE_CHANNEL_ID"),
            issuer='https://access.line.me'
        )

    except httpx.HTTPStatusError as e:
        print(f"Error during token exchange: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not exchange code for token with Line")
    except Exception as e:
        print(f"Error authorizing or decoding token: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not authorize or process Line account token")

    if not user_info or not user_info.get('sub'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not retrieve user info from Line token")

    line_id = user_info.get('sub')
    user = await db.scalar(select(User).where(User.line_id == line_id))

    if not user:
        email = user_info.get('email')
        if email:
            existing_user = await db.scalar(select(User).where(User.email == email))
            if existing_user:
                existing_user.line_id = line_id
                user = existing_user
                db.add(user)
                await db.commit()

    if not user:
        user = User(
            username=user_info.get('name'),
            email=user_info.get('email'),
            line_id=line_id,
            hashed_password=None
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    access_token = create_access_token(data={"sub": user.username})
    
    # Redirect admin users to the admin dashboard
    if user.is_admin:
        response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    else:
        response = RedirectResponse(url="/login-success", status_code=status.HTTP_303_SEE_OTHER)
        
    response.set_cookie(key="token", value=access_token, httponly=True)
    return response
