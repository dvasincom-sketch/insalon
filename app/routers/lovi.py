from fastapi import APIRouter, Query, HTTPException, Body, Header
from app.yclients import get_book_times
from app.database import supabase
from datetime import datetime, timezone, timedelta, date as dt_module

router = APIRouter(prefix="/api/lovi", tags=["lovi"])

COMPANY_ID = 1166484

def get_user_token():
    res = supabase.table("salons").select("user_token").eq("company_id", COMPANY_ID).single().execute()
    return res.data["user_token"]


# ── Стратегии ──────────────────────────────────────────────────────────────

STRATEGY_DEFAULTS = {
    "premium": dict(threshold_far=48, threshold_near=24, coeff_far=0.65, coeff_near=0.60, coeff_hot=0.60),
    "popular": dict(threshold_far=48, threshold_near=24, coeff_far=0.90, coeff_near=0.80, coeff_hot=0.65),
    "step":    dict(threshold_far=24, threshold_near=1,  coeff_far=0.90, coeff_near=0.85, coeff_hot=0.60),
}

class DynamicDiscountStrategy:
    def __init__(self, threshold_far, threshold_near, coeff_far, coeff_near, coeff_hot, strategy_name="custom"):
        self.threshold_far   = threshold_far
        self.threshold_near  = threshold_near
        self.coeff_far       = coeff_far
        self.coeff_near      = coeff_near
        self.coeff_hot       = coeff_hot
        self.strategy_name   = strategy_name

    def calculate(self, base_price: float, minutes_to_slot: float) -> float:
        hours = minutes_to_slot / 60
        if hours > self.threshold_far:
            return base_price * self.coeff_far
        elif hours > self.threshold_near:
            return base_price * self.coeff_near
        else:
            return base_price * self.coeff_hot


def get_strategy_from_row(row: dict) -> DynamicDiscountStrategy:
    return DynamicDiscountStrategy(
        threshold_far=row["threshold_far"],
        threshold_near=row["threshold_near"],
        coeff_far=row["coeff_far"],
        coeff_near=row["coeff_near"],
        coeff_hot=row["coeff_hot"],
        strategy_name=row.get("strategy_name", "custom"),
    )


def get_strategy(service_id: int, company_id: int = COMPANY_ID) -> DynamicDiscountStrategy:
    res = supabase.table("service_strategies") \
        .select("*") \
        .eq("company_id", company_id) \
        .eq("service_id", service_id) \
        .eq("status", "published") \
        .execute()
    if res.data:
        return get_strategy_from_row(res.data[0])
    d = STRATEGY_DEFAULTS["step"]
    return DynamicDiscountStrategy(**d, strategy_name="step")


def get_published_services(company_id: int = COMPANY_ID) -> list:
    """Читает published услуги из Supabase отсортированные по display_order."""
    res = supabase.table("service_strategies") \
        .select("service_id,service_name,category,strategy_name,duration_min,"
                "threshold_far,threshold_near,coeff_far,coeff_near,coeff_hot,status") \
        .eq("company_id", company_id) \
        .eq("status", "published") \
        .order("display_order") \
        .execute()
    return res.data or []


# ── Pricing ────────────────────────────────────────────────────────────────

def get_lovi_price(base_price: float, slot_datetime: datetime, strategy: DynamicDiscountStrategy) -> dict | None:
    now = datetime.now(tz=timezone.utc)
    minutes_to_slot = (slot_datetime.astimezone(timezone.utc) - now).total_seconds() / 60
    if minutes_to_slot < 0:
        return None
    lovi_price = strategy.calculate(base_price, minutes_to_slot)
    lovi_price = max(lovi_price, base_price * 0.35)
    discount_pct = round((1 - lovi_price / base_price) * 100)
    return {
        "base_price":      int(base_price),
        "lovi_price":      int(lovi_price),
        "discount_pct":    discount_pct,
        "minutes_to_slot": int(minutes_to_slot),
    }


# ── Общая функция получения слотов ────────────────────────────────────────

async def _fetch_slots_for_date(
    fetch_date: str,
    services: list,        # список строк из service_strategies
    svc_prices: dict,      # service_id → price_min
    token: str,
    company_id: int = COMPANY_ID,
    gap_minutes: int = 60,
    max_per_service: int = 2,
) -> list:
    import asyncio
    now_ts = datetime.now(tz=timezone.utc).timestamp()
    gap_sec = gap_minutes * 60

    async def fetch_one(svc):
        svc_id = svc["service_id"]
        try:
            slots_resp = await get_book_times(company_id, token, fetch_date, svc_id)
        except Exception as e:
            print(f"[SLOTS] timeout service {svc_id}: {e}")
            return []

        strategy = get_strategy_from_row(svc)
        # Длительность из Supabase (надёжнее чем seance_length из YCLIENTS)
        duration_min = svc.get("duration_min") or 60

        all_slots = slots_resp.get("data", [])
        valid = [s for s in all_slots
                 if datetime.fromisoformat(s["datetime"]).timestamp() - now_ts >= gap_sec]

        items = []
        for slot in valid[:max_per_service]:
            slot_dt = datetime.fromisoformat(slot["datetime"])
            base_price = svc_prices.get(svc_id, 5000)
            pricing = get_lovi_price(base_price, slot_dt, strategy)
            if not pricing:
                continue
            items.append({
                "time":         slot["time"],
                "datetime":     slot["datetime"],
                "slot_date":    fetch_date,
                "service_id":   svc_id,
                "service_name": svc["service_name"],
                "category":     svc.get("category", ""),
                "duration_min": duration_min,
                "strategy":     strategy.strategy_name,
                "tag":          None,
                **pricing,
            })
        return items

    all_results = await asyncio.gather(*[fetch_one(svc) for svc in services])
    results = []
    for items in all_results:
        results.extend(items)
    return results


def _get_svc_prices(services: list) -> dict:
    """Получает цены услуг из таблицы services."""
    ids = [s["service_id"] for s in services]
    if not ids:
        return {}
    res = supabase.table("services").select("id,price_min").in_("id", ids).execute()
    return {r["id"]: r["price_min"] for r in (res.data or [])}


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
    strategy = get_strategy(service_id)

    # duration_min из service_strategies
    str_res = supabase.table("service_strategies").select("duration_min") \
        .eq("company_id", COMPANY_ID).eq("service_id", service_id).execute()
    duration_min = str_res.data[0]["duration_min"] if str_res.data else 60

    result = []
    for slot in slots_raw:
        if int(slot["time"].split(":")[1]) not in (0, 30):
            continue
        slot_dt = datetime.fromisoformat(slot["datetime"])
        pricing = get_lovi_price(base_price, slot_dt, strategy)
        if pricing:
            result.append({
                "time":         slot["time"],
                "datetime":     slot["datetime"],
                "duration_min": duration_min,
                **pricing
            })
    return {"date": date, "service_id": service_id, "slots": result}


@router.get("/price")
async def get_price(
    base_price: int = Query(...),
    slot_time: str = Query(..., description="ISO: 2026-05-06T18:00:00+03:00")
):
    slot_dt = datetime.fromisoformat(slot_time)
    d = STRATEGY_DEFAULTS["step"]
    strategy = DynamicDiscountStrategy(**d, strategy_name="step")
    pricing = get_lovi_price(base_price, slot_dt, strategy)
    if not pricing:
        raise HTTPException(status_code=400, detail="Slot is in the past")
    return pricing


@router.get("/featured")
async def get_featured(date: str = Query(None)):
    """BentoGrid — топ слоты. Читает published услуги из Supabase."""
    if not date:
        date = dt_module.today().isoformat()

    token    = get_user_token()
    services = get_published_services(COMPANY_ID)

    if not services:
        return {"date": date, "slots": [], "error": "no_published_services"}

    svc_prices = _get_svc_prices(services)

    results = await _fetch_slots_for_date(date, services, svc_prices, token)

    # Fallback 1: нет premium → добавляем один premium из ближайших дней
    if not any(s["strategy"] == "premium" for s in results):
        for delta in range(1, 8):
            next_date = (dt_module.fromisoformat(date) + timedelta(days=delta)).isoformat()
            extra = await _fetch_slots_for_date(next_date, services, svc_prices, token)
            premium_extra = [s for s in extra if s["strategy"] == "premium"]
            if premium_extra:
                results = [premium_extra[0]] + results
                break

    # Fallback 2: мало слотов → добираем из следующего дня
    if len(results) < 3:
        for delta in range(1, 8):
            next_date = (dt_module.fromisoformat(date) + timedelta(days=delta)).isoformat()
            extra = await _fetch_slots_for_date(next_date, services, svc_prices, token)
            seen = {r["datetime"] for r in results}
            results += [s for s in extra if s["datetime"] not in seen]
            if len(results) >= 3:
                break

    # Сортировка: premium первыми, внутри — по времени
    strategy_order = {"premium": 0, "popular": 1, "step": 2, "custom": 3}
    results.sort(key=lambda x: (strategy_order.get(x["strategy"], 9), x["datetime"]))
    results = results[:8]

    # Теги
    tagged_premium = tagged_popular = False
    for slot in results:
        if not tagged_premium and slot["strategy"] == "premium":
            slot["tag"] = "Лучшее предложение"
            tagged_premium = True
        elif not tagged_popular and slot["strategy"] == "popular":
            slot["tag"] = "Популярное"
            tagged_popular = True

    return {"date": date, "slots": results}


@router.get("/slots-stream")
async def get_slots_stream(date: str = Query(None)):
    """AllSlots — ближайшие окошки строго по времени."""
    if not date:
        date = dt_module.today().isoformat()

    token    = get_user_token()
    services = get_published_services(COMPANY_ID)

    if not services:
        return {"date": date, "slots": []}

    svc_prices = _get_svc_prices(services)

    results = await _fetch_slots_for_date(
        date, services, svc_prices, token, max_per_service=3
    )

    # Добираем завтра если мало
    if len(results) < 3:
        next_date = (dt_module.fromisoformat(date) + timedelta(days=1)).isoformat()
        extra = await _fetch_slots_for_date(
            next_date, services, svc_prices, token, max_per_service=2
        )
        seen = {r["datetime"] for r in results}
        results += [s for s in extra if s["datetime"] not in seen]

    # Дедупликация
    seen = set()
    deduped = []
    for s in results:
        key = (s["service_id"], s["datetime"])
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    deduped.sort(key=lambda x: x["minutes_to_slot"])
    return {"date": date, "slots": deduped[:12]}


@router.get("/strategies")
async def get_strategies(company_id: int = Query(COMPANY_ID)):
    res = supabase.table("service_strategies") \
        .select("*") \
        .eq("company_id", company_id) \
        .order("display_order") \
        .execute()
    return {"strategies": res.data}


@router.put("/strategies/{service_id}")
async def update_strategy(service_id: int, data: dict = Body(...)):
    company_id = data.get("company_id", COMPANY_ID)
    allowed = {"threshold_far", "threshold_near", "coeff_far", "coeff_near", "coeff_hot",
               "strategy_name", "status", "category", "display_order", "duration_min"}
    update = {k: v for k, v in data.items() if k in allowed}
    if not update:
        raise HTTPException(400, "Нет полей для обновления")
    update["updated_at"] = datetime.utcnow().isoformat()
    res = supabase.table("service_strategies") \
        .update(update) \
        .eq("company_id", company_id) \
        .eq("service_id", service_id) \
        .execute()
    if not res.data:
        raise HTTPException(404, "Стратегия не найдена")
    return {"ok": True, "strategy": res.data[0]}


# ── Sync Services ──────────────────────────────────────────────────────────

YCLIENTS_CATEGORY_MAP = {
    27323178: "spa",
    19468178: "head",
    19658180: "back",
    27461844: "spa",
}

EXCLUDED_SERVICE_IDS = {22296048, 22296054, 22296057}

@router.post("/sync-services")
async def sync_services(authorization: str = Header(...)):
    """Синхронизация услуг из YCLIENTS в Supabase service_strategies"""
    import os, httpx
    company_id = get_salon_id(authorization)

    salon = supabase.table("salons").select("user_token").eq("company_id", company_id).single().execute().data
    token = salon["user_token"]
    partner_token = os.getenv("YCLIENTS_PARTNER_TOKEN", "").strip()

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"https://api.yclients.com/api/v1/services/{company_id}",
            headers={
                "Authorization": f"Bearer {partner_token}, User {token}",
                "Accept": "application/vnd.api.v2+json"
            }
        )

    if r.status_code != 200:
        raise HTTPException(502, f"YCLIENTS error: {r.status_code}")

    services = r.json().get("data") or []
    filtered = [
        s for s in services
        if s.get("category_id") in YCLIENTS_CATEGORY_MAP
        and s.get("id") not in EXCLUDED_SERVICE_IDS
    ]

    existing_res = supabase.table("service_strategies") \
        .select("service_id,status,strategy_name,threshold_far,threshold_near,"
                "coeff_far,coeff_near,coeff_hot,duration_min") \
        .eq("company_id", company_id).execute()
    existing = {row["service_id"]: row for row in existing_res.data}

    added, skipped = [], []

    for svc in filtered:
        sid      = svc["id"]
        category = YCLIENTS_CATEGORY_MAP[svc["category_id"]]
        # duration из YCLIENTS в секундах → минуты
        duration_min = (svc.get("duration") or 0) // 60 or 60

        if sid in existing:
            supabase.table("service_strategies").update({
                "service_name": svc["title"],
                "category":     category,
                "duration_min": duration_min,
            }).eq("company_id", company_id).eq("service_id", sid).execute()
            skipped.append(sid)
        else:
            supabase.table("service_strategies").insert({
                "company_id":    company_id,
                "service_id":    sid,
                "service_name":  svc["title"],
                "category":      category,
                "duration_min":  duration_min,
                "strategy_name": "step",
                "status":        "draft",
                "display_order": 0,
                "threshold_far": 24,
                "threshold_near":1,
                "coeff_far":     0.90,
                "coeff_near":    0.85,
                "coeff_hot":     0.60,
            }).execute()
            added.append(sid)

    return {"ok": True, "added": len(added), "updated": len(skipped), "added_ids": added}


# ── Book ───────────────────────────────────────────────────────────────────

@router.post("/book")
async def lovi_book(data: dict = Body(...)):
    import uuid, os, hmac, hashlib, re
    from app.yclients import create_client, find_client_by_phone

    token = get_user_token()

    row = {
        "company_id":    COMPANY_ID,
        "service_id":    data.get("service_id"),
        "service_title": data.get("service_title"),
        "datetime":      data.get("datetime"),
        "duration":      data.get("duration"),
        "total_price":   data.get("lovi_price"),
        "master_id":     data.get("staff_id"),
        "master_name":   data.get("staff_name"),
        "client_name":   data.get("client_name"),
        "client_phone":  data.get("client_phone"),
        "client_email":  data.get("client_email", ""),
        "user_id":       data.get("user_id") or None,
        "status":        "pending",
        "source":        "lovi",
    }
    _secret = os.getenv("BOOKING_CODE_SECRET", "lovi-secret-2026")
    _raw = hmac.new(_secret.encode(), f"{uuid.uuid4()}".encode(), hashlib.sha256).hexdigest()[:10].upper()
    row["booking_code"] = f"{_raw[:4]}-{_raw[4:8]}"
    booking_result = supabase.table("bookings").insert(row).execute()
    booking_id = booking_result.data[0]["id"]

    try:
        existing = await create_client(
            COMPANY_ID, token,
            name=data.get("client_name"),
            phone=data.get("client_phone"),
            email=data.get("client_email", "")
        )
        yclients_client_id = existing.get("data", {}).get("id") if existing and existing.get("success") else None
        if not yclients_client_id:
            normalized = "+" + re.sub(r"\D", "", data.get("client_phone", ""))
            if normalized.startswith("+8"):
                normalized = "+7" + normalized[2:]
            found = await find_client_by_phone(COMPANY_ID, token, normalized)
            if found:
                yclients_client_id = found.get("id")
        print(f"[LOVI BOOK] client_id={yclients_client_id}")
    except Exception as e:
        print(f"[LOVI BOOK] Ошибка клиента YCLIENTS: {e}")

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
    city  = (data.get("city")  or "").strip()
    email = (data.get("email") or "").strip().lower()
    if not city:
        raise HTTPException(status_code=422, detail="city is required")
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="valid email is required")
    try:
        supabase.table("city_waitlist").upsert(
            {"city": city, "email": email, "source": "lovi_hero"},
            on_conflict="city,email", ignore_duplicates=True,
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    try:
        import resend as _resend, os
        from app.emails.utils import render_template
        _resend.api_key = os.getenv("RESEND_API_KEY")
        html = render_template(template="city_waitlist", subject="test", email=email, city=city)
        _resend.Emails.send({
            "from": "«Лови» <noreply@lovi.today>",
            "to": email,
            "subject": f"«Лови» скоро в {city}",
            "html": html,
        })
    except Exception as e:
        import logging; logging.error(f"city_waitlist email error: {e}")
    return {"ok": True}


@router.post("/city-partner")
async def city_partner_request(data: dict = Body(...)):
    city       = (data.get("city")       or "").strip()
    name       = (data.get("name")       or "").strip()
    phone      = (data.get("phone")      or "").strip()
    email      = (data.get("email")      or "").strip() or None
    salon_name = (data.get("salon_name") or "").strip()
    address    = (data.get("address")    or "").strip() or None
    crm        = (data.get("crm")        or "").strip() or None
    if not city:       raise HTTPException(status_code=422, detail="city is required")
    if not name:       raise HTTPException(status_code=422, detail="name is required")
    if not phone or len(phone.replace("+","").replace(" ","")) < 10:
        raise HTTPException(status_code=422, detail="valid phone is required")
    if not salon_name: raise HTTPException(status_code=422, detail="salon_name is required")
    try:
        supabase.table("city_partner_requests").insert({
            "city": city, "name": name, "phone": phone,
            "salon_name": salon_name, "address": address, "crm": crm,
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}


# ── Connect (YCLIENTS marketplace) ────────────────────────────────────────

@router.post("/connect")
async def lovi_connect(data: dict = Body(...)):
    import os, secrets as _secrets, resend as _resend
    from jose import jwt as jose_jwt
    from app.emails.utils import render_template

    salon_id  = data.get("salon_id")
    user_info = data.get("user_info", {})
    if not salon_id:
        raise HTTPException(400, "salon_id обязателен")

    existing = supabase.table("salons").select("user_token").eq("company_id", int(salon_id)).execute()
    existing_token = existing.data[0]["user_token"] if existing.data else ""
    res = supabase.table("salons").upsert({
        "company_id":       int(salon_id),
        "user_token":       existing_token or "",
        "yclients_user_id": str(user_info.get("id", "")),
        "owner_name":       user_info.get("name", ""),
        "owner_phone":      user_info.get("phone", ""),
        "owner_email":      user_info.get("email", ""),
        "salon_name":       user_info.get("salon_name", ""),
        "connected_at":     datetime.utcnow().isoformat(),
        "is_active":        True,
    }, on_conflict="company_id").execute()

    salon  = res.data[0]
    secret = os.getenv("JWT_SECRET", "lovi-secret-change-in-prod")
    token  = jose_jwt.encode(
        {"sub": str(salon["id"]), "company_id": int(salon_id),
         "exp": datetime.utcnow() + timedelta(days=365)},
        secret, algorithm="HS256"
    )
    try:
        ml_token   = _secrets.token_urlsafe(32)
        ml_expires = (datetime.utcnow() + timedelta(days=7)).isoformat()
        supabase.table("salon_magic_links").insert({
            "company_id": int(salon_id), "token": ml_token, "expires_at": ml_expires,
        }).execute()
        magic_link = f"https://lovi.today/salon/auth?token={ml_token}"
        _resend.api_key = os.getenv("RESEND_API_KEY")
        owner_email = user_info.get("email", "")
        if owner_email:
            html = render_template(
                template="salon_welcome", subject="Добро пожаловать в «Лови»",
                owner_name=user_info.get("name", "Партнёр"),
                salon_name=user_info.get("salon_name", "Ваш салон"),
                email=owner_email, magic_link=magic_link,
            )
            _resend.Emails.send({
                "from": "«Лови» <noreply@lovi.today>",
                "to": owner_email,
                "subject": "Добро пожаловать в «Лови»",
                "html": html,
            })
    except Exception as e:
        import logging; logging.error(f"salon welcome email error: {e}")

    return {"ok": True, "token": token, "salon": salon}


# ── Salon Dashboard ────────────────────────────────────────────────────────

def get_salon_id(authorization: str = Header(...)) -> int:
    import os
    from jose import jwt as jose_jwt, JWTError
    try:
        token   = authorization.replace("Bearer ", "")
        secret  = os.getenv("JWT_SECRET", "lovi-secret-change-in-prod")
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
    token = salon.get("user_token", "")
    if token:
        try:
            import httpx, os
            from datetime import date as dt_date
            partner_token = os.getenv("YCLIENTS_PARTNER_TOKEN", "").strip()
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
            d = resp.json()
            if resp.status_code == 200 and d.get("success"):
                new_status, status_message = "ok", None
            else:
                msg = d.get("meta", {}).get("message", "")
                new_status = "no_access" if "прав" in msg.lower() else "error"
                status_message = msg
        except Exception as e:
            new_status, status_message = "error", str(e)
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


# ── Salon Magic Link ───────────────────────────────────────────────────────

import secrets, resend as _resend
from app.emails.utils import render_template

@router.post("/salon/magic-link")
async def salon_magic_link(data: dict = Body(...)):
    email = (data.get("email") or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(422, "Укажите email")
    res = supabase.table("salons") \
        .select("id,company_id,owner_name,salon_name,owner_email") \
        .eq("owner_email", email).execute()
    if not res.data:
        return {"ok": True}
    salon   = res.data[0]
    token   = secrets.token_urlsafe(32)
    expires = (datetime.utcnow() + timedelta(days=7)).isoformat()
    supabase.table("salon_magic_links").insert({
        "company_id": salon["company_id"], "token": token, "expires_at": expires,
    }).execute()
    magic_link = f"https://lovi.today/salon/auth?token={token}"
    import os
    _resend.api_key = os.getenv("RESEND_API_KEY")
    html = render_template(
        template="salon_welcome", subject="Вход в кабинет «Лови»",
        owner_name=salon["owner_name"] or "Партнёр",
        salon_name=salon["salon_name"] or "Ваш салон",
        email=email, magic_link=magic_link,
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
    from datetime import timezone as tz
    res = supabase.table("salon_magic_links").select("*").eq("token", token).execute()
    if not res.data:
        raise HTTPException(400, "Ссылка недействительна")
    rec = res.data[0]
    if rec["used"]:
        raise HTTPException(400, "Ссылка уже использована")
    expires = datetime.fromisoformat(rec["expires_at"].replace("Z", "+00:00"))
    if datetime.now(tz.utc) > expires:
        raise HTTPException(400, "Ссылка истекла")
    supabase.table("salon_magic_links").update({"used": True}).eq("token", token).execute()
    salon = supabase.table("salons").select("*") \
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

# ── Zones 2GIS ─────────────────────────────────────────────────────────────
@router.get("/zones/search")
async def search_zones(
    lat: float = Query(...),
    lon: float = Query(...),
    radius: int = Query(600),
    q: str = Query("массаж")
):
    """Поиск массажных салонов в радиусе через 2GIS API"""
    import os, httpx

    key = os.getenv("DGIS_API_KEY")
    if not key:
        raise HTTPException(500, "DGIS_API_KEY не настроен")

    url = "https://catalog.api.2gis.com/3.0/items"
    params = {
        "q": q,
        "point": f"{lon},{lat}",   # 2GIS принимает lon,lat!
        "radius": radius,
        "fields": "items.point,items.address,items.rating",
        "key": key,
        "locale": "ru_RU",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
        if resp.status_code != 200:
            raise HTTPException(502, f"2GIS ответил {resp.status_code}")
        data = resp.json()
        items = []
        for it in data.get("result", {}).get("items", []):
            items.append({
                "name": it.get("name"),
                "address": it.get("address_name", ""),
                "rating": it.get("rating"),
            })
        return {"count": len(items), "items": items}
    except Exception as e:
        raise HTTPException(502, f"Ошибка запроса к 2GIS: {str(e)}")

# ── Cancel Booking ─────────────────────────────────────────────────────────

@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: int, authorization: str = Header(...)):
    import os
    from jose import jwt as jose_jwt, JWTError
    from datetime import timezone as tz
    try:
        token   = authorization.replace("Bearer ", "")
        secret  = os.getenv("JWT_SECRET", "lovi-secret-change-in-prod")
        payload = jose_jwt.decode(token, secret, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (JWTError, KeyError):
        raise HTTPException(401, "Невалидный токен")

    res = supabase.table("bookings").select("*").eq("id", booking_id).execute()
    if not res.data:
        raise HTTPException(404, "Бронь не найдена")
    booking = res.data[0]
    if booking.get("user_id") != user_id:
        raise HTTPException(403, "Нет доступа")
    if booking["status"] not in ("confirmed", "waiting_payment", "pending"):
        raise HTTPException(400, f"Нельзя отменить бронь со статусом {booking['status']}")

    slot_dt = datetime.fromisoformat(booking["datetime"])
    if slot_dt.tzinfo is None:
        slot_dt = slot_dt.replace(tzinfo=tz.utc)
    hours_before = (slot_dt - datetime.now(tz=tz.utc)).total_seconds() / 3600
    if hours_before < 2:
        raise HTTPException(400, "Отмена невозможна менее чем за 2 часа до визита")

    yclients_cancelled = False
    if booking.get("yclients_record_id"):
        try:
            import httpx
            partner_token = os.getenv("YCLIENTS_PARTNER_TOKEN", "").strip()
            salon = supabase.table("salons").select("user_token") \
                .eq("company_id", booking["company_id"]).single().execute().data
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.delete(
                    f"https://api.yclients.com/api/v1/record/{booking['company_id']}/{booking['yclients_record_id']}",
                    headers={
                        "Authorization": f"Bearer {partner_token}, User {salon['user_token']}",
                        "Accept": "application/vnd.api.v2+json"
                    }
                )
            yclients_cancelled = resp.status_code == 200
        except Exception as e:
            print(f"[CANCEL] YCLIENTS error: {e}")

    supabase.table("bookings").update({"status": "cancelled_by_client"}).eq("id", booking_id).execute()

    refund_amount = booking.get("total_price", 0)
    supabase.table("balance_transactions").insert({
        "user_id": user_id, "booking_id": booking_id,
        "amount": refund_amount * 100, "type": "refund",
    }).execute()
    user_res = supabase.table("users").select("lovi_balance").eq("id", user_id).single().execute()
    current_balance = user_res.data.get("lovi_balance", 0) or 0
    supabase.table("users").update({
        "lovi_balance": current_balance + refund_amount
    }).eq("id", user_id).execute()

    try:
        import resend as _resend
        from app.emails.utils import render_template
        _resend.api_key = os.getenv("RESEND_API_KEY")
        if booking.get("client_email"):
            html = render_template(
                template="booking_cancelled", subject="Бронирование отменено",
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
        import logging; logging.error(f"cancel email error: {e}")

    return {
        "ok": True,
        "refunded": refund_amount,
        "new_balance": current_balance + refund_amount,
        "yclients_cancelled": yclients_cancelled,
    }