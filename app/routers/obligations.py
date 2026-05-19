from fastapi import APIRouter, UploadFile, File
from app.database import supabase
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import os, io, csv

router = APIRouter(prefix="/obligations", tags=["Obligations"])
COMPANY_ID = int(os.getenv("YCLIENTS_COMPANY_ID"))

class ObligationCreate(BaseModel):
    type: str = "fixed"
    project: str = "salon"
    expense_category: Optional[str] = ""
    description: str
    amount: float
    day_of_month: Optional[int] = None
    notes: Optional[str] = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class PaymentCreate(BaseModel):
    obligation_id: int
    amount: float
    payment_date: str
    notes: Optional[str] = ""
    source: str = "manual"

@router.get("")
async def get_obligations():
    result = supabase.table("obligations").select("*").eq(
        "company_id", COMPANY_ID
    ).eq("is_active", True).order("day_of_month").execute()
    return {"obligations": result.data}

@router.post("")
async def create_obligation(data: ObligationCreate):
    row = {
        "company_id": COMPANY_ID,
        "type": data.type,
        "project": data.project,
        "expense_category": data.expense_category,
        "description": data.description,
        "amount": data.amount,
        "day_of_month": data.day_of_month,
        "notes": data.notes,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "is_active": True
    }
    result = supabase.table("obligations").insert(row).execute()
    return {"status": "created", "id": result.data[0]["id"]}

@router.put("/{obligation_id}")
async def update_obligation(obligation_id: int, data: ObligationCreate):
    row = {
        "type": data.type,
        "project": data.project,
        "expense_category": data.expense_category,
        "description": data.description,
        "amount": data.amount,
        "day_of_month": data.day_of_month,
        "notes": data.notes,
        "start_date": data.start_date,
        "end_date": data.end_date,
    }
    supabase.table("obligations").update(row).eq("id", obligation_id).eq(
        "company_id", COMPANY_ID
    ).execute()
    return {"status": "updated"}

@router.delete("/{obligation_id}")
async def delete_obligation(obligation_id: int):
    supabase.table("obligations").update({"is_active": False}).eq(
        "id", obligation_id
    ).eq("company_id", COMPANY_ID).execute()
    return {"status": "deleted"}

@router.get("/payments")
async def get_payments(year: int = None, month: int = None):
    now = datetime.now()
    y = year or now.year
    m = month or now.month
    date_from = f"{y}-{m:02d}-01"
    import calendar
    last_day = calendar.monthrange(y, m)[1]
    date_to = f"{y}-{m:02d}-{last_day}"

    result = supabase.table("obligation_payments").select(
        "*, obligations(description, type, project, expense_category)"
    ).eq("company_id", COMPANY_ID).gte(
        "payment_date", date_from
    ).lte("payment_date", date_to).order("payment_date", desc=True).execute()
    return {"payments": result.data}

@router.post("/pay")
async def pay_obligation(data: PaymentCreate):
    row = {
        "company_id": COMPANY_ID,
        "obligation_id": data.obligation_id,
        "amount": data.amount,
        "payment_date": data.payment_date,
        "notes": data.notes,
        "source": data.source
    }
    result = supabase.table("obligation_payments").insert(row).execute()

    # Обновляем last_payment_date
    supabase.table("obligations").update({
        "last_payment_date": data.payment_date
    }).eq("id", data.obligation_id).execute()

    return {"status": "paid", "id": result.data[0]["id"]}

@router.delete("/payments/{payment_id}")
async def delete_payment(payment_id: int):
    supabase.table("obligation_payments").delete().eq("id", payment_id).eq(
        "company_id", COMPANY_ID
    ).execute()
    return {"status": "deleted"}

@router.get("/summary")
async def get_summary():
    """Сводка: общий долг, платежи этой недели, статус месяца"""
    from datetime import timedelta
    now = date.today()
    week_end = now + timedelta(days=7)

    obligations = supabase.table("obligations").select("*").eq(
        "company_id", COMPANY_ID
    ).eq("is_active", True).execute()

    import calendar
    m = now.month
    y = now.year
    last_day = calendar.monthrange(y, m)[1]
    date_from = f"{y}-{m:02d}-01"
    date_to = f"{y}-{m:02d}-{last_day}"

    payments = supabase.table("obligation_payments").select(
        "obligation_id, amount"
    ).eq("company_id", COMPANY_ID).gte(
        "payment_date", date_from
    ).lte("payment_date", date_to).execute()

    paid_ids = {p["obligation_id"] for p in payments.data}
    paid_amounts = {}
    for p in payments.data:
        paid_amounts[p["obligation_id"]] = paid_amounts.get(p["obligation_id"], 0) + float(p["amount"])

    total_fixed = 0
    total_variable = 0
    total_debt = 0
    upcoming_week = []
    overdue = []

    for o in obligations.data:
        amt = float(o["amount"])
        if o["type"] == "debt":
            total_debt += amt
        elif o["type"] == "fixed":
            total_fixed += amt
        else:
            total_variable += amt

        if o["day_of_month"]:
            pay_date = date(y, m, min(o["day_of_month"], last_day))
            is_paid = o["id"] in paid_ids
            if not is_paid:
                if pay_date < now:
                    overdue.append({"description": o["description"], "amount": amt, "day": o["day_of_month"]})
                elif pay_date <= week_end:
                    upcoming_week.append({"description": o["description"], "amount": amt, "day": o["day_of_month"]})

    # Динамическая ЗП из ФОТ + автосверка
    fot_salary = 0
    fot_first_half_paid = False
    fot_second_half_paid = False
    try:
        fot_data = supabase.table("payroll").select(
            "staff_name, total_accrued, total_paid, status, period_start"
        ).eq("company_id", COMPANY_ID).gte(
            "period_start", f"{now.year}-{now.month:02d}-01"
        ).execute()
        fot_salary = sum(float(p["total_accrued"] or 0) for p in fot_data.data)

        # Первая половина (1-го) — все записи period_start = 01 оплачены
        first_half = [p for p in fot_data.data if p["period_start"].endswith("-01")]
        second_half = [p for p in fot_data.data if p["period_start"].endswith("-15")]
        fot_first_half_total  = sum(float(p["total_accrued"] or 0) for p in first_half)
        fot_second_half_total = sum(float(p["total_accrued"] or 0) for p in second_half)
        if first_half and all(p["status"] == "paid" for p in first_half):
            fot_first_half_paid = True
        if second_half and all(p["status"] == "paid" for p in second_half):
            fot_second_half_paid = True
    except:
        pass

    # Автосверка с bank_transactions — ищем совпадения по сумме и месяцу
    try:
        bank_data = supabase.table("bank_transactions").select(
            "amount, description, category, date"
        ).eq("company_id", COMPANY_ID).gte(
            "date", date_from
        ).lte("date", date_to).lt("amount", 0).execute()

        bank_amounts = {}
        for b in bank_data.data:
            amt = abs(float(b["amount"]))
            key = round(amt)
            if key not in bank_amounts:
                bank_amounts[key] = []
            bank_amounts[key].append(b)

        for o in obligations.data:
            if o["id"] in paid_ids:
                continue
            if not o.get("day_of_month"):
                continue
            if o.get("expense_category") in ("salary", "internal", "personal"):
                continue
            amt_key = round(float(o["amount"]))
            # Ищем с допуском ±5₽
            found = False
            for delta in range(-5, 6):
                if amt_key + delta in bank_amounts:
                    paid_ids.add(o["id"])
                    paid_amounts[o["id"]] = float(o["amount"])
                    found = True
                    break
    except:
        pass

    # Автоматически помечаем salary-обязательства как оплаченные
    # 15-го числа → выплата за 1-14 (first_half) → paid если все first_half paid
    # 1-го числа → выплата за 15-31 прошлого месяца → paid если все second_half прошлого месяца paid
    for o in obligations.data:
        if o.get("expense_category") == "salary" and o.get("day_of_month"):
            day = o["day_of_month"]
            if day >= 14 and day <= 16 and fot_first_half_paid:
                paid_ids.add(o["id"])
            # 1-го числа — это выплата за 15-31 ТЕКУЩЕГО месяца
            # Помечаем как оплачен только если уже наступило следующее число (т.е. прошёл 1-й след. месяца)
            # Пока идёт текущий месяц — всегда "Ожидается"

    return {
        "total_fixed": total_fixed,
        "total_variable": total_variable,
        "total_debt": total_debt,
        "paid_ids": list(paid_ids),
        "paid_amounts": paid_amounts,
        "overdue": overdue,
        "upcoming_week": upcoming_week,
        "fot_salary": fot_salary,
        "fot_first_half_total": locals().get("fot_first_half_total", 0),
        "fot_second_half_total": locals().get("fot_second_half_total", 0),
        "fot_first_half_paid": fot_first_half_paid,
        "fot_second_half_paid": fot_second_half_paid
    }


@router.post("/upload-bank-csv")
async def upload_bank_csv(file: UploadFile = File(...), project: str = "salon"):
    """Загрузка банковской выписки CSV (Т-Банк ИП формат)"""
    content_bytes = await file.read()
    # Убираем BOM если есть
    text = content_bytes.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text), delimiter=';')

    rows = []
    skipped = 0
    for row in reader:
        try:
            date_str = row.get('Дата проведения', '').strip()
            if not date_str:
                continue
            # Формат DD.MM.YYYY
            d = datetime.strptime(date_str, '%d.%m.%Y').date()
            amount_str = row.get('Сумма в валюте счёта', '0').replace(',', '.').replace(' ', '')
            amount = float(amount_str)
            op_type = row.get('Тип операции (пополнение/списание)', '').strip()
            if op_type == 'Дебет':
                amount = -abs(amount)
            else:
                amount = abs(amount)

            description  = row.get('Назначение платежа', '').strip()[:500]
            counterparty = row.get('Наименование контрагента', '').strip()[:200]
            inn          = row.get('ИНН контрагента', '').strip()

            rows.append({
                "company_id":   COMPANY_ID,
                "date":         d.isoformat(),
                "type":         op_type,
                "amount":       amount,
                "description":  description,
                "counterparty": counterparty,
                "inn":          inn,
                "project":      project,
                "period":       d.replace(day=1).isoformat(),
                "category":     "uncategorized"
            })
        except Exception as e:
            skipped += 1
            continue

    if not rows:
        return {"status": "error", "message": "Нет данных для загрузки"}

    # Upsert по date+description+amount чтобы избежать дублей
    result = supabase.table("bank_transactions").upsert(
        rows, on_conflict="company_id,date,description,amount"
    ).execute()

    return {
        "status": "ok",
        "loaded": len(rows),
        "skipped": skipped,
        "project": project
    }
