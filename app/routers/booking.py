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

@router.get("/slots")
async def get_slots(date: str, duration: int):
    """Свободные слоты на дату с учётом длительности"""
    # Получаем все записи на эту дату
    result = supabase.table("records").select(
        "date, duration, staff_name"
    ).eq("company_id", COMPANY_ID).gte(
        "date", f"{date} 00:00:00"
    ).lte(
        "date", f"{date} 23:59:59"
    ).neq("attendance", -1).execute()

    booked = result.data

    # Рабочие часы: 10:00 - 21:00, слоты по 30 минут
    slots = []
    start = datetime.strptime(f"{date} 10:00", "%Y-%m-%d %H:%M")
    end = datetime.strptime(f"{date} 21:00", "%Y-%m-%d %H:%M")
    now = datetime.now()

    current = start
    while current + timedelta(seconds=duration) <= end:
        slot_end = current + timedelta(seconds=duration)

        # Проверяем пересечение с существующими записями
        is_free = True
        for b in booked:
            b_start = datetime.fromisoformat(b["date"])
            b_end = b_start + timedelta(seconds=b.get("duration", 3600))
            if not (slot_end <= b_start or current >= b_end):
                is_free = False
                break

        if is_free and current > now:
            slots.append(current.strftime("%H:%M"))

        current += timedelta(minutes=30)

    return {"date": date, "slots": slots}

@router.get("/staff")
async def get_available_staff(datetime: str, duration: int):
    """Мастера доступные в выбранный слот"""
    from datetime import datetime as dt, timedelta

    slot_start = dt.fromisoformat(datetime)
    slot_end = slot_start + timedelta(seconds=duration)
    date = datetime.split(" ")[0]

    # Только активные мастера
    all_staff = supabase.table("staff").select("id, name, specialization, avatar, rating").eq(
        "company_id", COMPANY_ID
    ).eq("is_active", True).execute().data

    # Занятые записи в этот день
    booked = supabase.table("records").select(
        "staff_name, date, duration"
    ).eq("company_id", COMPANY_ID).gte(
        "date", f"{date} 00:00:00"
    ).lte(
        "date", f"{date} 23:59:59"
    ).neq("attendance", -1).execute().data

    # Находим занятых мастеров в этот слот
    busy_staff = set()
    for b in booked:
        b_start = dt.fromisoformat(b["date"])
        b_end = b_start + timedelta(seconds=b.get("duration", 3600))
        if not (slot_end <= b_start or slot_start >= b_end):
            busy_staff.add(b["staff_name"])

    available = [s for s in all_staff if s["name"] not in busy_staff]
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

    # 5. TODO: заменить на реальный ЮKassa платёж
    payment_url = f"http://localhost:5174/success?booking_id={booking_id}"

    return {"booking_id": booking_id, "payment_url": payment_url}

@router.get("/nearest_slot")
async def get_nearest_slot(duration: int):
    """Ближайший свободный слот на ближайшие 30 дней"""
    from datetime import datetime, timedelta

    now = datetime.now()
    for i in range(1, 31):
        date = (now + timedelta(days=i)).strftime("%Y-%m-%d")
        result = supabase.table("records").select(
            "date, duration"
        ).eq("company_id", COMPANY_ID).gte(
            "date", f"{date} 00:00:00"
        ).lte(
            "date", f"{date} 23:59:59"
        ).neq("attendance", -1).execute()

        booked = result.data
        start = datetime.strptime(f"{date} 10:00", "%Y-%m-%d %H:%M")
        end = datetime.strptime(f"{date} 21:00", "%Y-%m-%d %H:%M")
        current = start

        while current + timedelta(seconds=duration) <= end:
            slot_end = current + timedelta(seconds=duration)
            is_free = True
            for b in booked:
                b_start = datetime.fromisoformat(b["date"])
                b_end = b_start + timedelta(seconds=b.get("duration", 3600))
                if not (slot_end <= b_start or current >= b_end):
                    is_free = False
                    break
            if is_free:
                return {"date": date, "time": current.strftime("%H:%M")}
            current += timedelta(minutes=30)

    return {"date": None, "time": None}

@router.get("/booking/{booking_id}")
async def get_booking(booking_id: int):
    result = supabase.table("bookings").select("*").eq("id", booking_id).execute()
    if not result.data:
        return {"error": "Запись не найдена"}
    return result.data[0]
