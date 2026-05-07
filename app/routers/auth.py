from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from jose import jwt
from datetime import datetime, timedelta
import os, bcrypt
from app.database import supabase

router = APIRouter(prefix="/api/auth", tags=["auth"])

SECRET_KEY = os.getenv("JWT_SECRET", "lovi-secret-change-in-prod")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30

class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

def make_token(user_id: int, email: str) -> str:
    exp = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "email": email, "exp": exp}, SECRET_KEY, ALGORITHM)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode()[:72], hashed.encode())


def send_welcome_email(name: str, email: str):
    html = render_template(template="welcome", subject="Добро пожаловать в «Лови»", name=name, email=email)
    resend.Emails.send({
        "from": "«Лови» <noreply@lovi.today>",
        "to": email,
        "subject": "Добро пожаловать в «Лови»",
        "html": html,
    })


@router.post("/register")
async def register(data: RegisterIn):
    existing = supabase.table("users").select("id").eq("email", data.email).execute()
    if existing.data:
        raise HTTPException(400, "Email уже зарегистрирован")
    res = supabase.table("users").insert({
        "name": data.name,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "created_at": datetime.utcnow().isoformat(),
    }).execute()
    user = res.data[0]
    token = make_token(user["id"], user["email"])
    try:
        send_welcome_email(user["name"], user["email"])
    except Exception as e:
        import logging
        logging.error(f"Welcome email failed: {e}")
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"]}}

@router.post("/login")
async def login(data: LoginIn):
    res = supabase.table("users").select("*").eq("email", data.email).execute()
    if not res.data:
        raise HTTPException(401, "Неверный email или пароль")
    user = res.data[0]
    if not check_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Неверный email или пароль")
    token = make_token(user["id"], user["email"])
    try:
        send_welcome_email(user["name"], user["email"])
    except Exception as e:
        import logging
        logging.error(f"Welcome email failed: {e}")
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"]}}

# ─── My Bookings ───────────────────────────────────────────────────────────────

from fastapi import Header
from jose import JWTError

def get_user_id(authorization: str = Header(...)) -> int:
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError):
        raise HTTPException(401, "Невалидный токен")

@router.get("/my-bookings")
async def my_bookings(authorization: str = Header(...)):
    user_id = get_user_id(authorization)
    res = supabase.table("bookings").select("*").eq("user_id", user_id).order("datetime", desc=True).execute()
    return {"bookings": res.data}

class RatingIn(BaseModel):
    booking_id: int
    rating_place: int
    rating_master: int
    rating_service: int
    review_text: str = ""

@router.post("/rate")
async def rate_booking(data: RatingIn, authorization: str = Header(...)):
    user_id = get_user_id(authorization)
    booking = supabase.table("bookings").select("id,user_id").eq("id", data.booking_id).execute()
    if not booking.data or booking.data[0]["user_id"] != user_id:
        raise HTTPException(403, "Нет доступа")
    supabase.table("bookings").update({
        "rating_place": data.rating_place,
        "rating_master": data.rating_master,
        "rating_service": data.rating_service,
        "review_text": data.review_text,
    }).eq("id", data.booking_id).execute()
    return {"ok": True}

# ─── Password Reset ────────────────────────────────────────────────────────────
import resend, secrets
from app.emails.utils import render_template
from datetime import timezone

resend.api_key = os.getenv("RESEND_API_KEY")
LOVI_BASE_URL = os.getenv("LOVI_BASE_URL", "https://lovi-web.onrender.com")

class ForgotIn(BaseModel):
    email: EmailStr

class ResetIn(BaseModel):
    token: str
    password: str

@router.post("/forgot-password")
async def forgot_password(data: ForgotIn, request: Request):
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    ua = request.headers.get("user-agent", "")
    res = supabase.table("users").select("id,name,email").eq("email", data.email).execute()
    # Всегда возвращаем 200 — не раскрываем существование email
    if not res.data:
        supabase.table("auth_events").insert({
            "event_type": "forgot_password_unknown_email",
            "email": data.email,
            "ip": ip,
            "user_agent": ua,
            "success": False,
            "meta": {"reason": "email not found"}
        }).execute()
        return {"ok": True}
    user = res.data[0]
    token = secrets.token_urlsafe(32)
    expires = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    supabase.table("password_reset_tokens").insert({
        "user_id": user["id"], "token": token, "expires_at": expires
    }).execute()
    supabase.table("auth_events").insert({
        "event_type": "forgot_password_sent",
        "email": data.email,
        "ip": ip,
        "user_agent": ua,
        "success": True,
        "meta": {"user_id": user["id"]}
    }).execute()
    reset_url = f"{LOVI_BASE_URL}/reset-password?token={token}"
    html = render_template(template="forgot_password", subject="Сброс пароля «Лови»", name=user["name"], email=user["email"], reset_url=reset_url)
    resend.Emails.send({
        "from": "«Лови» <noreply@lovi.today>",
        "to": user["email"],
        "subject": "Сброс пароля «Лови»",
        "html": html,
    })
    return {"ok": True}

@router.post("/reset-password")
async def reset_password(data: ResetIn):
    res = supabase.table("password_reset_tokens").select("*").eq("token", data.token).execute()
    if not res.data:
        raise HTTPException(400, "Недействительная ссылка")
    rec = res.data[0]
    if rec["used"]:
        raise HTTPException(400, "Ссылка уже использована")
    expires = datetime.fromisoformat(rec["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(400, "Ссылка истекла")
    hashed = hash_password(data.password)
    supabase.table("users").update({"password_hash": hashed}).eq("id", rec["user_id"]).execute()
    supabase.table("password_reset_tokens").update({"used": True}).eq("token", data.token).execute()
    return {"ok": True}
