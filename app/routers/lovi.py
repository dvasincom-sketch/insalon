from fastapi import APIRouter, Query, HTTPException
from app.yclients import get_book_times, get_services
from app.database import supabase
import math
from datetime import datetime, timezone

router = APIRouter(prefix="/api/lovi", tags=["lovi"])

COMPANY_ID = 1166484

def get_user_token():
    res = supabase.table("salons").select("user_token").eq("company_id", COMPANY_ID).single().execute()
    return res.data["user_token"]

# --- Pricing ---

class StepDiscountStrategy:
    def calculate(self, base_price: float, minutes_to_slot: float) -> float:
        if minutes_to_slot > 1440:
            return base_price * 0.90
        elif minutes_to_slot > 60:
            return base_price * 0.85
        else:
            return base_price * 0.60

STRATEGY = StepDiscountStrategy()

def get_lovi_price(base_price: float, slot_datetime: datetime) -> dict | None:
    now = datetime.now(tz=timezone.utc)
    minutes_to_slot = (slot_datetime.astimezone(timezone.utc) - now).total_seconds() / 60
    if minutes_to_slot < 0:
        return None
    lovi_price = STRATEGY.calculate(base_price, minutes_to_slot)
    lovi_price = max(lovi_price, base_price * 0.35)
    discount_pct = round((1 - lovi_price / base_price) * 100)
    return {
        "base_price": int(base_price),
        "lovi_price": int(lovi_price),
        "discount_pct": discount_pct,
        "minutes_to_slot": int(minutes_to_slot),
    }

# --- Endpoints ---

@router.get("/slots")
async def get_slots(
    date: str = Query(..., description="YYYY-MM-DD"),
    service_id: int = Query(..., description="ID услуги из YCLIENTS")
):
    token = get_user_token()
    slots_raw_resp = await get_book_times(COMPANY_ID, token, date, service_id)
    slots_raw = slots_raw_resp.get("data", [])

    # Базовая цена из таблицы services
    svc = supabase.table("services").select("price_min").eq("id", service_id).single().execute()
    base_price = svc.data["price_min"] if svc.data else 5000

    result = []
    seen_times = set()
    for slot in slots_raw:
        # Только слоты на :00 и :30
        minute = int(slot["time"].split(":")[1])
        if minute not in (0, 30):
            continue
        slot_dt = datetime.fromisoformat(slot["datetime"])
        pricing = get_lovi_price(base_price, slot_dt)
        if pricing:
            result.append({
                "time": slot["time"],
                "datetime": slot["datetime"],
                "duration_min": slot["seance_length"] // 60,
                **pricing
            })

    return {"date": date, "service_id": service_id, "slots": result}


@router.get("/price")
async def get_price(
    base_price: int = Query(...),
    slot_time: str = Query(..., description="ISO: 2026-05-06T18:00:00+03:00")
):
    slot_dt = datetime.fromisoformat(slot_time)
    pricing = get_lovi_price(base_price, slot_dt)
    if not pricing:
        raise HTTPException(status_code=400, detail="Slot is in the past")
    return pricing



@router.get("/featured")
async def get_featured(date: str = Query(None)):
    """Топ слоты дня по всем популярным услугам"""
    from datetime import date as dt
    if not date:
        date = dt.today().isoformat()

    token = get_user_token()

    # Топ услуги с реальными ценами
    featured_services = [
        {"id": 19556836, "name": "«Экспресс» для двоих", "duration": 100},
        {"id": 19655561, "name": "SPA для двоих в будни", "duration": 120},
        {"id": 19468539, "name": "Ручной лимфодренажный массаж", "duration": 190},
    ]

    svc_prices = {}
    svc_res = supabase.table("services").select("id,title,price_min").in_("id", [s["id"] for s in featured_services]).execute()
    for s in svc_res.data:
        svc_prices[s["id"]] = s["price_min"]

    results = []
    for svc in featured_services:
        slots_resp = await get_book_times(COMPANY_ID, token, date, svc["id"])
        slots = slots_resp.get("data", [])
        # Берём только первые 2 слота на сегодня
        for slot in slots[:2]:
            slot_dt = datetime.fromisoformat(slot["datetime"])
            base_price = svc_prices.get(svc["id"], 5000)
            pricing = get_lovi_price(base_price, slot_dt)
            if pricing and base_price >= 3000:
                results.append({
                    "time": slot["time"],
                    "datetime": slot["datetime"],
                    "service_id": svc["id"],
                    "service_name": svc["name"],
                    "category": svc.get("category", "other"),
                    "duration_min": slot["seance_length"] // 60,
                    **pricing
                })

    # Сортируем по времени
    results.sort(key=lambda x: x["datetime"])
    return {"date": date, "slots": results[:8]}


@router.get("/featured")
async def get_featured(date: str = Query(None)):
    """Топ слоты дня по всем популярным услугам"""
    from datetime import date as dt_module
    if not date:
        date = dt_module.today().isoformat()

    token = get_user_token()

    featured_services = [
        {"id": 19655561, "name": "SPA для двоих в будни", "category": "spa"},
        {"id": 19556836, "name": "Экспресс для двоих", "category": "spa"},
        {"id": 19655588, "name": "SPA для мужчин Самурай", "category": "spa"},
        {"id": 19556779, "name": "Перерождение для двоих", "category": "spa"},
        {"id": 19468539, "name": "Ручной лимфодренажный массаж лица", "category": "face"},
        {"id": 19468351, "name": "Расслабляющий массаж головы", "category": "head"},
        {"id": 19468462, "name": "Пенный массаж головы", "category": "head"},
    ]

    svc_res = supabase.table("services").select("id,title,price_min").in_("id", [s["id"] for s in featured_services]).execute()
    svc_prices = {s["id"]: s["price_min"] for s in svc_res.data}

    results = []
    for svc in featured_services:
        slots_resp = await get_book_times(COMPANY_ID, token, date, svc["id"])
        slots = slots_resp.get("data", [])
        for slot in slots[:2]:
            slot_dt = datetime.fromisoformat(slot["datetime"])
            base_price = svc_prices.get(svc["id"], 5000)
            pricing = get_lovi_price(base_price, slot_dt)
            if pricing and base_price >= 3000:
                results.append({
                    "time": slot["time"],
                    "datetime": slot["datetime"],
                    "service_id": svc["id"],
                    "service_name": svc["name"],
                    "category": svc.get("category", "other"),
                    "duration_min": slot["seance_length"] // 60,
                    **pricing
                })

    results.sort(key=lambda x: x["datetime"])
    return {"date": date, "slots": results[:8]}
