from fastapi import APIRouter
from app.database import supabase
import os

router = APIRouter(prefix="/booking", tags=["Виджет записи"])

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
    time = datetime.split(" ")[1] if " " in datetime else "00:00"

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
        if time in times:
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

    # 4. Создаём запись в YCLIENTS
    try:
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
        await create_record(COMPANY_ID, user_token, record_data)
    except Exception as e:
        print(f"[BOOKING] Ошибка создания записи в YCLIENTS: {e}")

    # 5. Создаём платёж в ЮKassa
    try:
        from app.routers.payments import get_yookassa
        import uuid
        Payment = get_yookassa()
        base_url = os.getenv("BOOKING_BASE_URL", "https://insalon.onrender.com")
        payment = Payment.create({
            "amount": {"value": "2000.00", "currency": "RUB"},
            "confirmation": {
                "type": "embedded",
            },
            "capture": True,
            "description": f"Бронирование #{booking_id} — HeadSPA Beauty",
            "metadata": {"booking_id": str(booking_id)}
        }, uuid.uuid4())
        supabase.table("bookings").update({
            "payment_id": payment.id,
            "status": "waiting_payment"
        }).eq("id", booking_id).execute()
        import json as _json
        conf_data = _json.loads(payment.confirmation.json())
        payment_url = conf_data.get("confirmation_url", "")
        confirmation_token = conf_data.get("confirmation_token")
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

@router.get("/booking/{booking_id}")
async def get_booking(booking_id: int):
    result = supabase.table("bookings").select("*").eq("id", booking_id).execute()
    if not result.data:
        return {"error": "Запись не найдена"}
    return result.data[0]
