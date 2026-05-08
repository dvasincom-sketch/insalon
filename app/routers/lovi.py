from fastapi import APIRouter, Query, HTTPException, Body
from app.yclients import get_book_times
from app.database import supabase
from datetime import datetime, timezone, timedelta, date as dt_module

router = APIRouter(prefix="/api/lovi", tags=["lovi"])

COMPANY_ID = 1166484

def get_user_token():
    res = supabase.table("salons").select("user_token").eq("company_id", COMPANY_ID).single().execute()
    return res.data["user_token"]

# ── Стратегии ──────────────────────────────────────────────────────────────

class PremiumDiscountStrategy:
    """Перерождение, Весна 9 трав, парные премиум в выходные"""
    def calculate(self, base_price: float, minutes_to_slot: float) -> float:
        hours = minutes_to_slot / 60
        if hours <= 24:
            return base_price * 0.60
        elif hours <= 48:
            return base_price * 0.65
        elif hours <= 72:
            return base_price * 0.80
        else:
            return base_price * 0.90

class PopularDiscountStrategy:
    """Массаж ШВЗ и спина — только будни"""
    def calculate(self, base_price: float, minutes_to_slot: float) -> float:
        hours = minutes_to_slot / 60
        if hours <= 24:
            return base_price * 0.65
        elif hours <= 48:
            return base_price * 0.80
        else:
            return base_price * 0.90

class StepDiscountStrategy:
    """Все остальные услуги"""
    def calculate(self, base_price: float, minutes_to_slot: float) -> float:
        if minutes_to_slot > 1440:
            return base_price * 0.90
        elif minutes_to_slot > 60:
            return base_price * 0.85
        else:
            return base_price * 0.60

# service_id → стратегия (будни)
PREMIUM_IDS_WEEKDAY  = {24560829, 26949774}
POPULAR_IDS_WEEKDAY  = {19658225, 19658183}

# service_id → стратегия (выходные)
PREMIUM_IDS_WEEKEND  = {28219353, 19556779, 19655561, 19556836}

_premium  = PremiumDiscountStrategy()
_popular  = PopularDiscountStrategy()
_step     = StepDiscountStrategy()

def get_strategy(service_id: int, is_weekend: bool):
    if is_weekend:
        if service_id in PREMIUM_IDS_WEEKEND:
            return _premium, "premium"
        return _step, "step"
    else:
        if service_id in PREMIUM_IDS_WEEKDAY:
            return _premium, "premium"
        if service_id in POPULAR_IDS_WEEKDAY:
            return _popular, "popular"
        return _step, "step"

# ── Pricing ────────────────────────────────────────────────────────────────

def get_lovi_price(base_price: float, slot_datetime: datetime, strategy) -> dict | None:
    now = datetime.now(tz=timezone.utc)
    minutes_to_slot = (slot_datetime.astimezone(timezone.utc) - now).total_seconds() / 60
    if minutes_to_slot < 0:
        return None
    lovi_price = strategy.calculate(base_price, minutes_to_slot)
    lovi_price = max(lovi_price, base_price * 0.35)
    discount_pct = round((1 - lovi_price / base_price) * 100)
    return {
        "base_price": int(base_price),
        "lovi_price": int(lovi_price),
        "discount_pct": discount_pct,
        "minutes_to_slot": int(minutes_to_slot),
    }

# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/slots")
async def get_slots(
    date: str = Query(..., description="YYYY-MM-DD"),
    service_id: int = Query(..., description="ID услуги из YCLIENTS")
):
    token = get_user_token()
    slots_raw = (await get_book_times(COMPANY_ID, token, date, service_id)).get("data", [])
    svc = supabase.table("services").select("price_min").eq("id", service_id).single().execute()
    base_price = svc.data["price_min"] if svc.data else 5000
    is_weekend = datetime.now().weekday() >= 5
    strategy, _ = get_strategy(service_id, is_weekend)

    result = []
    for slot in slots_raw:
        if int(slot["time"].split(":")[1]) not in (0, 30):
            continue
        slot_dt = datetime.fromisoformat(slot["datetime"])
        pricing = get_lovi_price(base_price, slot_dt, strategy)
        if pricing:
            result.append({"time": slot["time"], "datetime": slot["datetime"],
                           "duration_min": slot["seance_length"] // 60, **pricing})
    return {"date": date, "service_id": service_id, "slots": result}


@router.get("/price")
async def get_price(
    base_price: int = Query(...),
    slot_time: str = Query(..., description="ISO: 2026-05-06T18:00:00+03:00")
):
    slot_dt = datetime.fromisoformat(slot_time)
    pricing = get_lovi_price(base_price, slot_dt, _step)
    if not pricing:
        raise HTTPException(status_code=400, detail="Slot is in the past")
    return pricing


@router.get("/featured")
async def get_featured(date: str = Query(None)):
    """Топ слоты дня — с тегами и fallback на завтра"""
    if not date:
        date = dt_module.today().isoformat()

    token = get_user_token()
    is_weekend = datetime.now().weekday() >= 5

    if is_weekend:
        featured_services = [
            {"id": 28219353, "name": "«Весна» для двоих",              "duration": 180, "category": "spa"},
            {"id": 19556779, "name": "«Перерождение» для двоих",       "duration": 150, "category": "spa"},
            {"id": 19655561, "name": "SPA для двоих",                  "duration": 120, "category": "spa"},
            {"id": 19556836, "name": "«Экспресс» для двоих",           "duration": 100, "category": "spa"},
            {"id": 19655588, "name": "SPA для мужчин «Самурай»",       "duration": 90,  "category": "spa"},
            {"id": 19468351, "name": "Расслабляющий массаж головы",    "duration": 45,  "category": "head"},
        ]
    else:
        featured_services = [
            {"id": 24560829, "name": "«Перерождение» (Premium Head SPA)", "duration": 120, "category": "head"},
            {"id": 26949774, "name": "«Весна: 9 трав»",                   "duration": 120, "category": "head"},
            {"id": 24562251, "name": "«Гималайский дзен» (Relax Head SPA)","duration": 90, "category": "head"},
            {"id": 24562305, "name": "«Гималайский экспресс»",            "duration": 60,  "category": "head"},
            {"id": 19655588, "name": "SPA для мужчин «Самурай»",          "duration": 90,  "category": "spa"},
            {"id": 19658183, "name": "Массаж спины",                      "duration": 60,  "category": "back"},
            {"id": 19658189, "name": "Массаж всего тела",                 "duration": 90,  "category": "body"},
            {"id": 19658225, "name": "Массаж шейно-воротниковой зоны",   "duration": 30,  "category": "neck"},
        ]

    svc_res = supabase.table("services").select("id,price_min").in_(
        "id", [s["id"] for s in featured_services]
    ).execute()
    svc_prices = {s["id"]: s["price_min"] for s in svc_res.data}

    async def fetch_slots_for_date(fetch_date: str) -> list:
        results = []
        now_ts = datetime.now(tz=timezone.utc).timestamp()
        async def fetch_one(svc):
            try:
                slots_resp = await get_book_times(COMPANY_ID, token, fetch_date, svc["id"])
            except Exception as e:
                print(f"[FEATURED] timeout for service {svc['id']}: {e}")
                return []
            items = []
            for slot in slots_resp.get("data", [])[:2]:
                slot_dt = datetime.fromisoformat(slot["datetime"])
                if slot_dt.timestamp() - now_ts < 3600:
                    continue
                base_price = svc_prices.get(svc["id"], 5000)
                strategy, strategy_type = get_strategy(svc["id"], is_weekend)
                pricing = get_lovi_price(base_price, slot_dt, strategy)
                if pricing:
                    items.append({
                        "time": slot["time"],
                        "datetime": slot["datetime"],
                        "slot_date": fetch_date,
                        "service_id": svc["id"],
                        "service_name": svc["name"],
                        "category": svc["category"],
                        "duration_min": slot["seance_length"] // 60,
                        "strategy": strategy_type,
                        "tag": None,
                        **pricing,
                    })
            return items

        import asyncio
        all_results = await asyncio.gather(*[fetch_one(svc) for svc in featured_services])
        for items in all_results:
            results.extend(items)
        results.sort(key=lambda x: x["datetime"])
        return results[:8]

    results = await fetch_slots_for_date(date)
    if not any(s["strategy"] == "premium" for s in results):
        for delta in range(1, 8):
            next_date = (dt_module.fromisoformat(date) + timedelta(days=delta)).isoformat()
            extra = await fetch_slots_for_date(next_date)
            premium_extra = [s for s in extra if s["strategy"] == "premium"]
            if premium_extra:
                results = premium_extra + [s for s in results if s["strategy"] != "premium"]
                results = results[:8]
                break
    if len(results) < 3:
        for delta in range(1, 8):
            next_date = (dt_module.fromisoformat(date) + timedelta(days=delta)).isoformat()
            results = await fetch_slots_for_date(next_date)
            if len(results) >= 3:
                break

    # ── Теги ──────────────────────────────────────────────────────────────
    tagged_premium = False
    tagged_popular = False
    for slot in results:
        if not tagged_premium and slot["strategy"] == "premium":
            slot["tag"] = "Лучшее предложение"
            tagged_premium = True
        elif not tagged_popular and slot["strategy"] == "popular":
            slot["tag"] = "Популярное"
            tagged_popular = True

    return {"date": date, "slots": results}


@router.post("/book")
async def lovi_book(data: dict = Body(...)):
    """Бронирование горящего слота через Lovi — обёртка над /api/booking/create"""
    import uuid, os, hmac, hashlib
    from app.yclients import create_client, create_record, find_client_by_phone
    import re, asyncio

    token = get_user_token()
    salon = supabase.table("salons").select("*").eq("company_id", COMPANY_ID).single().execute().data

    # 1. Сохраняем бронирование с lovi_price
    row = {
        "company_id": COMPANY_ID,
        "service_id": data.get("service_id"),
        "service_title": data.get("service_title"),
        "datetime": data.get("datetime"),
        "duration": data.get("duration"),
        "total_price": data.get("lovi_price"),
        "master_id": data.get("staff_id"),
        "master_name": data.get("staff_name"),
        "client_name": data.get("client_name"),
        "client_phone": data.get("client_phone"),
        "client_email": data.get("client_email", ""),
        "user_id": data.get("user_id") or None,
        "status": "pending",
        "source": "lovi",
    }
    # Генерируем непредсказуемый код брони
    _secret = os.getenv("BOOKING_CODE_SECRET", "lovi-secret-2026")
    _raw = hmac.new(_secret.encode(), f"{uuid.uuid4()}".encode(), hashlib.sha256).hexdigest()[:10].upper()
    row["booking_code"] = f"{_raw[:4]}-{_raw[4:8]}"
    booking_result = supabase.table("bookings").insert(row).execute()
    booking_id = booking_result.data[0]["id"]

    # 2. Создаём/находим клиента в YCLIENTS
    yclients_client_id = None
    try:
        existing = await create_client(
            COMPANY_ID, token,
            name=data.get("client_name"),
            phone=data.get("client_phone"),
            email=data.get("client_email", "")
        )
        if existing and existing.get("success"):
            yclients_client_id = existing.get("data", {}).get("id")
        if not yclients_client_id:
            raw_phone = data.get("client_phone", "")
            normalized = "+" + re.sub(r"\D", "", raw_phone)
            if normalized.startswith("+8"):
                normalized = "+7" + normalized[2:]
            found = await find_client_by_phone(COMPANY_ID, token, normalized)
            if found:
                yclients_client_id = found.get("id")
        print(f"[LOVI BOOK] client_id={yclients_client_id}")
    except Exception as e:
        print(f"[LOVI BOOK] Ошибка клиента YCLIENTS: {e}")

    # 3. Создаём запись в YCLIENTS (fire-and-forget)
    staff_id = data.get("staff_id") or data.get("staff", {}).get("id") if isinstance(data.get("staff"), dict) else data.get("staff_id")
    print(f"[LOVI BOOK] staff_id from request: {data.get('staff_id')}, staff: {data.get('staff')}")
    record_data = {
        "staff_id": staff_id,
        "services": [{"id": data.get("service_id")}],
        "client": {"id": yclients_client_id} if yclients_client_id else {
            "name": data.get("client_name"),
            "phone": data.get("client_phone"),
        },
        "datetime": data.get("datetime").replace(" ", "T"),
        "seance_length": data.get("duration"),
        "comment": f"lovi.today | booking_id={booking_id}",
    }
    async def _create_record_bg():
        try:
            print(f"[LOVI BOOK] Отправляем в YCLIENTS: {record_data}")
            result = await create_record(COMPANY_ID, token, record_data)
            print(f"[LOVI BOOK] YCLIENTS ответ: {result}")
            if result.get("success"):
                print(f"[LOVI BOOK] YCLIENTS запись создана booking_id={booking_id}")
            else:
                print(f"[LOVI BOOK] YCLIENTS ОШИБКА booking_id={booking_id}: {result}")
        except Exception as e:
            print(f"[LOVI BOOK] Ошибка записи YCLIENTS: {e}")
    asyncio.create_task(_create_record_bg())

    # 4. Создаём платёж YooKassa
    try:
        from app.routers.payments import get_yookassa
        Payment = get_yookassa()
        lovi_price = data.get("lovi_price", 0)
        base_url = os.getenv("LOVI_BASE_URL", "https://lovi-web.onrender.com")
        payment = Payment.create({
            "amount": {"value": f"{lovi_price}.00", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": f"{base_url}/confirm?booking_id={booking_id}"
            },
            "capture": True,
            "description": f"Lovi #{booking_id} — {data.get('service_title', '')}",
            "metadata": {"booking_id": str(booking_id), "source": "lovi"}
        }, str(uuid.uuid4()))

        supabase.table("bookings").update({
            "payment_id": payment.id,
            "status": "waiting_payment"
        }).eq("id", booking_id).execute()

        return {"booking_id": booking_id, "payment_url": payment.confirmation.confirmation_url}

    except Exception as e:
        print(f"[LOVI BOOK] Ошибка платежа: {e}")
        return {"booking_id": booking_id, "payment_url": None, "error": str(e)}


# ── City Expansion ─────────────────────────────────────────────────────────

@router.post("/city-waitlist")
async def city_waitlist_subscribe(data: dict = Body(...)):
    """Подписка на открытие Lovi в городе (форма «Узнать первым»)"""
    city  = (data.get("city")  or "").strip()
    email = (data.get("email") or "").strip().lower()

    if not city:
        raise HTTPException(status_code=422, detail="city is required")
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="valid email is required")

    try:
        supabase.table("city_waitlist").upsert(
            {"city": city, "email": email, "source": "lovi_hero"},
            on_conflict="city,email",
            ignore_duplicates=True,
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        import resend as _resend
        from app.emails.utils import render_template
        import os
        _resend.api_key = os.getenv("RESEND_API_KEY")
        html = render_template(template="city_waitlist", subject="test", email=email, city=city)
        _resend.Emails.send({
            "from": "«Лови» <noreply@lovi.today>",
            "to": email,
            "subject": f"«Лови» скоро в {city}",
            "html": html,
        })
    except Exception as e:
        import logging
        logging.error(f"city_waitlist email error: {e}")
    return {"ok": True}


@router.post("/city-partner")
async def city_partner_request(data: dict = Body(...)):
    """Заявка владельца салона на подключение к Lovi"""
    city       = (data.get("city")       or "").strip()
    name       = (data.get("name")       or "").strip()
    phone      = (data.get("phone")      or "").strip()
    email      = (data.get("email")      or "").strip() or None
    salon_name = (data.get("salon_name") or "").strip()
    address    = (data.get("address")    or "").strip() or None
    crm        = (data.get("crm")        or "").strip() or None

    if not city:
        raise HTTPException(status_code=422, detail="city is required")
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    if not phone or len(phone.replace("+", "").replace(" ", "")) < 10:
        raise HTTPException(status_code=422, detail="valid phone is required")
    if not salon_name:
        raise HTTPException(status_code=422, detail="salon_name is required")

    try:
        supabase.table("city_partner_requests").insert({
            "city":       city,
            "name":       name,
            "phone":      phone,
            "salon_name": salon_name,
            "address":    address,
            "crm":        crm,
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"ok": True}


@router.post("/connect")
async def lovi_connect(data: dict = Body(...)):
    """Салон подключил приложение Lovi из маркетплейса YCLIENTS"""
    import os
    from jose import jwt as jose_jwt
    from datetime import datetime, timedelta

    salon_id = data.get("salon_id")
    user_info = data.get("user_info", {})

    if not salon_id:
        raise HTTPException(400, "salon_id обязателен")

    existing = supabase.table("salons").select("user_token").eq("company_id", int(salon_id)).execute()
    existing_token = existing.data[0]["user_token"] if existing.data else ""
    res = supabase.table("salons").upsert({
        "company_id": int(salon_id),
        "user_token": existing_token or "",
        "yclients_user_id": str(user_info.get("id", "")),
        "owner_name": user_info.get("name", ""),
        "owner_phone": user_info.get("phone", ""),
        "owner_email": user_info.get("email", ""),
        "salon_name": user_info.get("salon_name", ""),
        "connected_at": datetime.utcnow().isoformat(),
        "is_active": True,
    }, on_conflict="company_id").execute()

    salon = res.data[0]
    secret = os.getenv("JWT_SECRET", "lovi-secret-change-in-prod")
    token = jose_jwt.encode(
        {"sub": str(salon["id"]), "company_id": int(salon_id), "exp": datetime.utcnow() + timedelta(days=365)},
        secret, algorithm="HS256"
    )
    # Welcome письмо с magic link
    try:
        import secrets as _secrets, resend as _resend, os
        from app.emails.utils import render_template
        ml_token = _secrets.token_urlsafe(32)
        ml_expires = (datetime.utcnow() + timedelta(days=7)).isoformat()
        supabase.table("salon_magic_links").insert({
            "company_id": int(salon_id),
            "token": ml_token,
            "expires_at": ml_expires,
        }).execute()
        magic_link = f"https://lovi.today/salon/auth?token={ml_token}"
        _resend.api_key = os.getenv("RESEND_API_KEY")
        owner_email = user_info.get("email", "")
        if owner_email:
            html = render_template(
                template="salon_welcome",
                subject="Добро пожаловать в «Лови»",
                owner_name=user_info.get("name", "Партнёр"),
                salon_name=user_info.get("salon_name", "Ваш салон"),
                email=owner_email,
                magic_link=magic_link,
            )
            _resend.Emails.send({
                "from": "«Лови» <noreply@lovi.today>",
                "to": owner_email,
                "subject": "Добро пожаловать в «Лови»",
                "html": html,
            })
    except Exception as e:
        import logging
        logging.error(f"salon welcome email error: {e}")

    return {"ok": True, "token": token, "salon": salon}


# ── Salon Dashboard ────────────────────────────────────────────────────────────

from fastapi import Header

def get_salon_id(authorization: str = Header(...)) -> int:
    import os
    from jose import jwt as jose_jwt, JWTError
    try:
        token = authorization.replace("Bearer ", "")
        secret = os.getenv("JWT_SECRET", "lovi-secret-change-in-prod")
        payload = jose_jwt.decode(token, secret, algorithms=["HS256"])
        return int(payload["company_id"])
    except (JWTError, KeyError):
        raise HTTPException(401, "Невалидный токен")

@router.get("/salon/me")
async def salon_me(authorization: str = Header(...)):
    company_id = get_salon_id(authorization)
    res = supabase.table("salons").select("*").eq("company_id", company_id).single().execute()
    if not res.data:
        raise HTTPException(404, "Салон не найден")
    salon = res.data

    # Health-check токена YCLIENTS
    token = salon.get("user_token", "")
    if token:
        try:
            import httpx, os
            partner_token = os.getenv("YCLIENTS_PARTNER_TOKEN", "").strip()
            from datetime import date as dt_date
            today = dt_date.today().isoformat()
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"https://api.yclients.com/api/v1/records/{company_id}",
                    params={"start_date": today, "end_date": today, "count": 1},
                    headers={
                        "Authorization": f"Bearer {partner_token}, User {token}",
                        "Accept": "application/vnd.api.v2+json"
                    }
                )
            data = resp.json()
            if resp.status_code == 200 and data.get("success"):
                new_status = "ok"
                status_message = None
            else:
                msg = data.get("meta", {}).get("message", "")
                if "прав" in msg.lower():
                    new_status = "no_access"
                    status_message = msg
                else:
                    new_status = "error"
                    status_message = msg
        except Exception as e:
            new_status = "error"
            status_message = str(e)
        supabase.table("salons").update({
            "token_status": new_status,
            "last_sync_at": datetime.utcnow().isoformat(),
        }).eq("company_id", company_id).execute()
        salon["token_status"] = new_status
        salon["last_sync_at"] = datetime.utcnow().isoformat()
        if status_message:
            salon["token_status_message"] = status_message
    else:
        salon["token_status"] = "no_token"

    return salon


# ── Salon Magic Link ───────────────────────────────────────────────────────────

import secrets, resend as _resend
from app.emails.utils import render_template

@router.post("/salon/magic-link")
async def salon_magic_link(data: dict = Body(...)):
    """Запрос magic link для входа в кабинет салона"""
    email = (data.get("email") or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(422, "Укажите email")

    # Ищем салон по email
    res = supabase.table("salons").select("id,company_id,owner_name,salon_name,owner_email")\
        .eq("owner_email", email).execute()
    # Всегда 200 — не раскрываем существование
    if not res.data:
        return {"ok": True}

    salon = res.data[0]
    token = secrets.token_urlsafe(32)
    expires = (datetime.utcnow() + timedelta(days=7)).isoformat()

    supabase.table("salon_magic_links").insert({
        "company_id": salon["company_id"],
        "token": token,
        "expires_at": expires,
    }).execute()

    magic_link = f"https://lovi.today/salon/auth?token={token}"

    import os
    _resend.api_key = os.getenv("RESEND_API_KEY")
    html = render_template(
        template="salon_welcome",
        subject="Вход в кабинет «Лови»",
        owner_name=salon["owner_name"] or "Партнёр",
        salon_name=salon["salon_name"] or "Ваш салон",
        email=email,
        magic_link=magic_link,
    )
    _resend.Emails.send({
        "from": "«Лови» <noreply@lovi.today>",
        "to": email,
        "subject": "Вход в кабинет партнёра «Лови»",
        "html": html,
    })
    return {"ok": True}


@router.get("/salon/auth")
async def salon_auth_by_token(token: str):
    """Верификация magic link — возвращает JWT салона"""
    from datetime import timezone
    res = supabase.table("salon_magic_links").select("*").eq("token", token).execute()
    if not res.data:
        raise HTTPException(400, "Ссылка недействительна")
    rec = res.data[0]
    if rec["used"]:
        raise HTTPException(400, "Ссылка уже использована")
    expires = datetime.fromisoformat(rec["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(400, "Ссылка истекла")

    # Помечаем использованной
    supabase.table("salon_magic_links").update({"used": True}).eq("token", token).execute()

    # Получаем салон
    salon = supabase.table("salons").select("*")\
        .eq("company_id", rec["company_id"]).single().execute().data

    import os
    from jose import jwt as jose_jwt
    secret = os.getenv("JWT_SECRET", "lovi-secret-change-in-prod")
    jwt_token = jose_jwt.encode(
        {"sub": str(salon["id"]), "company_id": salon["company_id"],
         "exp": datetime.utcnow() + timedelta(days=30)},
        secret, algorithm="HS256"
    )
    return {"ok": True, "token": jwt_token, "salon": salon}


# ── Cancel Booking ─────────────────────────────────────────────────────────────

@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: int, authorization: str = Header(...)):
    """Отмена бронирования клиентом — возврат на баланс Lovi"""
    from jose import jwt as jose_jwt, JWTError
    import os

    # Авторизация клиента
    try:
        token = authorization.replace("Bearer ", "")
        secret = os.getenv("JWT_SECRET", "lovi-secret-change-in-prod")
        payload = jose_jwt.decode(token, secret, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (JWTError, KeyError):
        raise HTTPException(401, "Невалидный токен")

    # Получаем бронь
    res = supabase.table("bookings").select("*").eq("id", booking_id).execute()
    if not res.data:
        raise HTTPException(404, "Бронь не найдена")
    booking = res.data[0]

    # Проверяем владельца
    if booking.get("user_id") != user_id:
        raise HTTPException(403, "Нет доступа")

    # Проверяем статус
    if booking["status"] not in ("confirmed", "waiting_payment", "pending"):
        raise HTTPException(400, f"Нельзя отменить бронь со статусом {booking['status']}")

    # Проверяем время — минимум 2 часа до визита
    from datetime import timezone
    slot_dt = datetime.fromisoformat(booking["datetime"])
    if slot_dt.tzinfo is None:
        slot_dt = slot_dt.replace(tzinfo=timezone.utc)
    hours_before = (slot_dt - datetime.now(tz=timezone.utc)).total_seconds() / 3600
    if hours_before < 2:
        raise HTTPException(400, "Отмена невозможна менее чем за 2 часа до визита")

    # Отменяем запись в YCLIENTS если есть record_id
    yclients_cancelled = False
    if booking.get("yclients_record_id") and booking.get("yclients_record_hash"):
        try:
            import httpx
            partner_token = os.getenv("YCLIENTS_PARTNER_TOKEN", "").strip()
            salon = supabase.table("salons").select("user_token")\
                .eq("company_id", booking["company_id"]).single().execute().data
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.delete(
                    f"https://api.yclients.com/api/v1/record/{booking['company_id']}/{booking['yclients_record_id']}",
                    params={"record_hash": booking["yclients_record_hash"]},
                    headers={
                        "Authorization": f"Bearer {partner_token}, User {salon['user_token']}",
                        "Accept": "application/vnd.api.v2+json"
                    }
                )
            yclients_cancelled = resp.status_code == 200
            print(f"[CANCEL] YCLIENTS: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"[CANCEL] YCLIENTS error: {e}")

    # Обновляем статус брони
    supabase.table("bookings").update({
        "status": "cancelled_by_client"
    }).eq("id", booking_id).execute()

    # Возврат на баланс Lovi
    refund_amount = booking.get("total_price", 0)
    supabase.table("balance_transactions").insert({
        "user_id": user_id,
        "booking_id": booking_id,
        "amount": refund_amount * 100,
        "type": "refund",
    }).execute()
    # Обновляем баланс пользователя
    user_res = supabase.table("users").select("lovi_balance").eq("id", user_id).single().execute()
    current_balance = user_res.data.get("lovi_balance", 0) or 0
    supabase.table("users").update({
        "lovi_balance": current_balance + refund_amount
    }).eq("id", user_id).execute()

    # Email клиенту
    try:
        import resend as _resend
        from app.emails.utils import render_template
        _resend.api_key = os.getenv("RESEND_API_KEY")
        if booking.get("client_email"):
            html = render_template(
                template="booking_cancelled",
                subject="Бронирование отменено",
                email=booking["client_email"],
                client_name=booking.get("client_name", ""),
                service_title=booking.get("service_title", ""),
                datetime=str(booking.get("datetime", "")),
            )
            _resend.Emails.send({
                "from": "«Лови» <noreply@lovi.today>",
                "to": booking["client_email"],
                "subject": "Бронирование отменено — средства возвращены на баланс",
                "html": html,
            })
    except Exception as e:
        import logging
        logging.error(f"cancel email error: {e}")

    return {
        "ok": True,
        "refunded": refund_amount,
        "new_balance": current_balance + refund_amount,
        "yclients_cancelled": yclients_cancelled,
    }
