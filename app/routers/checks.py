from fastapi import APIRouter
from app.database import supabase
import os

router = APIRouter(prefix="/checks", tags=["Проверки данных"])

COMPANY_ID = int(os.getenv("YCLIENTS_COMPANY_ID"))


@router.get("/", summary="Все проверки", description="Запускает все проверки данных и возвращает список расхождений.")
async def run_all_checks():
    results = {}
    errors = []
    warnings = []

    # 1. Записи с нулевой ценой (не Fitmost)
    zero_cost = supabase.table("records").select(
        "date, client_name, service_title, staff_name, record_from"
    ).eq("company_id", COMPANY_ID).eq("attendance", 1).eq(
        "service_cost", 0
    ).eq("is_fitmost", False).execute()

    if zero_cost.data:
        warnings.append({
            "check": "Записи с нулевой ценой",
            "count": len(zero_cost.data),
            "description": "Визиты проведены как оплаченные но цена = 0. Возможно оплата абонементом или сертификатом.",
            "samples": zero_cost.data[:5]
        })

    # 2. Записи без клиента
    no_client = supabase.table("records").select(
        "date, service_title, staff_name"
    ).eq("company_id", COMPANY_ID).eq("attendance", 1).is_(
        "client_id", "null"
    ).eq("is_fitmost", False).execute()

    if no_client.data:
        warnings.append({
            "check": "Записи без клиента",
            "count": len(no_client.data),
            "description": "Визиты без привязки к клиенту — невозможно отследить историю.",
            "samples": no_client.data[:5]
        })

    # 3. Месяцы без аренды (начиная с июня 2025)
    rent_by_month = supabase.table("bank_transactions").select(
        "period, amount"
    ).eq("company_id", COMPANY_ID).eq("category", "salon_rent").ilike(
        "description", "%договору 18%"
    ).execute()

    rent_months = set(r["period"][:7] for r in rent_by_month.data if r.get("period"))

    from datetime import datetime, timedelta
    start = datetime(2025, 6, 1)
    end = datetime.now()
    current = start
    missing_rent = []
    while current <= end:
        month_str = current.strftime("%Y-%m")
        if month_str not in rent_months:
            missing_rent.append(month_str)
        current += timedelta(days=32)
        current = current.replace(day=1)

    if missing_rent:
        errors.append({
            "check": "Месяцы без аренды салона",
            "count": len(missing_rent),
            "description": "Не найдены платежи аренды за эти месяцы.",
            "months": missing_rent
        })

    # 4. Fitmost сверка — записи vs платежи
    fitmost_records = supabase.table("records").select(
        "date, service_cost"
    ).eq("company_id", COMPANY_ID).eq("attendance", 1).eq(
        "is_fitmost", True
    ).eq("record_from", "").execute()

    fitmost_payments = supabase.table("bank_transactions").select(
        "period, amount"
    ).eq("company_id", COMPANY_ID).ilike(
        "counterparty", "%фитмост%"
    ).eq("type", "Кредит").execute()

    from collections import defaultdict
    fitmost_by_month = defaultdict(float)
    for r in fitmost_records.data:
        month = r["date"][:7]
        fitmost_by_month[month] += float(r["service_cost"] or 0)

    payments_by_month = defaultdict(float)
    for p in fitmost_payments.data:
        period = p.get("period") or p["period"]
        month = period[:7]
        payments_by_month[month] += float(p["amount"] or 0)

    fitmost_discrepancies = []
    for month in sorted(fitmost_by_month.keys()):
        expected = round(fitmost_by_month[month] * 0.65)
        actual = round(payments_by_month.get(month, 0))
        diff = actual - expected
        if abs(diff) > 1000:
            fitmost_discrepancies.append({
                "month": month,
                "expected": expected,
                "actual": actual,
                "difference": diff
            })

    if fitmost_discrepancies:
        warnings.append({
            "check": "Расхождения Fitmost",
            "count": len(fitmost_discrepancies),
            "description": "Ожидаемые платежи от Fitmost не совпадают с фактическими.",
            "details": fitmost_discrepancies
        })

    # 5. Транзакции YCLIENTS vs записи
    from datetime import datetime
    last_month_start = datetime.now().replace(day=1) - timedelta(days=1)
    last_month_start = last_month_start.replace(day=1).strftime("%Y-%m-%d")
    last_month_end = datetime.now().replace(day=1).strftime("%Y-%m-%d")

    yclients_transactions = supabase.table("transactions").select(
        "amount"
    ).eq("company_id", COMPANY_ID).gte(
        "date", last_month_start
    ).lt("date", last_month_end).gt("amount", 0).execute()

    yclients_records = supabase.table("records").select(
        "service_cost"
    ).eq("company_id", COMPANY_ID).eq("attendance", 1).gte(
        "date", last_month_start
    ).lt("date", last_month_end).gt("service_cost", 0).execute()

    total_transactions = sum(float(t["amount"]) for t in yclients_transactions.data)
    total_records = sum(float(r["service_cost"]) for r in yclients_records.data)
    diff = abs(total_transactions - total_records)

    if diff > 5000:
        warnings.append({
            "check": "Транзакции vs Записи (прошлый месяц)",
            "description": "Сумма транзакций YCLIENTS не совпадает с суммой записей.",
            "transactions_total": round(total_transactions),
            "records_total": round(total_records),
            "difference": round(diff)
        })

    # Итог
    results["errors"] = errors
    results["warnings"] = warnings
    results["summary"] = {
        "total_errors": len(errors),
        "total_warnings": len(warnings),
        "status": "🔴 Есть ошибки" if errors else ("🟡 Есть предупреждения" if warnings else "🟢 Всё в порядке")
    }

    return results
