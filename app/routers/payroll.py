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
    }

    if existing.data:
        record_id = existing.data[0]["id"]
        supabase.table("payroll").update(row).eq("id", record_id).execute()
        return {"status": "updated", "id": record_id}
    else:
        result = supabase.table("payroll").insert(row).execute()
        return {"status": "created", "id": result.data[0]["id"]}
