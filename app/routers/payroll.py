from fastapi import APIRouter
from app.database import supabase
from pydantic import BaseModel
from typing import Optional
import os

router = APIRouter(prefix="/payroll", tags=["Payroll"])
COMPANY_ID = int(os.getenv("YCLIENTS_COMPANY_ID"))

class PayrollUpsert(BaseModel):
    staff_name: str
    period_start: str
    period_end: str
    shifts: int = 0
    shift_pay: int = 0
    visit_pay: int = 0
    bonus_loyalty: int = 0
    bonus: int = 0
    advance_cash: int = 0
    advance_transfer: int = 0
    expenses_reimbursement: int = 0
    total_accrued: int = 0
    total_paid: int = 0
    balance: int = 0
    notes: Optional[str] = ""
    status: str = "draft"

@router.get("/period/{year}/{month}")
async def get_period_payroll(year: int, month: int):
    period_start_1 = f"{year}-{month:02d}-01"
    period_start_2 = f"{year}-{month:02d}-15"
    result = supabase.table("payroll").select("*").eq(
        "company_id", COMPANY_ID
    ).in_("period_start", [period_start_1, period_start_2]).execute()
    return {"records": result.data}

@router.get("/unclosed")
async def get_unclosed_periods():
    """Все незакрытые draft периоды за последние 3 месяца"""
    from datetime import date, timedelta
    date_from = (date.today().replace(day=1) - timedelta(days=90)).strftime("%Y-%m-%d")
    result = supabase.table("payroll").select(
        "staff_name, period_start, period_end, total_accrued, total_paid, balance, status"
    ).eq("company_id", COMPANY_ID).eq(
        "status", "draft"
    ).gt("balance", 0).gte(
        "period_start", date_from
    ).order("period_start").execute()
    
    # Группируем по периоду
    periods = {}
    for p in result.data:
        key = p["period_start"]
        if key not in periods:
            periods[key] = {"period_start": p["period_start"], "period_end": p["period_end"], "staff": []}
        periods[key]["staff"].append(p)
    
    return {"unclosed": list(periods.values())}

@router.get("/draft/{year}/{month}")
async def get_draft_payroll(year: int, month: int):
    period_start_1 = f"{year}-{month:02d}-01"
    period_start_2 = f"{year}-{month:02d}-15"
    result = supabase.table("payroll").select("*").eq(
        "company_id", COMPANY_ID
    ).eq("status", "draft").in_(
        "period_start", [period_start_1, period_start_2]
    ).execute()
    return {"drafts": result.data}

@router.post("/mark-paid")
async def mark_paid(data: dict):
    record_id = data.get("id")
    if not record_id:
        return {"error": "id required"}
    status = data.get("status", "paid")
    update_data = {"status": status}
    if status == "paid":
        update_data["total_paid"] = data.get("total_paid", 0)
        update_data["balance"] = data.get("balance", 0)
        if "advance_cash" in data:
            update_data["advance_cash"] = data["advance_cash"]
        if "advance_transfer" in data:
            update_data["advance_transfer"] = data["advance_transfer"]
    supabase.table("payroll").update(update_data).eq("id", record_id).execute()
    return {"status": "ok", "id": record_id}

@router.get("/advances/{year}/{month}/{day}")
async def get_advances(year: int, month: int, day: int):
    """Получить выплаты мастерам из personal_transactions по алиасам"""
    from datetime import date as dt
    import calendar
    
    period_start = f"{year}-{month:02d}-{day:02d}"
    is_second_half = day >= 15
    if is_second_half:
        last_day = calendar.monthrange(year, month)[1]
        period_end = f"{year}-{month:02d}-{last_day:02d}"
    else:
        period_end = f"{year}-{month:02d}-14"
    
    # Получаем алиасы
    aliases = supabase.table("staff_payment_aliases").select("*").eq(
        "company_id", COMPANY_ID
    ).execute()
    
    # Получаем транзакции за период
    transactions = supabase.table("personal_transactions").select(
        "date, amount, description"
    ).eq("company_id", COMPANY_ID).eq(
        "expense_category", "salary"
    ).gte("date", period_start).lte("date", period_end).lt("amount", 0).execute()
    
    # Маппим по алиасам
    result = {}
    for alias_row in aliases.data:
        staff = alias_row["staff_name"]
        alias = alias_row["alias"]
        payments = [
            {"date": t["date"], "amount": abs(float(t["amount"]))}
            for t in transactions.data
            if t["description"] == alias
        ]
        if payments:
            result[staff] = payments
    
    return {"advances": result, "period_start": period_start, "period_end": period_end}

class ShiftAdd(BaseModel):
    date: str
    staff_name: str
    shift_pay: int = 5000
    is_visit_only: bool = False
    is_double_shift: bool = False

@router.post("/shifts/add")
async def add_shift(data: ShiftAdd):
    """Добавить смену или выход под запись в расписание"""
    # Проверяем дубль
    # Для выходов под запись (is_visit_only=True) допускаем несколько записей
    # одного мастера в день — каждая парная программа = отдельный выход
    if not data.is_visit_only:
        existing = supabase.table("shifts").select("id").eq(
            "company_id", COMPANY_ID
        ).eq("date", data.date).eq("staff_name", data.staff_name).eq(
            "is_visit_only", False
        ).execute()
        if existing.data:
            record_id = existing.data[0]["id"]
            if data.shift_pay > 0:
                supabase.table("shifts").update({"shift_pay": data.shift_pay}).eq("id", record_id).execute()
            return {"status": "exists", "id": record_id}

    result = supabase.table("shifts").insert({
        "company_id": COMPANY_ID,
        "date": data.date,
        "staff_name": data.staff_name,
        "shift_pay": data.shift_pay,
        "is_visit_only": data.is_visit_only,
        "is_double_shift": data.is_double_shift
    }).execute()
    return {"status": "created", "id": result.data[0]["id"]}

@router.delete("/shifts/{shift_id}")
async def delete_shift(shift_id: int):
    """Удалить смену из расписания"""
    supabase.table("shifts").delete().eq("id", shift_id).eq(
        "company_id", COMPANY_ID
    ).execute()
    return {"status": "deleted", "id": shift_id}

@router.get("/staff/list")
async def get_staff_list():
    """Список активных сотрудников"""
    result = supabase.table("staff").select("name").eq(
        "company_id", COMPANY_ID
    ).execute()
    names = sorted(list(set([r["name"] for r in result.data if r.get("name")])))
    return {"staff": names}

@router.post("/upsert")
async def upsert_payroll(data: PayrollUpsert):
    # Проверяем есть ли уже запись за этот период
    existing = supabase.table("payroll").select("id").eq(
        "company_id", COMPANY_ID
    ).eq("staff_name", data.staff_name).eq(
        "period_start", data.period_start
    ).execute()

    row = {
        "company_id": COMPANY_ID,
        "staff_name": data.staff_name,
        "period_start": data.period_start,
        "period_end": data.period_end,
        "shifts": data.shifts,
        "shift_pay": data.shift_pay,
        "visit_pay": data.visit_pay,
        "bonus_loyalty": data.bonus_loyalty,
        "bonus": data.bonus,
        "advance_cash": data.advance_cash,
        "advance_transfer": data.advance_transfer,
        "expenses_reimbursement": data.expenses_reimbursement,
        "total_accrued": data.total_accrued,
        "total_paid": data.total_paid,
        "balance": data.balance,
        "notes": data.notes,
        "status": data.status,
    }

    if existing.data:
        record_id = existing.data[0]["id"]
        supabase.table("payroll").update(row).eq("id", record_id).execute()
        return {"status": "updated", "id": record_id}
    else:
        result = supabase.table("payroll").insert(row).execute()
        return {"status": "created", "id": result.data[0]["id"]}
