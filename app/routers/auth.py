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
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Добро пожаловать в «Лови»</title>
  <style>
    * {{ margin:0;padding:0;box-sizing:border-box; }}
    body {{ background:#F1F0EC;font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif; }}
    .wrapper {{ max-width:560px;margin:40px auto;background:#FDFCF9;border-radius:24px;overflow:hidden;box-shadow:0 4px 32px rgba(18,26,18,0.08); }}
    .header {{ background:#121A12;padding:28px 40px; }}
    .body {{ padding:40px; }}
    .greeting {{ font-size:22px;font-weight:700;color:#121A12;margin-bottom:16px;line-height:1.35;font-family:Georgia,serif; }}
    .text {{ font-size:15px;color:#5C5347;line-height:1.75;margin-bottom:20px; }}
    .cta-block {{ background:#121A12;border-radius:16px;padding:28px 32px;margin:32px 0; }}
    .cta-label {{ font-size:10px;color:rgba(255,255,255,0.35);text-transform:uppercase;letter-spacing:0.14em;margin-bottom:10px; }}
    .cta-title {{ font-size:18px;font-weight:700;color:#fff;margin-bottom:6px;font-family:Georgia,serif;line-height:1.3; }}
    .cta-sub {{ font-size:13px;color:rgba(255,255,255,0.45);margin-bottom:24px;line-height:1.6; }}
    .cta-btn {{ display:inline-block;background:#ffffff;color:#121A12;text-decoration:none;padding:13px 26px;border-radius:11px;font-size:14px;font-weight:600; }}
    .principle {{ display:flex;gap:16px;align-items:flex-start;padding:18px 0;border-bottom:1px solid rgba(18,26,18,0.06); }}
    .principle:last-child {{ border-bottom:none;padding-bottom:0; }}
    .principle:first-child {{ padding-top:0;border-top:none; }}
    .icon-box {{ width:36px;height:36px;border-radius:10px;background:#F1F0EC;display:flex;align-items:center;justify-content:center;flex-shrink:0; }}
    .p-title {{ font-size:14px;font-weight:600;color:#121A12;margin-bottom:4px; }}
    .p-text {{ font-size:13px;color:#8F8475;line-height:1.6; }}
    .divider {{ height:1px;background:rgba(18,26,18,0.06);margin:32px 0; }}
    .signature {{ font-size:14px;color:#5C5347;line-height:1.75; }}
    .footer {{ padding:22px 40px;background:#F1F0EC; }}
    .footer-text {{ font-size:11px;color:#A09485;line-height:1.6;text-align:center; }}
    .footer-text a {{ color:#A09485;text-decoration:underline; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <img src="https://lovi.today/logo_w.svg" alt="«Лови»" height="26" style="display:block;">
    </div>
    <div class="body">
      <div class="greeting">{name}, вы в «Лови»</div>
      <p class="text">«Лови» — это платформа, которая показывает реальную стоимость времени в лучших SPA и массажных салонах Москвы. Не скидки ради скидок — а прозрачный доступ к слотам, которые салон иначе потеряет. Вы видите честную цену, таймер и одно действие. Без давления.</p>
      <div class="cta-block">
        <div class="cta-label">Доступно сейчас</div>
        <div class="cta-title">Слоты на сегодня открыты</div>
        <div class="cta-sub">Цена каждого слота — реальная стоимость в салоне как точка отсчёта.<br>Выгода рассчитывается автоматически, исходя из времени до начала.</div>
        <a href="https://lovi.today" class="cta-btn">Смотреть окошки</a>
      </div>
      <div class="principle">
        
        <div><div class="p-title">Прозрачность настоящей ценности</div><div class="p-text">Мы не продаём скидки. Мы показываем реальную цену салона как точку отсчёта — и рассчитываем вашу выгоду без манипуляций. Вы сами принимаете решение.</div></div>
      </div>
      <div class="principle">
        
        <div><div class="p-title">Уважение к времени</div><div class="p-text">Каждый слот — это конкретная минута, которую салон иначе потеряет. Мы не растягиваем выбор: таймер, цена, действие. Ваше время стоит ровно столько, сколько вы решаете потратить.</div></div>
      </div>
      <div class="principle">
        
        <div><div class="p-title">Честная технологичность</div><div class="p-text">Предоплата удерживается платформой до подтверждения визита. Если что-то пошло не так — деньги возвращаются в течение 24 часов. Никаких исключений.</div></div>
      </div>
      <div class="divider"></div>
      <div class="signature">
        <p>Если появятся вопросы — напишите нам: <a href="mailto:support@lovi.today" style="color:#121A12;font-weight:600;">support@lovi.today</a></p>
        <br>
        <p><strong style="color:#121A12;">Команда «Лови»</strong><br>
        <span style="font-size:13px;color:#8F8475;">lovi.today · Москва</span></p>
      </div>
    </div>
    <div class="footer">
      <div class="footer-text">
        Вы получили это письмо, потому что зарегистрировались на <a href="https://lovi.today">lovi.today</a>.<br>
        <a href="https://lovi.today/unsubscribe?email={email}">Отписаться</a>
      </div>
    </div>
  </div>
</body>
</html>"""
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
