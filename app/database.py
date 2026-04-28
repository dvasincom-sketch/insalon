import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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
            "record_from": r.get("record_from", "")
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