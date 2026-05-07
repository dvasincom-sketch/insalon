from fastapi import APIRouter, HTTPException
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
from datetime import timezone

resend.api_key = os.getenv("RESEND_API_KEY")
LOVI_BASE_URL = os.getenv("LOVI_BASE_URL", "https://lovi-web.onrender.com")

class ForgotIn(BaseModel):
    email: EmailStr

class ResetIn(BaseModel):
    token: str
    password: str

@router.post("/forgot-password")
async def forgot_password(data: ForgotIn):
    res = supabase.table("users").select("id,name,email").eq("email", data.email).execute()
    # Всегда возвращаем 200 — не раскрываем существование email
    if not res.data:
        return {"ok": True}
    user = res.data[0]
    token = secrets.token_urlsafe(32)
    expires = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    supabase.table("password_reset_tokens").insert({
        "user_id": user["id"], "token": token, "expires_at": expires
    }).execute()
    reset_url = f"{LOVI_BASE_URL}/reset-password?token={token}"
    resend.Emails.send({
        "from": "Lovi <noreply@lovi.today>",
        "to": user["email"],
        "subject": "Сброс пароля Lovi",
        "html": f"""
        <div style="font-family:Inter,sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;background:#FDFCF9;">
          <div style="font-size:22px;font-weight:700;color:#121A12;margin-bottom:8px;font-family:Georgia,serif;">Лови</div>
          <p style="font-size:15px;color:#121A12;margin:24px 0 8px;">Привет, {user['name']}!</p>
          <p style="font-size:14px;color:#8F8475;line-height:1.6;margin:0 0 24px;">Вы запросили сброс пароля. Ссылка действительна 2 часа.</p>
          <a href="{reset_url}" style="display:inline-block;background:#121A12;color:#fff;text-decoration:none;padding:14px 28px;border-radius:12px;font-size:14px;font-weight:600;">Сбросить пароль</a>
          <p style="font-size:12px;color:#8F8475;margin-top:24px;line-height:1.6;">Если вы не запрашивали сброс — просто проигнорируйте это письмо.</p>
        </div>
        """,
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
