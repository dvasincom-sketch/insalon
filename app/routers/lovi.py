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
        for svc in featured_services:
            slots_resp = await get_book_times(COMPANY_ID, token, fetch_date, svc["id"])
            for slot in slots_resp.get("data", [])[:2]:
                slot_dt = datetime.fromisoformat(slot["datetime"])
                if slot_dt.timestamp() - now_ts < 3600:
                    continue
                base_price = svc_prices.get(svc["id"], 5000)
                strategy, strategy_type = get_strategy(svc["id"], is_weekend)
                pricing = get_lovi_price(base_price, slot_dt, strategy)
                if pricing:
                    results.append({
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
    salon_id = data.get("salon_id")
    user_info = data.get("user_info", {})

    if not salon_id:
        raise HTTPException(400, "salon_id обязателен")

    supabase.table("salons").upsert({
        "company_id": int(salon_id),
        "user_token": None,
    }, on_conflict="company_id").execute()

    return {"ok": True}
