from fastapi import APIRouter, HTTPException, Header
from app.database import supabase
import os
import re

router = APIRouter(prefix="/api/booking", tags=["Виджет записи"])

COMPANY_ID = int(os.getenv("YCLIENTS_COMPANY_ID"))

@router.get("/categories")
async def get_categories():
    result = supabase.table("service_categories").select("*").eq(
        "company_id", COMPANY_ID
    ).order("weight", desc=True).execute()
    return result.data

@router.get("/services")
async def get_services(category_id: int):
    result = supabase.table("services").select("*").eq(
        "company_id", COMPANY_ID
    ).eq("category_id", category_id).gt("seance_length", 0).gt("price_min", 0).execute()
    return result.data

from datetime import datetime, timedelta
from app.yclients import get_book_times

@router.get("/slots")
async def get_slots(date: str, duration: int, service_id: int = 0):
    """Свободные слоты из YCLIENTS в реальном времени"""
    salon = supabase.table("salons").select("user_token").eq("company_id", COMPANY_ID).execute().data[0]
    user_token = salon["user_token"]

    data = await get_book_times(COMPANY_ID, user_token, date, service_id)
    times = data.get("data", [])
    slots = [t["time"] for t in times]
    return {"date": date, "slots": slots}

@router.get("/staff")
async def get_available_staff(datetime: str, duration: int, service_id: int = 0):
    """Мастера доступные в выбранный слот — проверка через YCLIENTS"""
    date = datetime.split(" ")[0]
    time_full = datetime.split(" ")[1] if " " in datetime else "00:00"
    time = ":".join(time_full.split(":")[:2])  # берём только HH:MM без секунд

    # Только активные мастера
    all_staff = supabase.table("staff").select(
        "id, name, specialization, avatar, rating"
    ).eq("company_id", COMPANY_ID).eq("is_active", True).execute().data

    salon = supabase.table("salons").select("user_token").eq(
        "company_id", COMPANY_ID
    ).execute().data[0]
    user_token = salon["user_token"]

    # Проверяем каждого мастера через YCLIENTS book_times
    available = []
    for staff in all_staff:
        data = await get_book_times(COMPANY_ID, user_token, date, service_id, staff["id"])
        times = [t["time"] for t in data.get("data", [])]
        if time in times or time_full[:5] in times:
            available.append(staff)

    return available

from fastapi import Body
from app.yclients import create_client, create_record

@router.post("/create")
async def create_booking(data: dict = Body(...)):
    """Создать бронирование → лид → запись в YCLIENTS → ссылка на оплату"""
    salon = supabase.table("salons").select("*").eq("company_id", COMPANY_ID).execute().data[0]
    user_token = salon["user_token"]

    # 1. Сохраняем бронирование
    row = {
        "company_id": COMPANY_ID,
        "service_id": data.get("service_id"),
        "service_title": data.get("service_title"),
        "datetime": data.get("datetime"),
        "duration": data.get("duration"),
        "total_price": data.get("total_price"),
        "master_id": data.get("master_id"),
        "master_name": data.get("master_name"),
        "client_name": data.get("client_name"),
        "client_phone": data.get("client_phone"),
        "client_email": data.get("client_email"),
        "extras": data.get("extras", []),
        "status": "pending",
    }
    booking_result = supabase.table("bookings").insert(row).execute()
    booking_id = booking_result.data[0]["id"]

    # 2. Создаём лид
    lead_row = {
        "company_id": COMPANY_ID,
        "name": data.get("client_name"),
        "phone": data.get("client_phone"),
        "email": data.get("client_email"),
        "booking_id": booking_id,
        "status": "new",
    }

    # 3. Ищем клиента в YCLIENTS по телефону
    yclients_client_id = None
    try:
        existing = await create_client(
            COMPANY_ID, user_token,
            name=data.get("client_name"),
            phone=data.get("client_phone"),
            email=data.get("client_email", "")
        )
        print(f"[BOOKING] YCLIENTS ответ: {existing}")
        if existing.get("success"):
            yclients_client_id = existing.get("data", {}).get("id")
            lead_row["yclients_client_id"] = yclients_client_id
        elif "уже существует" in str(existing.get("meta", {}).get("message", "")):
            # Нормализуем телефон: +7 (926) 930-84-84 → +79269308484
            import re
            raw_phone = data.get("client_phone", "")
            normalized_phone = "+" + re.sub(r"\D", "", raw_phone)
            if normalized_phone.startswith("+8"):
                normalized_phone = "+7" + normalized_phone[2:]
            from app.yclients import find_client_by_phone
            found = await find_client_by_phone(COMPANY_ID, user_token, normalized_phone)
            print(f"[BOOKING] Поиск по телефону {normalized_phone}: {found}")
            if found:
                yclients_client_id = found.get("id")
                lead_row["yclients_client_id"] = yclients_client_id
                print(f"[BOOKING] Найден существующий клиент: {yclients_client_id}")
    except Exception as e:
        import traceback
        print(f"[BOOKING] Ошибка создания клиента в YCLIENTS: {e}")
        print(traceback.format_exc())

    supabase.table("leads").insert(lead_row).execute()

    # 4. Создаём запись в YCLIENTS (fire-and-forget, не блокируем ответ)
    import asyncio
    record_data = {
        "staff_id": data.get("master_id"),
        "services": [{"id": data.get("service_id")}],
        "client": {"id": yclients_client_id} if yclients_client_id else {
            "name": data.get("client_name"),
            "phone": data.get("client_phone"),
        },
        "datetime": data.get("datetime").replace(" ", "T"),
        "seance_length": data.get("duration"),
        "comment": f"insalon | booking_id={booking_id}",
    }
    async def _create_record_bg():
        try:
            await create_record(COMPANY_ID, user_token, record_data)
            print(f"[BOOKING] YCLIENTS запись создана для booking_id={booking_id}")
        except Exception as e:
            print(f"[BOOKING] Ошибка создания записи в YCLIENTS: {e}")
    asyncio.create_task(_create_record_bg())

    # 5. Создаём платёж в ЮKassa
    try:
        from app.routers.payments import get_yookassa
        import uuid
        Payment = get_yookassa()
        base_url = os.getenv("BOOKING_BASE_URL", "https://insalon.onrender.com")
        base_url = os.getenv("BOOKING_BASE_URL", "https://insalon.onrender.com")
        payment = Payment.create({
            "amount": {"value": "2000.00", "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": f"{base_url}/booking/?booking_id={booking_id}"
            },
            "capture": True,
            "description": f"Бронирование #{booking_id} — HeadSPA Beauty",
            "metadata": {"booking_id": str(booking_id)}
        }, uuid.uuid4())
        supabase.table("bookings").update({
            "payment_id": payment.id,
            "status": "waiting_payment"
        }).eq("id", booking_id).execute()
        payment_url = payment.confirmation.confirmation_url
        confirmation_token = None
    except Exception as e:
        print(f"[PAYMENT] Ошибка создания платежа: {e}")
        base_url = os.getenv("BOOKING_BASE_URL", "https://insalon.onrender.com")
        payment_url = f"{base_url}/booking/?booking_id={booking_id}"
        confirmation_token = None

    return {"booking_id": booking_id, "payment_url": payment_url, "confirmation_token": confirmation_token}

@router.get("/nearest_slot")
async def get_nearest_slot(duration: int, service_id: int = 0):
    """Ближайший свободный слот из YCLIENTS"""
    from datetime import datetime, timedelta

    salon = supabase.table("salons").select("user_token").eq("company_id", COMPANY_ID).execute().data[0]
    user_token = salon["user_token"]

    now = datetime.now()
    for i in range(0, 31):
        date = (now + timedelta(days=i)).strftime("%Y-%m-%d")
        data = await get_book_times(COMPANY_ID, user_token, date, service_id)
        times = data.get("data", [])
        if times:
            return {"date": date, "time": times[0]["time"]}

    return {"date": None, "time": None}

def _norm_phone(raw: str) -> str:
    """Приводим телефон к виду 7XXXXXXXXXX — в базе номера лежат в разном формате."""
    d = re.sub(r"\D", "", raw or "")
    if len(d) == 11 and d.startswith("8"):
        d = "7" + d[1:]
    if len(d) == 10:
        d = "7" + d
    return d


@router.get("/active")
async def get_active_bookings(phone: str, x_internal_key: str = Header(None)):
    """Активные (будущие) записи по номеру телефона.

    Персональные данные, поэтому только для внутренних сервисов — по ключу
    INTERNAL_API_KEY в заголовке X-Internal-Key.
    """
    expected = os.getenv("INTERNAL_API_KEY")
    if not expected:
        raise HTTPException(503, "INTERNAL_API_KEY не задан")
    if x_internal_key != expected:
        raise HTTPException(401, "Требуется внутренний ключ")

    target = _norm_phone(phone)
    if len(target) != 11:
        raise HTTPException(400, "Некорректный номер телефона")

    today = datetime.now().strftime("%Y-%m-%d")
    rows = supabase.table("bookings").select(
        "id, service_title, datetime, duration, master_name, total_price, status, booking_code, client_name, client_phone"
    ).eq("company_id", COMPANY_ID).gte("datetime", today).order("datetime").limit(300).execute().data or []

    dead = ("cancelled", "canceled", "отменено")
    items = []
    for r in rows:
        if _norm_phone(r.get("client_phone", "")) != target:
            continue
        if str(r.get("status", "")).lower() in dead:
            continue
        items.append({
            "id": r.get("id"),
            "service_title": r.get("service_title"),
            "datetime": r.get("datetime"),
            "duration": r.get("duration"),
            "master_name": r.get("master_name"),
            "total_price": r.get("total_price"),
            "status": r.get("status"),
            "client_name": r.get("client_name"),
        })

    return {"count": len(items), "items": items}


@router.get("/{booking_id}")
async def get_booking(booking_id: int):
    result = supabase.table("bookings").select("*").eq("id", booking_id).execute()
    if not result.data:
        return {"error": "Запись не найдена"}
    return result.data[0]

@router.post("/checkin/{booking_code}")
async def checkin_booking(booking_code: str):
    result = supabase.table("bookings").select("*").eq("booking_code", booking_code).execute()
    if not result.data:
        raise HTTPException(404, "Бронирование не найдено")
    b = result.data[0]
    if b.get("checkin_used_at"):
        raise HTTPException(400, f"Код уже использован {b['checkin_used_at']}")
    if b.get("status") not in ("paid", "confirmed"):
        raise HTTPException(400, "Бронирование не оплачено")
    from datetime import datetime, timezone
    supabase.table("bookings").update({
        "checkin_used_at": datetime.now(timezone.utc).isoformat()
    }).eq("booking_code", booking_code).execute()
    return {"ok": True, "client_name": b.get("client_name"), "service_title": b.get("service_title"), "datetime": b.get("datetime")}
