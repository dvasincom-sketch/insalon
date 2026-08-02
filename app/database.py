import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

DB_BACKEND = os.getenv("DB_BACKEND", "supabase").lower()
if DB_BACKEND == "postgres":
    # синхронный шим над управляемым Postgres (тот же интерфейс, что supabase-py)
    from app.pg import supabase
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


async def save_salon(company_id: int, user_token: str, company_data: dict):
    data = {
        "company_id": company_id,
        "user_token": user_token,
        "title": company_data.get("title", ""),
        "city": company_data.get("city", ""),
        "phone": company_data.get("phone", ""),
        "is_active": True
    }
    result = supabase.table("salons").upsert(data, on_conflict="company_id").execute()
    return result.data


async def get_all_salons():
    result = supabase.table("salons").select("*").eq("is_active", True).execute()
    return result.data


async def deactivate_salon(company_id: int):
    result = supabase.table("salons").update(
        {"is_active": False}
    ).eq("company_id", company_id).execute()
    return result.data


async def save_records(records: list, company_id: int):
    if not records:
        return []

    rows = []
    for r in records:
        service = r.get("services", [])
        service_title = service[0].get("title", "") if service else ""
        service_cost = int(float(service[0].get("cost", 0))) if service else 0
        client = r.get("client") or {}

        from datetime import datetime
        rows.append({
            "id": r["id"],
            "company_id": company_id,
            "client_id": client.get("id"),
            "client_name": client.get("name", ""),
            "client_phone": client.get("phone", ""),
            "staff_name": r.get("staff", {}).get("name", ""),
            "service_title": service_title,
            "service_cost": service_cost,
            "date": r.get("date"),
            "attendance": r.get("attendance", 0),
            "online": r.get("online", False),
            "record_from": r.get("record_from", ""),
            "duration": int(r.get("seance_length", 0)),
            "synced_at": datetime.now().isoformat()
        })

    result = supabase.table("records").upsert(rows, on_conflict="id").execute()
    return result.data


async def get_records_by_company(company_id: int, limit: int = 100):
    result = supabase.table("records").select("*").eq(
        "company_id", company_id
    ).order("date", desc=True).limit(limit).execute()
    return result.data


async def save_clients(clients: list, company_id: int):
    if not clients:
        return []

    rows = []
    for c in clients:
        rows.append({
            "id": c["id"],
            "company_id": company_id,
            "name": c.get("name", ""),
            "phone": c.get("phone", ""),
            "email": c.get("email", ""),
            "success_visits": c.get("success_visits_count", 0),
            "is_new": c.get("is_new", False)
        })

    result = supabase.table("clients").upsert(rows, on_conflict="id").execute()
    return result.data

async def get_salon(company_id: int):
    result = supabase.table("salons").select("*").eq(
        "company_id", company_id
    ).execute()
    if result.data:
        return result.data[0]
    return None
async def save_staff(staff_list: list, company_id: int):
    if not staff_list:
        return []
    rows = []
    for s in staff_list:
        rows.append({
            "id": s["id"],
            "company_id": company_id,
            "name": s.get("name", ""),
            "specialization": s.get("specialization", ""),
            "position": s.get("position", {}).get("title", "") if isinstance(s.get("position"), dict) else "",
            "avatar": s.get("avatar", ""),
            "rating": float(s.get("rating", 0))
        })
    result = supabase.table("staff").upsert(rows, on_conflict="id").execute()
    return result.data

async def save_service_categories(categories_list: list, company_id: int):
    if not categories_list:
        return []
    rows = []
    for c in categories_list:
        rows.append({
            "id": c["id"],
            "company_id": company_id,
            "title": c.get("title", ""),
            "weight": c.get("weight", 0)
        })
    result = supabase.table("service_categories").upsert(rows, on_conflict="id").execute()
    return result.data

async def save_services(services_list: list, company_id: int):
    if not services_list:
        return []
    rows = []
    for s in services_list:
        staff = s.get("staff", [])
        seance_length = staff[0].get("seance_length", 0) if staff and isinstance(staff[0], dict) else 0
        rows.append({
            "id": s["id"],
            "company_id": company_id,
            "title": s.get("title", ""),
            "category_id": s.get("category_id"),
            "price_min": int(float(s.get("price_min", 0))),
            "price_max": int(float(s.get("price_max", 0))),
            "duration": int(s.get("duration") or 0),
            "seance_length": seance_length
        })
    result = supabase.table("services").upsert(rows, on_conflict="id").execute()
    return result.data

async def save_transactions(transactions_list: list, company_id: int):
    if not transactions_list:
        return []
    rows = []
    for t in transactions_list:
        client = t.get("client") or {}
        account = t.get("account") or {}
        expense = t.get("expense") or {}
        rows.append({
            "id": t["id"],
            "company_id": company_id,
            "client_id": client.get("id"),
            "client_name": client.get("name", ""),
            "amount": float(t.get("amount", 0)),
            "type_id": expense.get("type", 0),
            "type_title": expense.get("title", ""),
            "account": account.get("title", ""),
            "comment": t.get("comment", ""),
            "date": t.get("date")
        })
    result = supabase.table("transactions").upsert(rows, on_conflict="id").execute()
    return result.data
