from fastapi import APIRouter
from app.analytics import (
    get_revenue_by_weeks,
    get_new_vs_returning,
    get_churn_risk,
    get_top_services,
    get_summary
)
from collections import defaultdict
import os
from fastapi import Body
from typing import Optional
import calendar as cal_module

router = APIRouter(prefix="/analytics", tags=["Аналитика"])

COMPANY_ID = int(os.getenv("YCLIENTS_COMPANY_ID"))


def fetch_all(supabase, query_fn):
    """Получить все записи с пагинацией"""
    all_data = []
    page_size = 1000
    offset = 0
    while True:
        result = query_fn().range(offset, offset + page_size - 1).execute()
        all_data.extend(result.data)
        if len(result.data) < page_size:
            break
        offset += page_size
    return all_data


@router.get("/summary", summary="Сводка за месяц")
async def analytics_summary():
    try:
        return await get_summary(COMPANY_ID)
    except Exception as e:
        return {"error": str(e)}


@router.get("/revenue", summary="Выручка по неделям")
async def analytics_revenue(weeks: int = 12):
    try:
        return await get_revenue_by_weeks(COMPANY_ID, weeks)
    except Exception as e:
        return {"error": str(e)}


@router.get("/clients", summary="Новые vs повторные клиенты")
async def analytics_clients(weeks: int = 12):
    try:
        return await get_new_vs_returning(COMPANY_ID, weeks)
    except Exception as e:
        return {"error": str(e)}


@router.get("/churn", summary="Риск оттока клиентов")
async def analytics_churn(days: int = 45):
    try:
        return await get_churn_risk(COMPANY_ID, days)
    except Exception as e:
        return {"error": str(e)}


@router.get("/services", summary="Топ услуги по выручке")
async def analytics_services():
    try:
        return await get_top_services(COMPANY_ID)
    except Exception as e:
        return {"error": str(e)}


# Проекты для консолидированного отчёта (всё кроме internal/personal/unknown)
CONSOLIDATED_EXCLUDE = ["internal", "personal", "unknown", "transfer_in"]

# Человеческие названия проектов
PROJECT_LABELS = {
    "salon": "Салон (HeadSPA)",
    "podcast": "Подкаст (NOISHA)",
    "book": "Книга",
    "consulting": "Консалтинг",
    "startup": "Стартап",
    "enzyme": "Enzyme",
    "consolidated": "Консолидированный",
}


def _build_pl_months(monthly: dict) -> list:
    """Собирает итоговый список месяцев из monthly-словаря"""
    result = []
    for month in sorted(monthly.keys()):
        d = monthly[month]
        total_revenue = (
            d["revenue_services"] + d["revenue_certificates"] +
            d["revenue_abonements"] + d["revenue_fitmost"] + d["revenue_other"]
        )
        total_expenses = sum([
            d["salary"], d["rent"], d["materials"], d["cosmetics"], d["marketing"],
            d["credit_card"], d["it"], d["equipment"], d["transport"],
            d["bank_fees"], d["other"]
        ])
        profit = total_revenue - total_expenses
        result.append({
            "month": month,
            "revenue_services": round(d["revenue_services"]),
            "revenue_certificates": round(d["revenue_certificates"]),
            "revenue_abonements": round(d["revenue_abonements"]),
            "revenue_fitmost": round(d["revenue_fitmost"]),
            "revenue_other": round(d["revenue_other"]),
            "total_revenue": round(total_revenue),
            "salary": round(d["salary"]),
            "rent": round(d["rent"]),
            "materials": round(d["materials"]),
            "cosmetics": round(d["cosmetics"]),
            "marketing": round(d["marketing"]),
            "bank_fees": round(d["bank_fees"]),
            "other": round(d["credit_card"] + d["it"] + d["equipment"] + d["transport"] + d["other"]),
            "total_expenses": round(total_expenses),
            "profit": round(profit)
        })
    return result


def _empty_month():
    return {
        "revenue_services": 0, "revenue_certificates": 0,
        "revenue_abonements": 0, "revenue_fitmost": 0, "revenue_other": 0,
        "salary": 0, "rent": 0, "materials": 0,
        "marketing": 0, "credit_card": 0, "it": 0,
        "equipment": 0, "transport": 0,
        "bank_fees": 0, "cosmetics": 0, "other": 0
    }


@router.get("/pl", summary="P&L по месяцам")
async def analytics_pl(project: str = "salon"):
    try:
        from app.database import supabase

        monthly = defaultdict(_empty_month)

        # ── САЛОН ──────────────────────────────────────────────────────────────
        if project in ("salon", "consolidated"):
            # Выручка из YCLIENTS
            transactions_data = fetch_all(supabase, lambda: supabase.table("transactions").select("date, amount, type_title").eq("company_id", COMPANY_ID).gt("amount", 0))
            for t in transactions_data:
                month = t["date"][:7]
                amount = float(t["amount"] or 0)
                type_title = t.get("type_title", "") or ""
                if "услуг" in type_title.lower():
                    monthly[month]["revenue_services"] += amount
                elif "сертификат" in type_title.lower():
                    monthly[month]["revenue_certificates"] += amount
                elif "абонемент" in type_title.lower():
                    monthly[month]["revenue_abonements"] += amount

            # Fitmost
            fitmost_data = fetch_all(supabase, lambda: supabase.table("bank_transactions").select("period, date, amount").eq("company_id", COMPANY_ID).eq("type", "Кредит").ilike("counterparty", "%фитмост%"))
            for f in fitmost_data:
                period = f.get("period") or f["date"]
                month = period[:7]
                monthly[month]["revenue_fitmost"] += float(f["amount"] or 0)

            # ФОТ из payroll
            payroll_data = fetch_all(supabase, lambda: supabase.table("payroll").select("period_start, total_accrued").eq("company_id", COMPANY_ID))
            for p in payroll_data:
                month = p["period_start"][:7]
                monthly[month]["salary"] += float(p["total_accrued"] or 0)

            # Банковские комиссии
            bank_fees_data = fetch_all(supabase, lambda: supabase.table("bank_transactions").select("date, amount").eq("company_id", COMPANY_ID).eq("category", "bank_fee").lt("amount", 0))
            for b in bank_fees_data:
                month = b["date"][:7]
                monthly[month]["bank_fees"] += abs(float(b["amount"] or 0))

            # Косметика
            cosmetics_data = fetch_all(supabase, lambda: supabase.table("bank_transactions").select("date, amount").eq("company_id", COMPANY_ID).eq("category", "cosmetics").lt("amount", 0))
            for c in cosmetics_data:
                month = c["date"][:7]
                monthly[month]["cosmetics"] += abs(float(c["amount"] or 0))

            # Аренда
            salon_rent_data = fetch_all(supabase, lambda: supabase.table("bank_transactions").select("period, date, amount, description").eq("company_id", COMPANY_ID).eq("category", "salon_rent").lt("amount", 0))
            for r in salon_rent_data:
                period = r.get("period") or r["date"]
                month = period[:7]
                amount = abs(float(r["amount"] or 0))
                if "рекламного" in (r.get("description") or "").lower():
                    monthly[month]["marketing"] += amount
                else:
                    monthly[month]["rent"] += amount

            # Расходы салона из personal_transactions
            salon_expenses = fetch_all(supabase, lambda: supabase.table("personal_transactions").select("date, amount, expense_category").eq("company_id", COMPANY_ID).eq("project", "salon").lt("amount", 0))
            known_cats = ["rent", "materials", "marketing", "credit_card", "it", "equipment", "transport"]
            for e in salon_expenses:
                month = e["date"][:7]
                cat = e["expense_category"]
                amount = abs(float(e["amount"] or 0))
                if cat == "salary":
                    pass  # берём из payroll
                elif cat in known_cats:
                    monthly[month][cat] += amount
                else:
                    monthly[month]["other"] += amount

        # ── ДРУГИЕ ПРОЕКТЫ (podcast / book / consulting / startup / enzyme) ────
        if project not in ("salon", "consolidated"):
            # Доходы проекта из personal_transactions (положительные)
            income_data = fetch_all(supabase, lambda: supabase.table("personal_transactions").select("date, amount, expense_category").eq("company_id", COMPANY_ID).eq("project", project).gt("amount", 0))
            for i in income_data:
                month = i["date"][:7]
                monthly[month]["revenue_other"] += float(i["amount"] or 0)

            # Также доходы из bank_transactions по проекту
            bank_income = fetch_all(supabase, lambda: supabase.table("bank_transactions").select("date, amount").eq("company_id", COMPANY_ID).eq("project", project).gt("amount", 0))
            for b in bank_income:
                month = b["date"][:7]
                monthly[month]["revenue_other"] += float(b["amount"] or 0)

        if project != "salon":
            # Расходы проекта из personal_transactions
            proj_filter = project if project != "consolidated" else None
            known_cats = ["rent", "materials", "marketing", "credit_card", "it", "equipment", "transport"]

            if proj_filter:
                expenses_data = fetch_all(supabase, lambda: supabase.table("personal_transactions").select("date, amount, expense_category, project").eq("company_id", COMPANY_ID).eq("project", proj_filter).lt("amount", 0))
            else:
                # consolidated — все кроме internal/personal/unknown
                expenses_data = fetch_all(supabase, lambda: supabase.table("personal_transactions").select("date, amount, expense_category, project").eq("company_id", COMPANY_ID).lt("amount", 0).not_.in_("project", CONSOLIDATED_EXCLUDE).not_.in_("expense_category", ["internal", "transfer_in"]))

            for e in expenses_data:
                if project == "consolidated" and e.get("project") == "salon":
                    continue  # салонные расходы уже добавлены выше
                month = e["date"][:7]
                cat = e["expense_category"]
                amount = abs(float(e["amount"] or 0))
                if cat == "salary":
                    pass
                elif cat in known_cats:
                    monthly[month][cat] += amount
                else:
                    monthly[month]["other"] += amount

            # Расходы из bank_transactions по проекту
            if proj_filter:
                bank_exp = fetch_all(supabase, lambda: supabase.table("bank_transactions").select("date, amount, category").eq("company_id", COMPANY_ID).eq("project", proj_filter).lt("amount", 0))
            else:
                bank_exp = fetch_all(supabase, lambda: supabase.table("bank_transactions").select("date, amount, category").eq("company_id", COMPANY_ID).lt("amount", 0).not_.in_("project", CONSOLIDATED_EXCLUDE))

            for b in bank_exp:
                if project == "consolidated" and b.get("category") in ("bank_fee", "cosmetics", "salon_rent"):
                    continue  # уже добавлены выше
                month = b["date"][:7]
                monthly[month]["other"] += abs(float(b["amount"] or 0))

        return {
            "project": project,
            "project_label": PROJECT_LABELS.get(project, project),
            "months": _build_pl_months(monthly)
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@router.get("/obligations/{year}/{month}", summary="Обязательства на месяц", description="Список всех ожидаемых платежей на указанный месяц.")
async def obligations_for_month(year: int, month: int):
    try:
        from app.database import supabase
        from datetime import date
        
        target_date = date(year, month, 1)
        
        result = supabase.table("obligations").select("*").eq(
            "company_id", COMPANY_ID
        ).eq("is_active", True).execute()
        
        obligations = []
        for o in result.data:
            start = date.fromisoformat(o["start_date"]) if o.get("start_date") else None
            end = date.fromisoformat(o["end_date"]) if o.get("end_date") else None
            
            # Проверяем входит ли в период
            if start and start > target_date:
                continue
            if end and end < target_date:
                continue
                
            obligations.append({
                "description": o["description"],
                "amount": o["amount"],
                "day_of_month": o["day_of_month"],
                "type": o["type"],
                "project": o["project"],
                "expense_category": o["expense_category"],
                "notes": o["notes"]
            })
        
        # Сортируем по дню месяца
        obligations.sort(key=lambda x: x["day_of_month"] or 99)
        
        total_fixed = sum(o["amount"] for o in obligations if o["type"] == "periodic_fixed")
        total_variable = sum(o["amount"] for o in obligations if o["type"] == "periodic_variable")
        total_debt = sum(o["amount"] for o in obligations if o["type"] == "debt")
        
        salon_total = sum(o["amount"] for o in obligations if o["project"] == "salon")
        personal_total = sum(o["amount"] for o in obligations if o["project"] == "personal")
        
        return {
            "month": f"{year}-{month:02d}",
            "obligations": obligations,
            "summary": {
                "fixed": round(total_fixed),
                "variable": round(total_variable),
                "debt": round(total_debt),
                "salon": round(salon_total),
                "personal": round(personal_total),
                "total": round(total_fixed + total_variable + total_debt)
            }
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@router.get("/revenue/detail", summary="Детализация выручки за период")
async def revenue_detail(date_from: str, date_to: str):
    try:
        from app.database import supabase
        
        data = supabase.table("transactions").select(
            "date, amount, type_title, client_name, account"
        ).eq("company_id", COMPANY_ID).gte(
            "date", date_from
        ).lt("date", date_to).gt("amount", 0).order("date").execute()
        
        total = sum(float(t["amount"]) for t in data.data)
        
        return {
            "date_from": date_from,
            "date_to": date_to,
            "total": round(total),
            "count": len(data.data),
            "transactions": data.data
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@router.get("/cmph", summary="CM per Labor Hour — North Star Metric")
async def get_cmph():
    try:
        from app.database import supabase
        from datetime import datetime, timedelta

        now = datetime.now()
        date_from = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        date_to = now.strftime("%Y-%m-%d")

        # Выручка за 30 дней
        transactions = supabase.table("transactions").select(
            "amount"
        ).eq("company_id", COMPANY_ID).gte("date", date_from).lt(
            "date", date_to
        ).gt("amount", 0).execute()

        revenue = sum(float(t["amount"]) for t in transactions.data)

        # Реальные часы из records (duration в секундах)
        records = supabase.table("records").select(
            "duration, service_cost"
        ).eq("company_id", COMPANY_ID).gte("date", date_from).lt(
            "date", date_to
        ).eq("attendance", 1).gt("duration", 0).execute()

        total_seconds = sum(r["duration"] or 0 for r in records.data)
        labor_hours = round(total_seconds / 3600, 1)

        # Переменные расходы из bank + personal за 30 дней
        bank_var = supabase.table("bank_transactions").select(
            "amount"
        ).eq("company_id", COMPANY_ID).eq("project", "salon").gte(
            "date", date_from
        ).lt("date", date_to).in_(
            "category", ["cosmetics", "materials", "marketing", "bank_fee"]
        ).lt("amount", 0).execute()

        personal_var = supabase.table("personal_transactions").select(
            "amount"
        ).eq("company_id", COMPANY_ID).eq("project", "salon").gte(
            "date", date_from
        ).lt("date", date_to).in_(
            "expense_category", ["materials", "marketing", "cosmetics"]
        ).lt("amount", 0).execute()

        variable_costs = sum(abs(float(t["amount"])) for t in bank_var.data)
        variable_costs += sum(abs(float(t["amount"])) for t in personal_var.data)

        # Зарплата за 30 дней
        salary_bank = supabase.table("bank_transactions").select(
            "amount"
        ).eq("company_id", COMPANY_ID).eq("project", "salon").gte(
            "date", date_from
        ).lt("date", date_to).eq("category", "salary").lt("amount", 0).execute()

        salary_personal = supabase.table("personal_transactions").select(
            "amount"
        ).eq("company_id", COMPANY_ID).eq("project", "salon").gte(
            "date", date_from
        ).lt("date", date_to).eq("expense_category", "salary").lt("amount", 0).execute()

        salary = sum(abs(float(t["amount"])) for t in salary_bank.data)
        salary += sum(abs(float(t["amount"])) for t in salary_personal.data)

        # CM = Выручка - Переменные расходы - Зарплата
        cm = revenue - variable_costs - salary
        cmph = round(cm / labor_hours) if labor_hours > 0 else 0

        return {
            "revenue": round(revenue),
            "variable_costs": round(variable_costs),
            "salary": round(salary),
            "cm": round(cm),
            "labor_hours": labor_hours,
            "cmph": cmph,
            "visits_with_duration": len(records.data),
            "period_days": 30
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@router.get("/staff/monthly", summary="Динамика метрик по месяцам")
async def staff_monthly(months: int = 6):
    try:
        from app.database import supabase
        from datetime import datetime, timedelta
        from collections import defaultdict
        import calendar

        result = []
        now = datetime.now()

        for i in range(months - 1, -1, -1):
            # Определяем период
            d = datetime(now.year, now.month, 1) - timedelta(days=1) if i == 0 else None
            yr = now.year
            mo = now.month - i
            while mo <= 0:
                mo += 12
                yr -= 1

            date_from = f"{yr}-{mo:02d}-01"
            last_day = calendar.monthrange(yr, mo)[1]
            # Для текущего месяца берём до сегодня
            if yr == now.year and mo == now.month:
                date_to = now.strftime("%Y-%m-%d")
            else:
                date_to = f"{yr}-{mo:02d}-{last_day}"

            month_label = datetime(yr, mo, 1).strftime("%b %Y")

            # Records
            records = supabase.table("records").select(
                "date, staff_name, service_cost, is_fitmost, duration, service_title"
            ).eq("company_id", COMPANY_ID).eq("attendance", 1).eq(
                "is_fitmost", False
            ).gte("date", date_from).lte("date", date_to).execute()

            # Transactions
            transactions = supabase.table("transactions").select(
                "date, amount"
            ).eq("company_id", COMPANY_ID).gte("date", date_from).lte(
                "date", date_to
            ).gt("amount", 0).ilike("type_title", "%услуг%").execute()

            # Shifts
            shifts_data = supabase.table("shifts").select(
                "date, staff_name"
            ).eq("company_id", COMPANY_ID).gte("date", date_from).lte("date", date_to).execute()

            shifts_by_day = defaultdict(set)
            for s in shifts_data.data:
                shifts_by_day[s["date"]].add(s["staff_name"])

            revenue_by_day = defaultdict(float)
            for t in transactions.data:
                revenue_by_day[t["date"][:10]] += float(t["amount"] or 0)

            # Агрегируем по дням
            daily = defaultdict(lambda: {"revenue": 0, "staff": ""})
            for r in records.data:
                day = r["date"][:10]
                staff = r["staff_name"]
                key = f"{day}|{staff}"
                daily[key]["staff"] = staff
                daily[key]["day"] = day

            SHIFT_PAY = 5000
            total_revenue = 0
            total_shifts = 0
            profitable = 0

            for key, d in daily.items():
                day = d["day"]
                staff_count = len(shifts_by_day.get(day, set()))
                rev = revenue_by_day[day] / 2 if staff_count >= 2 else revenue_by_day[day]
                d["revenue"] = rev
                total_revenue += rev
                total_shifts += 1
                if rev >= SHIFT_PAY * 2:
                    profitable += 1

            avg_revenue = round(total_revenue / total_shifts) if total_shifts else 0
            coefficient = round(avg_revenue / SHIFT_PAY, 1) if avg_revenue else 0
            salary_pct = round(SHIFT_PAY / avg_revenue * 100) if avg_revenue else 0
            profitable_pct = round(profitable / total_shifts * 100) if total_shifts else 0

            result.append({
                "month": month_label,
                "period": f"{yr}-{mo:02d}",
                "coefficient": coefficient,
                "salary_pct": salary_pct,
                "profitable_pct": profitable_pct,
                "avg_revenue": avg_revenue,
                "shifts": total_shifts,
                "is_current": yr == now.year and mo == now.month
            })

        return {"months": result}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@router.get("/staff/daily", summary="Эффективность мастеров по дням")
async def staff_daily(days: int = 30, date_from: str = None, date_to: str = None):
    try:
        from app.database import supabase
        from datetime import datetime, timedelta
        from collections import defaultdict

        if not date_from:
            date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")

        # Записи для нагрузки и длительности
        records = supabase.table("records").select(
            "date, staff_name, service_cost, is_fitmost, duration, client_name, service_title"
        ).eq("company_id", COMPANY_ID).eq(
            "attendance", 1
        ).eq("is_fitmost", False).gte("date", date_from).lte("date", date_to).execute()

        # Прайс услуг со скидкой абонемента 30% (5 сеансов)
        services_data = supabase.table("services").select(
            "title, price_min"
        ).eq("company_id", COMPANY_ID).execute()
        ABONEMENT_DISCOUNT = 0.7
        price_by_title = {
            s["title"]: round(float(s["price_min"] or 0) * ABONEMENT_DISCOUNT)
            for s in services_data.data
        }

        # Транзакции для реальной выручки (только оказание услуг, не сертификаты)
        transactions = supabase.table("transactions").select(
            "date, amount, account, type_title, client_name"
        ).eq("company_id", COMPANY_ID).gte(
            "date", date_from
        ).lte("date", date_to).gt("amount", 0).ilike("type_title", "%услуг%").execute()

        # Выручка по дням из транзакций (только услуги)
        revenue_by_day = defaultdict(float)
        cash_by_day = defaultdict(float)
        for t in transactions.data:
            day = t["date"][:10]
            amount = float(t["amount"] or 0)
            revenue_by_day[day] += amount
            if t.get("account") == "Основная касса":
                cash_by_day[day] += amount

        daily = defaultdict(lambda: {
            "revenue": 0, "records": 0, "zero_cost_records": 0,
            "abonement_revenue": 0,
            "duration_seconds": 0, "day": "", "staff": ""
        })
        for r in records.data:
            day = r["date"][:10]
            staff = r["staff_name"]
            key = f"{day}|{staff}"
            cost = float(r["service_cost"] or 0)
            daily[key]["records"] += 1
            daily[key]["duration_seconds"] += int(r["duration"] or 0)
            daily[key]["day"] = day
            daily[key]["staff"] = staff
            if cost == 0:
                daily[key]["zero_cost_records"] += 1
                # Берём полную цену из прайса
                full_price = price_by_title.get(r.get("service_title", ""), 0)
                daily[key]["abonement_revenue"] = daily[key].get("abonement_revenue", 0) + full_price

        # Присваиваем выручку из транзакций по дням
        # Если в день один мастер — вся выручка его
        # Если два мастера — делим пропорционально записям
                # Берём количество мастеров из таблицы shifts
        shifts_data = supabase.table("shifts").select(
            "date, staff_name, is_double_shift"
        ).eq("company_id", COMPANY_ID).gte("date", date_from).lte("date", date_to).execute()

        from collections import defaultdict as dd2
        shifts_by_day = dd2(set)
        is_double_by_day = {}
        for s in shifts_data.data:
            day = s["date"]
            shifts_by_day[day].add(s["staff_name"])
            if s.get("is_double_shift"):
                is_double_by_day[day] = True

        for key, d in daily.items():
            day = d["day"]
            staff_count = len(shifts_by_day.get(day, set()))
            is_double = is_double_by_day.get(day, False)

            if staff_count >= 2 or is_double:
                d["revenue"] = revenue_by_day[day] / 2
                d["is_weekend_double"] = True
                d["note"] = "Двойная смена: выручка ÷ 2"
            else:
                d["revenue"] = revenue_by_day[day]
                d["is_weekend_double"] = False
                d["note"] = ""

        SHIFT_PAY = 5000
        result = []
        for key, d in sorted(daily.items(), reverse=True):
            revenue = d["revenue"]
            duration_hours = round(d["duration_seconds"] / 3600, 1)
            coefficient = round(revenue / SHIFT_PAY, 1) if revenue > 0 else 0
            salary_pct = round(SHIFT_PAY / revenue * 100, 1) if revenue > 0 else 0
            abonement_revenue = d.get("abonement_revenue", 0)
            total_revenue_for_master = revenue + abonement_revenue
            coefficient_full = round(total_revenue_for_master / SHIFT_PAY, 1) if total_revenue_for_master > 0 else 0
            salary_pct_full = round(SHIFT_PAY / total_revenue_for_master * 100, 1) if total_revenue_for_master > 0 else 0

            result.append({
                "day": d["day"],
                "staff": d["staff"],
                "revenue": round(revenue),
                "abonement_revenue": round(abonement_revenue),
                "total_revenue": round(total_revenue_for_master),
                "records": d["records"],
                "zero_cost_records": d["zero_cost_records"],
                "duration_hours": duration_hours,
                "shift_pay": SHIFT_PAY,
                "coefficient": coefficient_full,
                "salary_pct": salary_pct_full,
                "is_profitable": coefficient_full >= 2.0
            })

        return {"days": result, "threshold": 2.0}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@router.get("/payroll", summary="Ведомость оплаты труда")
async def get_payroll(months: int = 3):
    try:
        from app.database import supabase
        from datetime import datetime, timedelta

        date_from = (datetime.now() - timedelta(days=months*30)).strftime("%Y-%m-%d")

        data = supabase.table("payroll").select("*").eq(
            "company_id", COMPANY_ID
        ).gte("period_start", date_from).eq("status", "paid").order("period_start", desc=True).execute()

        return {"payroll": data.data}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@router.get("/shifts/{year}/{month}", summary="Расписание смен на месяц")
async def get_shifts(year: int, month: int):
    try:
        from app.database import supabase
        import calendar

        last_day = calendar.monthrange(year, month)[1]
        date_from = f"{year}-{month:02d}-01"
        date_to = f"{year}-{month:02d}-{last_day}"

        # Основные смены (не выходы под запись)
        shifts = supabase.table("shifts").select("*").eq(
            "company_id", COMPANY_ID
        ).gte("date", date_from).lte("date", date_to).eq(
            "is_visit_only", False
        ).order("date").execute()

        # Выходы под запись отдельно
        visits = supabase.table("shifts").select("*").eq(
            "company_id", COMPANY_ID
        ).gte("date", date_from).lte("date", date_to).eq(
            "is_visit_only", True
        ).order("date").execute()

        return {"year": year, "month": month, "shifts": shifts.data, "visits": visits.data}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@router.get("/payroll/verify/{year}/{month}", summary="Сверка оплаты труда")
async def verify_payroll(year: int, month: int):
    try:
        from app.database import supabase
        from collections import defaultdict

        date_from = f"{year}-{month:02d}-01"
        # Берём +5 дней следующего месяца (выплаты могут быть 1-5 числа)
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        date_to = f"{next_year}-{next_month:02d}-05"

        # Данные из payroll
        payroll = supabase.table("payroll").select("*").eq(
            "company_id", COMPANY_ID
        ).gte("period_start", date_from).lte("period_start", f"{year}-{month:02d}-{last_day}").execute()

        # Реальные выплаты из personal_transactions
        # Исключаем 1-е число текущего месяца (это выплата за предыдущий месяц)
        pay_from = f"{year}-{month:02d}-02"  # с 2-го числа
        payments = supabase.table("personal_transactions").select(
            "date, amount, description"
        ).eq("company_id", COMPANY_ID).eq(
            "expense_category", "salary"
        ).gte("date", pay_from).lte("date", date_to).lt("amount", 0).execute()

        # Маппинг имён из транзакций → имена в payroll
        NAME_MAP = {
            'Александра Т.': 'Александра',
            'Светлана Б.': 'Светлана',
            'Екатерина Б.': 'Екатерина',
            'Анастасия К.': 'Анастасия',
            'Марина Ц.': 'Марина',
        }

        # Группируем реальные выплаты по сотруднику
        actual_by_staff = defaultdict(float)
        for p in payments.data:
            name = NAME_MAP.get(p["description"])
            if name:
                actual_by_staff[name] += abs(float(p["amount"]))

        # Группируем payroll по сотруднику
        # Итоговый баланс = сумма всех балансов (включая отрицательные которые зачтены)
        # Но для сверки выплат берём только финальный остаток последнего периода
        from collections import defaultdict as dd3
        periods_by_staff = dd3(list)
        for p in payroll.data:
            periods_by_staff[p["staff_name"]].append(p)

        expected_by_staff = defaultdict(lambda: {"accrued": 0, "paid_advance": 0, "balance": 0})
        for name, periods in periods_by_staff.items():
            periods_sorted = sorted(periods, key=lambda x: x["period_start"])
            total_accrued = sum(p["total_accrued"] for p in periods_sorted)
            total_advance = sum(p["advance_cash"] for p in periods_sorted)
            # Суммируем только положительные балансы каждого периода
            # Отрицательный баланс = переплата аванса, которая либо прощается либо
            # зачитывается в следующем периоде (уже отражено в advance следующего периода)
            positive_balance = sum(p["balance"] for p in periods_sorted if p["balance"] > 0)
            expected_by_staff[name]["accrued"] = total_accrued
            expected_by_staff[name]["paid_advance"] = total_advance
            expected_by_staff[name]["balance"] = positive_balance

        # Сверка
        result = []
        all_staff = set(list(actual_by_staff.keys()) + list(expected_by_staff.keys()))
        for name in sorted(all_staff):
            expected = expected_by_staff[name]
            actual_final = actual_by_staff.get(name, 0)
            expected_final = expected["balance"]
            diff = actual_final - expected_final
            result.append({
                "staff": name,
                "accrued": round(expected["accrued"]),
                "advance_cash": round(expected["paid_advance"]),
                "expected_final": round(expected_final),
                "actual_final": round(actual_final),
                "difference": round(diff),
                "status": "✅" if abs(diff) < 100 else ("⚠️ переплата" if diff > 0 else "⚠️ недоплата")
            })

        return {"month": f"{year}-{month:02d}", "verification": result}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}

@router.get("/couple-programs/{year}/{month}")
async def get_couple_programs(year: int, month: int):
    from datetime import date
    date_from = f"{year}-{month:02d}-01"
    last_day = (date(year, month % 12 + 1, 1) if month < 12 else date(year + 1, 1, 1)).replace(day=1)
    import datetime
    date_to = (last_day - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    from app.database import supabase
    result = supabase.table("records")\
        .select("date, service_title, staff_name, client_name, duration, service_cost, attendance")\
        .ilike("service_title", "%для двоих%")\
        .gte("date", date_from)\
        .lte("date", date_to + " 23:59:59")\
        .neq("attendance", -1)\
        .execute()

    services = supabase.table("services")\
        .select("title, price_min")\
        .execute()
    price_map = {s["title"]: s["price_min"] for s in services.data if s["price_min"]}

    def calc_visit_pay(duration):
        if duration is None: return 0
        if duration < 6300: return 1500
        if duration <= 8400: return 2000
        if duration <= 10800: return 3000
        return 3500

    by_day = {}
    for r in result.data:
        price_min = price_map.get(r["service_title"], 0)
        service_cost = r.get("service_cost") or 0
        from datetime import date as dt
        record_date = r["date"][:10]
        is_future = record_date >= dt.today().strftime("%Y-%m-%d")
        # Пропускаем только прошедшие записи с низкой стоимостью (абонементы)
        if not is_future and price_min > 0 and service_cost < price_min * 0.5:
            continue
        day = int(r["date"].split("-")[2][:2])
        if day not in by_day:
            by_day[day] = []
        by_day[day].append({
            "service_title": r["service_title"],
            "staff_name": r["staff_name"],
            "client_name": r["client_name"],
            "time": r["date"][11:16],
            "duration_min": round((r["duration"] or 0) / 60),
            "visit_pay": calc_visit_pay(r["duration"])
        })

    return {"couple_days": by_day}

@router.get("/visit-records/{year}/{month}")
async def get_visit_records(year: int, month: int):
    from app.database import supabase
    import datetime
    date_from = f"{year}-{month:02d}-01"
    last_day = (datetime.date(year, month % 12 + 1, 1) if month < 12 else datetime.date(year + 1, 1, 1)) - datetime.timedelta(days=1)
    date_to = last_day.strftime("%Y-%m-%d")

    result = supabase.table("visit_records")\
        .select("date, staff_name, visit_pay, service_title, notes")\
        .gte("date", date_from)\
        .lte("date", date_to)\
        .execute()

    by_day = {}
    for r in result.data:
        day = int(r["date"].split("-")[2])
        if day not in by_day:
            by_day[day] = []
        by_day[day].append({
            "staff_name": r["staff_name"],
            "visit_pay": r["visit_pay"],
            "service_title": r["service_title"],
            "notes": r["notes"]
        })

    return {"visit_days": by_day}

@router.get("/payroll-schedule/{year}/{month}")
async def get_payroll_schedule(year: int, month: int):
    from app.database import supabase
    import re
    import datetime

    date_from = f"{year}-{month:02d}-01"
    last_day = (datetime.date(year, month % 12 + 1, 1) if month < 12 else datetime.date(year + 1, 1, 1)) - datetime.timedelta(days=1)
    date_to = last_day.strftime("%Y-%m-%d")

    result = supabase.table("payroll")\
        .select("staff_name, period_start, period_end, notes")\
        .gte("period_start", date_from)\
        .lte("period_start", date_to)\
        .execute()
    print(f"[PAYROLL-SCHEDULE] {date_from} to {date_to} found={len(result.data)} data={result.data}")

    shifts_by_day = {}
    visits_by_day = {}

    for p in result.data:
        notes = p.get("notes") or ""
        staff = p["staff_name"]
        year_str = str(year)

        shifts_match = re.search(r"Смены?:\s*([\d,\s]+)", notes)
        if shifts_match:
            days = [int(d.strip()) for d in shifts_match.group(1).split(",") if d.strip().isdigit()]
            for day in days:
                if day not in shifts_by_day:
                    shifts_by_day[day] = []
                shifts_by_day[day].append(staff)

        visits_match = re.findall(r"(?:Выходы?|Выход)[^:]*:([^\n]+?)(?:\.\s+[А-Я]|$)", notes)
        for vm in visits_match:
            entries = re.findall(r"(\d{2})\.(\d{2})=(\d+)", vm)
            for day_str, month_str, pay in entries:
                if int(month_str) == month:
                    day = int(day_str)
                    if day not in visits_by_day:
                        visits_by_day[day] = []
                    visits_by_day[day].append({"staff_name": staff, "pay": int(pay)})

    return {
        "shifts_from_payroll": shifts_by_day,
        "visits_from_payroll": visits_by_day
    }



@router.get("/pl-detail")
async def pl_detail(month: str, category: str):
    """Детализация P&L по месяцу и категории"""
    try:
        from app.database import supabase
        date_from = month + "-01"
        import calendar
        y, m = map(int, month.split("-"))
        last_day = calendar.monthrange(y, m)[1]
        date_to = f"{month}-{last_day}"

        if category == "salary":
            # ФОТ из payroll
            result = supabase.table("payroll").select(
                "staff_name, period_start, period_end, shifts, shift_pay, visit_pay, bonus_loyalty, total_accrued, status"
            ).eq("company_id", COMPANY_ID).gte(
                "period_start", date_from
            ).lte("period_start", date_to).order("staff_name").execute()
            rows = [{"label": f"{p['staff_name']} ({p['period_start'][:7]} {p['period_start'][8:10]}–{p['period_end'][8:10]})",
                     "detail": f"{p['shifts']} смен × 5000 + выходы {p['visit_pay']} + бонусы {p['bonus_loyalty']}",
                     "amount": float(p["total_accrued"] or 0),
                     "status": p["status"]} for p in result.data]
            return {"category": "ФОТ", "month": month, "rows": rows,
                    "total": sum(r["amount"] for r in rows)}

        elif category in ("salon_rent", "rent", "marketing"):
            result = supabase.table("bank_transactions").select(
                "date, amount, description, counterparty, period, category"
            ).eq("company_id", COMPANY_ID).eq(
                "category", "salon_rent"
            ).execute()
            rows = []
            for t in result.data:
                period = (t.get("period") or t["date"])[:7]
                if period != month:
                    continue
                desc = (t.get("description") or "").lower()
                is_marketing = "рекламн" in desc
                if category == "marketing" and not is_marketing:
                    continue
                if category in ("rent", "salon_rent") and is_marketing:
                    continue
                rows.append({
                    "label": t["counterparty"] or t["description"][:50],
                    "detail": t["description"][:100],
                    "amount": abs(float(t["amount"] or 0)),
                    "date": t["date"]
                })
            return {"category": category, "month": month, "rows": rows,
                    "total": sum(r["amount"] for r in rows)}

        elif category == "cosmetics":
            result = supabase.table("bank_transactions").select(
                "date, amount, description, counterparty"
            ).eq("company_id", COMPANY_ID).eq(
                "category", "cosmetics"
            ).gte("date", date_from).lte("date", date_to).execute()
            rows = [{"label": t["counterparty"] or "", "detail": t["description"][:100],
                     "amount": abs(float(t["amount"] or 0)), "date": t["date"]} for t in result.data]
            return {"category": "Косметика", "month": month, "rows": rows,
                    "total": sum(r["amount"] for r in rows)}

        elif category == "bank_fees":
            result = supabase.table("bank_transactions").select(
                "date, amount, description"
            ).eq("company_id", COMPANY_ID).eq(
                "category", "bank_fee"
            ).gte("date", date_from).lte("date", date_to).execute()
            rows = [{"label": t["description"][:60], "detail": "",
                     "amount": abs(float(t["amount"] or 0)), "date": t["date"]} for t in result.data]
            return {"category": "Банк", "month": month, "rows": rows,
                    "total": sum(r["amount"] for r in rows)}

        elif category in ("revenue_services", "revenue_certificates", "revenue_abonements", "revenue_fitmost"):
            type_filter = {
                "revenue_services": "услуг",
                "revenue_certificates": "сертификат",
                "revenue_abonements": "абонемент"
            }
            if category == "revenue_fitmost":
                result = supabase.table("bank_transactions").select(
                    "date, amount, counterparty, period"
                ).eq("company_id", COMPANY_ID).eq("type", "Кредит").ilike(
                    "counterparty", "%фитмост%"
                ).gte("date", date_from).lte("date", date_to).execute()
                rows = [{"label": "Fitmost", "detail": t["counterparty"],
                         "amount": float(t["amount"] or 0), "date": t["date"]} for t in result.data]
            else:
                keyword = type_filter.get(category, "")
                result = supabase.table("transactions").select(
                    "date, amount, type_title, client_name"
                ).eq("company_id", COMPANY_ID).gt("amount", 0).ilike(
                    "type_title", f"%{keyword}%"
                ).gte("date", date_from).lte("date", date_to).order("date", desc=True).execute()
                rows = [{"label": t["type_title"] or "", "detail": t.get("client_name") or "",
                         "amount": float(t["amount"] or 0), "date": t["date"][:10]} for t in result.data]
            return {"category": category, "month": month, "rows": rows,
                    "total": sum(r["amount"] for r in rows)}

        return {"category": category, "month": month, "rows": [], "total": 0}

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}

# ── Справочники ────────────────────────────────────────────────
VALID_CATEGORIES = {
    "bank_fee", "cosmetics", "salon_rent", "credit", "internal",
    "salary", "marketing", "materials", "food", "transport", "other",
    "transfer_in", "production", "credit_card", "investor", "tax",
}
 
VALID_PROJECTS = {
    "salon", "personal", "podcast", "book", "consulting", "internal",
}
 
 
# ── GET /analytics/transactions ────────────────────────────────
@router.get("/transactions", summary="Объединённый аудит транзакций")
async def get_transactions(
    month:    Optional[str] = None,   # "2025-11"
    source:   Optional[str] = None,   # bank | personal | cash
    category: Optional[str] = None,
    project:  Optional[str] = None,
    page:     int = 1,
    per_page: int = 50,
):
    """
    Возвращает объединённый постраничный список транзакций из:
      - bank_transactions
      - personal_transactions
      - (cash: bank_transactions с пометкой source='cash', если нужно добавить фильтр)
    """
    try:
        from app.database import supabase
 
        per_page = min(max(per_page, 1), 200)
        offset   = (page - 1) * per_page
 
        # Диапазон дат по месяцу
        date_from = date_to = None
        if month:
            y, m    = map(int, month.split("-"))
            last_day = cal_module.monthrange(y, m)[1]
            date_from = f"{month}-01"
            date_to   = f"{month}-{last_day:02d}"
 
        rows = []
 
        # ── 1. bank_transactions ──────────────────────────────
        if not source or source == "bank":
            q = supabase.table("bank_transactions").select(
                "id, date, amount, description, counterparty, category, project"
            ).eq("company_id", COMPANY_ID)
 
            if date_from: q = q.gte("date", date_from)
            if date_to:   q = q.lte("date", date_to)
            if category == "__empty__": q = q.or_("category.is.null,category.eq.")
            elif category:  q = q.eq("category", category)
            if project:   q = q.eq("project",  project)
 
            result = q.order("date", desc=True).execute()
            for r in result.data:
                rows.append({
                    "id":          r["id"],
                    "source":      "bank",
                    "date":        r["date"][:10],
                    "amount":      float(r["amount"] or 0),
                    "description": r.get("description") or "",
                    "counterparty":r.get("counterparty") or "",
                    "category":    r.get("category") or "",
                    "project":     r.get("project")  or "",
                })
 
        # ── 2. personal_transactions ──────────────────────────
        if not source or source == "personal":
            q = supabase.table("personal_transactions").select(
                "id, date, amount, description, expense_category, project"
            ).eq("company_id", COMPANY_ID)
 
            if date_from: q = q.gte("date", date_from)
            if date_to:   q = q.lte("date", date_to)
            if category == "__empty__": q = q.or_("expense_category.is.null,expense_category.eq.")
            elif category:  q = q.eq("expense_category", category)
            if project:   q = q.eq("project",          project)
 
            result = q.order("date", desc=True).execute()
            for r in result.data:
                rows.append({
                    "id":          r["id"],
                    "source":      "personal",
                    "date":        r["date"][:10],
                    "amount":      float(r["amount"] or 0),
                    "description": r.get("description") or "",
                    "counterparty": "",
                    "category":    r.get("expense_category") or "",
                    "project":     r.get("project") or "",
                })
 
        # ── 3. Касса (bank_transactions с source='cash') ──────
        # Если в bank_transactions есть поле source/type = 'cash',
        # они уже попадут в блок "bank". Отдельный блок не нужен,
        # если структура другая — добавьте здесь аналогично.
 
        # Сортировка объединённого списка по дате убыванием
        rows.sort(key=lambda r: r["date"], reverse=True)
 
        total = len(rows)
        page_rows = rows[offset: offset + per_page]
 
        return {
            "total":    total,
            "page":     page,
            "per_page": per_page,
            "rows":     page_rows,
        }
 
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}
 
 
# ── PATCH /analytics/transactions/{id} ────────────────────────
@router.patch("/transactions/{tx_id}", summary="Inline-редактирование транзакции")
async def patch_transaction(
    tx_id:  int,
    body:   dict = Body(...),
):
    """
    Обновляет category и/или project транзакции.
    Тело: { "source": "bank"|"personal", "category": "...", "project": "..." }
    """
    try:
        from app.database import supabase
 
        source   = body.get("source", "bank")
        category = body.get("category")
        project  = body.get("project")
 
        # Валидация
        if category and category not in VALID_CATEGORIES:
            return {"ok": False, "error": f"Неизвестная категория: {category}"}
        if project and project not in VALID_PROJECTS:
            return {"ok": False, "error": f"Неизвестный проект: {project}"}
 
        update = {}
        if category is not None:
            update["category" if source == "bank" else "expense_category"] = category
        if project is not None:
            update["project"] = project
 
        if not update:
            return {"ok": False, "error": "Нечего обновлять"}
 
        table = "bank_transactions" if source == "bank" else "personal_transactions"
        result = supabase.table(table).update(update).eq("id", tx_id).execute()
 
        return {"ok": True, "updated": len(result.data)}
 
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}

# ── POST /analytics/transactions/auto-categorize ──────────────
@router.post("/transactions/auto-categorize", summary="Авто-разметка транзакций по ключевым словам")
async def auto_categorize_transactions():
    try:
        from app.database import supabase

        RULES = [
            ("зачисление средств по терминалам эквайринга", "transfer_in"),
            ("оплата за услуги спа",                        "transfer_in"),
            ("фитмост",                                     "transfer_in"),
            ("комиссия за операции по терминалам",          "bank_fee"),
            ("комиссия за внешний банковский перевод",      "bank_fee"),
            ("комиссия за вывод средств",                   "bank_fee"),
            ("плата за обслуживание счета",                 "bank_fee"),
            ("плата за пакет",                              "bank_fee"),
            ("плата за услугу оповещение",                  "bank_fee"),
            ("плата за активный овердрафт",                 "bank_fee"),
            ("плата за использованный лимит",               "bank_fee"),
            ("задолженность по договору кредита",           "credit"),
            ("погашение разрешенного овердрафта",           "credit"),
            ("предоставление овердрафта",                   "credit"),
            ("предоставление  овердрафта",                  "credit"),
            ("перевод собственных средств",                 "internal"),
            ("реестр",                                      "salary"),
            ("оплата налогов",                              "tax"),
            ("продюсирования",                              "production"),
        ]

        result = supabase.table("bank_transactions").select(
            "id, description, counterparty"
        ).eq("company_id", COMPANY_ID).or_(
            "category.is.null,category.eq."
        ).execute()

        updated = 0
        skipped = 0

        for row in result.data:
            desc = ((row.get("description") or "") + " " + (row.get("counterparty") or "")).lower()
            matched = None
            for keyword, category in RULES:
                if keyword in desc:
                    matched = category
                    break

            if matched:
                supabase.table("bank_transactions").update(
                    {"category": matched}
                ).eq("id", row["id"]).execute()
                updated += 1
            else:
                skipped += 1

        return {"ok": True, "updated": updated, "skipped": skipped}

    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}


# ── GET /analytics/reconciliation ─────────────────────────────
@router.get("/reconciliation", summary="Сверка: YClients vs Банк по месяцам")
async def get_reconciliation():
    """
    Две сверки по месяцам:
    1. Терминал ТБанк: YCL Расчетный счет vs bank transfer_in от ТБанк
    2. Онлайн ЮKassa: YCL Эквайринг ЮKassa vs Аванпост
    """
    try:
        from app.database import supabase
        from collections import defaultdict

        # ── YClients по месяцам и account ─────────────────────
        ycl = fetch_all(supabase, lambda: supabase.table("transactions").select(
            "date, amount, account, type_title"
        ).eq("company_id", COMPANY_ID).gt("amount", 0))

        EXCLUDE_TYPES = {"Продажа сертификатов"}
        ycl_terminal = defaultdict(float)
        ycl_online   = defaultdict(float)
        ycl_cash     = defaultdict(float)

        for r in ycl:
            if r.get("type_title") in EXCLUDE_TYPES:
                continue
            month  = r["date"][:7]
            amount = float(r["amount"] or 0)
            if r["account"] == "Расчетный счет":
                ycl_terminal[month] += amount
            elif r["account"] == "Эквайринг ЮKassa":
                ycl_online[month] += amount
            elif r["account"] == "Основная касса":
                ycl_cash[month] += amount

        # ── Банк: ТБанк transfer_in ────────────────────────────
        tbank = fetch_all(supabase, lambda: supabase.table("bank_transactions").select(
            "date, amount, description, category, counterparty"
        ).eq("company_id", COMPANY_ID).ilike("counterparty", "%тбанк%").gt("amount", 0))

        import re as _re2
        from datetime import date as _dt2, timedelta as _td2
        bank_terminal = defaultdict(float)
        for r in tbank:
            if r.get("category") in ("transfer_in", "Входящие платежи"):
                # Используем дату операции из description (банк зачисляет на след. день)
                desc = r.get("description") or ""
                m_d = _re2.search(r"от (\d{2})\.(\d{2})\.(\d{4})", desc)
                if m_d:
                    op_day = f"{m_d.group(3)}-{m_d.group(2)}-{m_d.group(1)}"
                    # YCL день = op_day - 1
                    ycl_day = (_dt2.fromisoformat(op_day) - _td2(days=1)).isoformat()
                    bank_terminal[ycl_day[:7]] += float(r["amount"] or 0)
                else:
                    bank_terminal[r["date"][:7]] += float(r["amount"] or 0)

        # ── Банк: ТБанк комиссия эквайринга ───────────────────
        tbank_fees = fetch_all(supabase, lambda: supabase.table("bank_transactions").select(
            "date, amount, description, category, counterparty"
        ).eq("company_id", COMPANY_ID).ilike("counterparty", "%тбанк%").lt("amount", 0).eq("category", "bank_fee"))

        bank_terminal_fee = defaultdict(float)
        for r in tbank_fees:
            bank_terminal_fee[r["date"][:7]] += abs(float(r["amount"] or 0))

        # ── Банк: Fitmost ──────────────────────────────────────
        fitmost = fetch_all(supabase, lambda: supabase.table("bank_transactions").select(
            "date, amount"
        ).eq("company_id", COMPANY_ID).ilike("counterparty", "%фитмост%").gt("amount", 0))

        bank_fitmost = defaultdict(float)
        for r in fitmost:
            bank_fitmost[r["date"][:7]] += float(r["amount"] or 0)

        # ── Fitmost записи из records ────────────────────────────
        fitmost_records = fetch_all(supabase, lambda: supabase.table("records").select(
            "date, service_cost"
        ).eq("company_id", COMPANY_ID).eq("record_from", "Партнёры: Fitmost 511055"))

        fitmost_count = defaultdict(int)
        fitmost_full  = defaultdict(float)
        for r in fitmost_records:
            _m = r["date"][:7]
            fitmost_count[_m] += 1
            fitmost_full[_m]  += float(r["service_cost"] or 0)

        # ── Банк: Аванпост ─────────────────────────────────────
        avanpost = fetch_all(supabase, lambda: supabase.table("bank_transactions").select(
            "date, amount, description, category, counterparty"
        ).eq("company_id", COMPANY_ID).gt("amount", 0).or_(
            "counterparty.ilike.%аванпост%,category.eq.acquiring"
        ))


        import re as _re
        bank_online         = defaultdict(float)
        bank_online_fee     = defaultdict(float)

        for r in avanpost:
            amount = float(r["amount"] or 0)
            desc   = r.get("description") or ""
            # Дата операции: "за DD.MM.YYYY" или "по DD.MM.YYYY"
            m_date = _re.search(r"(?:за|по реестру за)\s+(\d{2})\.(\d{2})\.(\d{4})", desc)
            # Комиссия: "Комиссия 475,20 руб" или "Комиссия 404,25 руб,"
            m_fee  = _re.search(r"Комиссия\s+([\d\s]+[,.]\d+)\s+руб", desc)

            if m_date:
                op_month = f"{m_date.group(3)}-{m_date.group(2)}"
                bank_online[op_month] += amount
                if m_fee:
                    fee_str = m_fee.group(1).replace("\xa0", "").replace(" ", "").replace(",", ".")
                    bank_online_fee[op_month] += float(fee_str)
            else:
                # Диапазон дат "за период с DD.MM по DD.MM" — берём последнюю дату
                m_range = _re.search(r"по\s+(\d{2})\.(\d{2})\.(\d{4})", desc)
                op_month = f"{m_range.group(3)}-{m_range.group(2)}" if m_range else r["date"][:7]
                bank_online[op_month] += amount
                if m_fee:
                    fee_str = m_fee.group(1).replace("\xa0", "").replace(" ", "").replace(",", ".")
                    bank_online_fee[op_month] += float(fee_str)

        # ── Сборка по месяцам ──────────────────────────────────
        all_months = sorted(set(
            list(ycl_terminal.keys()) + list(ycl_online.keys()) +
            list(bank_terminal.keys()) + list(bank_online.keys())
        ))

        months = []
        for m in all_months:
            ycl_t   = round(ycl_terminal[m])
            bank_t  = round(bank_terminal[m])
            fee_t   = round(bank_terminal_fee[m])
            fitmost = round(bank_fitmost[m])
            fm_count  = fitmost_count[m]
            fm_full   = round(fitmost_full[m])
            fm_expect = round(fm_full * 0.65)
            # gross банка = зачислено + комиссия (комиссия уже вычтена банком)
            bank_t_gross = bank_t + fee_t
            diff_t  = ycl_t - bank_t_gross


            ycl_o        = round(ycl_online[m])
            bank_o       = round(bank_online[m])
            fee_o        = round(bank_online_fee.get(m, 0))
            bank_o_gross = bank_o + fee_o
            diff_o       = ycl_o - bank_o_gross
            fee_o_pct    = round(fee_o / bank_o_gross * 100, 1) if bank_o_gross else 0

            ycl_cash_m = round(ycl_cash[m])
            # YCL total карточных = Расчетный счет + Касса (наличные/СБП)
            ycl_t_total = ycl_t + ycl_cash_m

            months.append({
                "month": m,
                "terminal_ycl":        ycl_t,
                "terminal_ycl_cash":   ycl_cash_m,
                "terminal_ycl_total":  ycl_t_total,
                "terminal_bank":       bank_t,
                "terminal_fee":        fee_t,
                "terminal_bank_gross": bank_t_gross,
                "terminal_fitmost":    fitmost,
                "fitmost_count":       fm_count,
                "fitmost_full":        fm_full,
                "fitmost_expect":      fm_expect,
                "fitmost_bank":        fitmost,
                # Разница = банк gross - YCL карточных (без наличных)
                "terminal_diff":       diff_t,
                "terminal_ok":         abs(diff_t) < 5000,
                "online_ycl":          ycl_o,
                "online_bank":         bank_o,
                "online_fee":          fee_o,
                "online_fee_pct":      fee_o_pct,
                "online_bank_gross":   bank_o_gross,
                "online_diff":         diff_o,
                "online_ok":           abs(diff_o) < 3000,
            })

        return {"months": list(reversed(months))}

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


# ── GET /analytics/reconciliation-detail ──────────────────────
@router.get("/reconciliation-detail", summary="Детализация сверки по месяцу и источнику")
async def reconciliation_detail(month: str, side: str):
    """
    side: ycl_terminal | ycl_cash | bank_terminal | ycl_online | bank_online
    """
    try:
        from app.database import supabase
        import calendar as _cal

        y, m = map(int, month.split("-"))
        last_day = _cal.monthrange(y, m)[1]
        date_from = f"{month}-01"
        date_to   = f"{month}-{last_day:02d}"

        rows = []
        total = 0.0

        if side == "ycl_terminal":
            result = supabase.table("transactions").select(
                "date, amount, account, type_title, client_name"
            ).eq("company_id", COMPANY_ID).eq(
                "account", "Расчетный счет"
            ).gte("date", date_from).lte("date", date_to).order("date", desc=True).execute()
            for r in result.data:
                amt = float(r["amount"] or 0)
                rows.append({"date": r["date"][:10], "label": r.get("type_title") or "", "detail": r.get("client_name") or "", "amount": amt})
                total += amt

        elif side == "ycl_cash":
            result = supabase.table("transactions").select(
                "date, amount, account, type_title, client_name"
            ).eq("company_id", COMPANY_ID).eq(
                "account", "Основная касса"
            ).gte("date", date_from).lte("date", date_to).order("date", desc=True).execute()
            for r in result.data:
                amt = float(r["amount"] or 0)
                rows.append({"date": r["date"][:10], "label": r.get("type_title") or "", "detail": r.get("client_name") or "", "amount": amt})
                total += amt

        elif side == "bank_terminal":
            result = supabase.table("bank_transactions").select(
                "date, amount, description, category"
            ).eq("company_id", COMPANY_ID).ilike(
                "counterparty", "%тбанк%"
            ).gt("amount", 0).in_(
                "category", ["transfer_in", "Входящие платежи"]
            ).gte("date", date_from).lte("date", date_to).order("date", desc=True).execute()
            for r in result.data:
                amt = float(r["amount"] or 0)
                rows.append({"date": r["date"][:10], "label": r.get("description") or "", "detail": r.get("category") or "", "amount": amt})
                total += amt

        elif side == "ycl_online":
            result = supabase.table("transactions").select(
                "date, amount, type_title, client_name"
            ).eq("company_id", COMPANY_ID).eq(
                "account", "Эквайринг ЮKassa"
            ).gte("date", date_from).lte("date", date_to).order("date", desc=True).execute()
            for r in result.data:
                amt = float(r["amount"] or 0)
                rows.append({"date": r["date"][:10], "label": r.get("type_title") or "", "detail": r.get("client_name") or "", "amount": amt})
                total += amt

        elif side == "bank_online":
            import re as _re
            result = supabase.table("bank_transactions").select(
                "date, amount, description"
            ).eq("company_id", COMPANY_ID).gt("amount", 0).or_(
                "counterparty.ilike.%аванпост%,category.eq.acquiring"
            ).gte("date", date_from).lte("date", date_to).order("date", desc=True).execute()
            for r in result.data:
                amt = float(r["amount"] or 0)
                desc = r.get("description") or ""
                m_fee = _re.search(r"Комиссия\s+([\d\s]+[,.]\d+)\s+руб", desc)
                fee = float(m_fee.group(1).replace(" ", "").replace(",", ".")) if m_fee else 0
                rows.append({"date": r["date"][:10], "label": desc[:80], "detail": f"комиссия {fee:.2f}" if fee else "", "amount": amt})
                total += amt

        return {"month": month, "side": side, "rows": rows, "total": round(total)}

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


# Базовые цены Fitmost (из отчётов за месяцы до 30 посещений)
FITMOST_BASE_PRICE = {
    "Массаж спины":                              2275,
    "Массаж шейно-воротниковой зоны":            1625,
    "Массаж головы":                             2275,
    "«\u200eГималайский экспресс»\u200e (Express Head SPA)": 3835,
    "«\u200eГималайский дзен»\u200e (Relax Head SPA)":       5525,
    "Массаж всего тела":                         3185,
    "Массаж лица фирменный":                     2925,
    "«\u200eПерерождение»\u200e (Premium Head SPA)":         7085,
    "SPA для двоих (запись через администратора)": 11050,
}

def fitmost_rate(count: int) -> float:
    if count <= 30:   return 1.0
    if count <= 60:   return 0.95
    if count <= 90:   return 0.90
    return 0.85

# ── GET /analytics/fitmost-reconciliation ─────────────────────
@router.get("/fitmost-reconciliation", summary="Сверка Fitmost: записи vs платежи")
async def fitmost_reconciliation():
    try:
        from app.database import supabase
        from collections import defaultdict

        # Записи Fitmost (авто-заглушки агрегатора)
        fitmost_records = fetch_all(supabase, lambda: supabase.table("records").select(
            "date, service_cost, client_name, service_title"
        ).eq("company_id", COMPANY_ID).eq("record_from", "Партнёры: Fitmost 511055").order("date"))

        by_month_records = defaultdict(list)
        for r in fitmost_records:
            m = r["date"][:7]
            title = r.get("service_title") or ""
            base = FITMOST_BASE_PRICE.get(title, float(r["service_cost"] or 0))
            by_month_records[m].append({
                "date":    r["date"][:10],
                "client":  r.get("client_name") or "—",
                "service": title,
                "cost":    round(base),
            })

        # Платежи от Fitmost из банка
        bank_payments = fetch_all(supabase, lambda: supabase.table("bank_transactions").select(
            "date, amount, description"
        ).eq("company_id", COMPANY_ID).ilike("counterparty", "%фитмост%").gt("amount", 0).order("date"))

        MONTH_RU = {
            "январ": "01", "феврал": "02", "март": "03", "апрел": "04",
            "май": "05", "мая": "05", "июн": "06", "июл": "07",
            "август": "08", "сентябр": "09", "октябр": "10",
            "ноябр": "11", "декабр": "12",
        }

        by_month_payments = defaultdict(list)
        for r in bank_payments:
            desc = (r.get("description") or "").lower()
            # Пробуем извлечь период из описания: "за Ноябрь 2025"
            m_period = None
            import re as _re
            match = _re.search(r"за\s+(\w+)\s+(20\d{2})", desc)
            if match:
                month_word = match.group(1)[:6]
                year       = match.group(2)
                for key, num in MONTH_RU.items():
                    if month_word.startswith(key[:4]):
                        m_period = f"{year}-{num}"
                        break
            if not m_period:
                # Fallback: сдвиг на -1 месяц от даты зачисления
                from datetime import date as _d, timedelta as _td
                pay_date = _d.fromisoformat(r["date"][:10])
                m_period = (pay_date.replace(day=1) - _td(days=1)).strftime("%Y-%m")
            by_month_payments[m_period].append({
                "date":   r["date"][:10],
                "amount": round(float(r["amount"] or 0)),
                "desc":   (r.get("description") or "")[:80],
            })

        all_months = sorted(set(list(by_month_records.keys()) + list(by_month_payments.keys())))

        cumulative_expect   = 0.0
        cumulative_received = 0.0
        months = []

        for m in all_months:
            recs     = by_month_records.get(m, [])
            payments = by_month_payments.get(m, [])

            # Динамическая комиссия Fitmost в зависимости от кол-ва бронирований
            count = len(recs)
            rate  = fitmost_rate(count)
            month_full_cost = sum(r["cost"] for r in recs)
            month_expect    = round(month_full_cost * rate)
            month_received = sum(p["amount"] for p in payments)

            cumulative_expect   += month_expect
            cumulative_received += month_received

            months.append({
                "month":               m,
                "count":               len(recs),
                "full_cost":           round(sum(r["cost"] for r in recs)),
                "month_expect":        round(month_expect),
                "month_received":      round(month_received),
                "month_diff":          round(month_received - month_expect),
                "cumulative_expect":   round(cumulative_expect),
                "cumulative_received": round(cumulative_received),
                "debt":                round(cumulative_expect - cumulative_received),
                "payments":            payments,
            })

        return {
            "months":         list(reversed(months)),
            "total_expect":   round(cumulative_expect),
            "total_received": round(cumulative_received),
            "total_debt":     round(cumulative_expect - cumulative_received),
        }

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


# ── GET /analytics/fitmost-detail ─────────────────────────────
@router.get("/fitmost-detail", summary="Детализация записей Fitmost за месяц")
async def fitmost_detail(month: str):
    try:
        from app.database import supabase
        import calendar as _cal

        y, m_int  = map(int, month.split("-"))
        last_day  = _cal.monthrange(y, m_int)[1]
        date_from = f"{month}-01"
        date_to   = f"{month}-{last_day:02d}"

        result = supabase.table("records").select(
            "date, service_cost, client_name, service_title"
        ).eq("company_id", COMPANY_ID).eq(
            "record_from", "Партнёры: Fitmost 511055"
        ).gte("date", date_from).lte("date", date_to + "T23:59:59").order("date").execute()

        rows = []
        total_cost = 0.0
        for r in result.data:
            title = r.get("service_title") or ""
            base  = FITMOST_BASE_PRICE.get(title, float(r["service_cost"] or 0))
            total_cost += base
            rows.append({
                "date":    r["date"][:10],
                "client":  r.get("client_name") or "—",
                "service": title,
                "cost":    round(base),
            })

        rate         = fitmost_rate(len(rows))
        total_expect = round(total_cost * rate)

        return {
            "month":        month,
            "rate":         rate,
            "rows":         rows,
            "total_cost":   round(total_cost),
            "total_expect": total_expect,
        }

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


# ── GET /analytics/fitmost-payments ───────────────────────────
@router.get("/fitmost-payments", summary="Платежи Fitmost из банка за месяц")
async def fitmost_payments(month: str):
    try:
        from app.database import supabase
        import calendar as _cal

        y, m_int  = map(int, month.split("-"))
        last_day  = _cal.monthrange(y, m_int)[1]
        date_from = f"{month}-01"
        date_to   = f"{month}-{last_day:02d}"

        # Ищем платёж по описанию — там указан месяц за который он пришёл
        import re as _re
        MONTH_RU_MAP = {
            "январ": "01", "феврал": "02", "март": "03", "апрел": "04",
            "май": "05", "мая": "05", "июн": "06", "июл": "07",
            "август": "08", "сентябр": "09", "октябр": "10",
            "ноябр": "11", "декабр": "12",
        }
        all_payments = supabase.table("bank_transactions").select(
            "date, amount, description, counterparty"
        ).eq("company_id", COMPANY_ID).ilike(
            "counterparty", "%фитмост%"
        ).gt("amount", 0).order("date").execute()

        rows = []
        total = 0.0
        for r in all_payments.data:
            desc = (r.get("description") or "").lower()
            match = _re.search(r"за\s+(\w+)\s+(20\d{2})", desc)
            pay_month = None
            if match:
                word = match.group(1)[:6]
                year = match.group(2)
                for key, num in MONTH_RU_MAP.items():
                    if word.startswith(key[:4]):
                        pay_month = f"{year}-{num}"
                        break
            if not pay_month:
                from datetime import date as _d, timedelta as _td
                pd = _d.fromisoformat(r["date"][:10])
                pay_month = (pd.replace(day=1) - _td(days=1)).strftime("%Y-%m")
            if pay_month != month:
                continue
            amt = float(r["amount"] or 0)
            total += amt
            rows.append({
                "date":        r["date"][:10],
                "amount":      round(amt),
                "description": (r.get("description") or "")[:100],
                "counterparty": r.get("counterparty") or "",
            })

        return {"month": month, "rows": rows, "total": round(total)}

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}
@router.get("/reconciliation-days", summary="Сверка по дням внутри месяца")
async def reconciliation_days(month: str):
    try:
        from app.database import supabase
        from collections import defaultdict
        import calendar as _cal
        import re as _re

        y, m = map(int, month.split("-"))
        last_day = _cal.monthrange(y, m)[1]
        date_from = f"{month}-01"
        date_to   = f"{month}-{last_day:02d}"

        # YCL по дням — только реальные оплаты (без сертификатов)
        # Берём +1 день до начала месяца — банк зачисляет на след. день
        EXCLUDE_TYPES = {"Продажа сертификатов"}
        from datetime import date as _date2, timedelta as _td2
        date_from_ext = (_date2.fromisoformat(date_from) - _td2(days=1)).isoformat()
        ycl = supabase.table("transactions").select(
            "date, amount, account, type_title"
        ).eq("company_id", COMPANY_ID).gt("amount", 0).gte(
            "date", date_from_ext + "T00:00:00"
        ).lte("date", date_to + "T23:59:59").execute()

        ycl_card = defaultdict(float)
        ycl_cash = defaultdict(float)
        for r in ycl.data:
            if r.get("type_title") in EXCLUDE_TYPES:
                continue
            day = r["date"][:10]
            amt = float(r["amount"] or 0)
            if r["account"] == "Расчетный счет":
                ycl_card[day] += amt
            elif r["account"] == "Основная касса":
                ycl_cash[day] += amt

        # Банк эквайринг — по дате операции из description
        bank = supabase.table("bank_transactions").select(
            "date, amount, description, category"
        ).eq("company_id", COMPANY_ID).ilike(
            "counterparty", "%тбанк%"
        ).gt("amount", 0).in_(
            "category", ["transfer_in", "Входящие платежи"]
        ).gte("date", date_from).lte("date", date_to).execute()

        bank_by_opday = defaultdict(float)
        for r in bank.data:
            desc = r.get("description") or ""
            m_date = _re.search(r"от (\d{2})\.(\d{2})\.(\d{4})", desc)
            if m_date:
                op_day = f"{m_date.group(3)}-{m_date.group(2)}-{m_date.group(1)}"
            else:
                op_day = r["date"][:10]
            bank_by_opday[op_day] += float(r["amount"] or 0)

        # Объединяем все дни
        from datetime import date as _date, timedelta as _td
        all_days = sorted(set(
            list(ycl_card.keys()) + list(ycl_cash.keys()) + list(bank_by_opday.keys())
        ))

        # Продажи товаров — вычитаем из банка (они уже учтены отдельно)
        sales = supabase.table("product_sales").select(
            "date, amount, account"
        ).eq("company_id", COMPANY_ID).gte("date", date_from_ext).lte("date", date_to).execute()

        sales_card_by_day = defaultdict(float)
        for r in sales.data:
            if r.get("account") == "card":
                sales_card_by_day[r["date"][:10]] += float(r["amount"] or 0)

        # Перестраиваем bank_by_opday: ключ = дата операции в YCL (банк зачисляет на след. день)
        # "Зачисление от DD.MM" → операция была DD.MM - 1 рабочий день
        bank_by_ycl_day = defaultdict(float)  # ключ = дата в YCL
        for op_day, amt in bank_by_opday.items():
            d = _date.fromisoformat(op_day)
            ycl_day = (d - _td(days=1)).isoformat()
            bank_by_ycl_day[ycl_day] += amt

        # Вычитаем карточные продажи товаров из банка
        for day, amt in sales_card_by_day.items():
            bank_by_ycl_day[day] -= amt

        all_days = sorted(set(
            list(ycl_card.keys()) + list(ycl_cash.keys()) + list(bank_by_ycl_day.keys())
        ))
        # Последний день месяца помечаем как пограничный но не исключаем

        rows = []
        for day in all_days:
            card     = round(ycl_card[day])
            cash     = round(ycl_cash[day])
            bank_amt = round(bank_by_ycl_day[day])
            diff     = card - bank_amt

            # Подозрение: банк есть, карта=0, но касса есть → карта записана как касса?
            suspicious = bank_amt > 500 and card == 0 and cash > 0 and cash < bank_amt * 0.8
            # Нет в YCL: банк есть, карта=0, касса=0
            real_missing = bank_amt > 500 and card == 0 and cash < 500
            mismatch = abs(diff) > 500

            boundary = (day == date_to)  # последний день — карта уйдёт в следующий месяц
            rows.append({
                "day":          day,
                "ycl_card":     card,
                "ycl_cash":     cash,
                "bank":         bank_amt,
                "diff":         diff,
                "suspicious":   suspicious,
                "real_missing": real_missing,
                "mismatch":     mismatch or (boundary and card > 0),
                "boundary":     boundary,
            })

        # Комиссия ТБанк за период
        fee_result = supabase.table("bank_transactions").select(
            "amount"
        ).eq("company_id", COMPANY_ID).ilike(
            "counterparty", "%тбанк%"
        ).eq("category", "bank_fee").gte("date", date_from).lte("date", date_to).execute()
        total_fee = round(sum(abs(float(r["amount"] or 0)) for r in fee_result.data))

        # total_ycl — только текущий месяц (без расширенного дня)
        total_ycl  = round(sum(v for k, v in ycl_card.items() if k >= date_from))
        total_bank_shifted = round(sum(bank_by_ycl_day.values()))
        total_bank_gross   = total_bank_shifted + total_fee

        return {
            "month": month,
            "rows":  rows,
            "total_ycl_card":     total_ycl,
            "total_ycl_cash":     round(sum(ycl_cash.values())),
            "total_bank":         round(sum(bank_by_opday.values())),
            "total_bank_shifted": total_bank_shifted,
            "total_bank_gross":   total_bank_gross,
            "total_fee":          total_fee,
            "total_diff":         total_ycl - total_bank_gross,
        }

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}



# ── GET /analytics/personal-expenses ──────────────────────────
@router.get("/personal-expenses", summary="Личные расходы по месяцам")
async def personal_expenses(date_from: str = "2026-01-01"):
    try:
        from app.database import supabase
        from collections import defaultdict

        data = fetch_all(supabase, lambda: supabase.table("personal_transactions").select(
            "date, amount, expense_category, description"
        ).eq("company_id", COMPANY_ID).eq("project", "personal").lt("amount", 0).gte("date", date_from).order("date"))

        CATEGORY_LABELS = {
            "food":        "🍽️ Еда",
            "transport":   "🚗 Транспорт",
            "rent":        "🏠 Аренда",
            "health":      "💊 Здоровье",
            "clothes":     "👕 Одежда",
            "entertainment":"🎭 Развлечения",
            "travel":      "✈️ Путешествия",
            "education":   "📚 Образование",
            "credit_card": "💳 Кредит",
            "other":       "📦 Прочее",
            "personal":    "👤 Личное",
            "internal":    "🔄 Внутренние",
        }

        # Группируем по месяцу и категории
        by_month = defaultdict(lambda: defaultdict(float))
        all_cats = set()
        for r in data:
            m   = r["date"][:7]
            cat = r.get("expense_category") or "other"
            amt = abs(float(r["amount"] or 0))
            by_month[m][cat] += amt
            all_cats.add(cat)

        all_months = sorted(by_month.keys())
        all_cats   = sorted(all_cats)

        months = []
        for m in reversed(all_months):
            cats = {}
            total = 0.0
            for cat in all_cats:
                amt = round(by_month[m].get(cat, 0))
                cats[cat] = amt
                total += amt
            months.append({
                "month":      m,
                "categories": cats,
                "total":      round(total),
            })

        grand_total = sum(m["total"] for m in months)

        return {
            "months":      months,
            "categories":  all_cats,
            "cat_labels":  CATEGORY_LABELS,
            "grand_total": round(grand_total),
        }

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}

# ── GET /analytics/personal-expenses-detail ───────────────────
@router.get("/personal-expenses-detail", summary="Детализация личных расходов")
async def personal_expenses_detail(month: str, category: str):
    try:
        from app.database import supabase
        import calendar as _cal

        y, m_int  = map(int, month.split("-"))
        last_day  = _cal.monthrange(y, m_int)[1]
        date_from = f"{month}-01"
        date_to   = f"{month}-{last_day:02d}T23:59:59"

        q = supabase.table("personal_transactions").select(
            "date, amount, expense_category, description"
        ).eq("company_id", COMPANY_ID).eq("project", "personal").lt("amount", 0).gte("date", date_from).lte("date", date_to)

        if category != "__all__":
            q = q.eq("expense_category", category)

        result = q.order("date", desc=True).execute()

        rows = []
        total = 0.0
        for r in result.data:
            amt = abs(float(r["amount"] or 0))
            total += amt
            rows.append({
                "date":        r["date"][:10],
                "description": (r.get("description") or "")[:100],
                "category":    r.get("expense_category") or "other",
                "amount":      round(amt),
            })

        return {"month": month, "category": category, "rows": rows, "total": round(total)}

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


# ── POST /analytics/personal-expenses-categorize ──────────────
@router.post("/personal-expenses-categorize", summary="Авторазметка личных расходов")
async def personal_expenses_categorize(date_from: str = "2026-01-01"):
    try:
        from app.database import supabase

        RULES = [
            # (ключевое слово, категория)
            ("яндекс аренда",        "rent"),
            ("досрочное погашение",   "credit_card"),
            ("беговое сообщество",    "sport"),
            ("яхонты",               "sport"),
            ("московский метрополитен", "transport"),
            ("московский транспорт",  "transport"),
            ("бери заряд",           "transport"),
            ("портал госуслуг",      "government"),
            ("mos.ru",               "government"),
            ("мпц кассы",            "government"),
            ("читай-город",          "education"),
            ("t2",                   "phone"),
            ("powerapp",             "subscriptions"),
            ("подписка",             "subscriptions"),
            ("магнит",               "food"),
            ("вкусвилл",             "food"),
            ("перекрёсток",          "food"),
            ("лента",                "food"),
            ("яндекс лавка",         "food"),
            ("яндекс доставка",      "food"),
            ("вкусно",               "food"),
            ("теремок",              "food"),
            ("farsh",                "food"),
            ("farш",                 "food"),
            ("лепим и варим",        "food"),
            ("пельменная",           "food"),
            ("шоко",                 "food"),
            ("ресторан",             "food"),
            ("mimi",                 "food"),
            ("remy",                 "food"),
            ("fast coffee",          "food"),
            ("сберчаевые",           "food"),
            ("klich",                "food"),
            ("новодевичий",          "food"),
            ("h-406",                "food"),
            ("ozon",                 "shopping"),
            ("яндекс маркет",        "shopping"),
            ("wildberries",          "shopping"),
            ("wb",                   "shopping"),
        ]

        data = supabase.table("personal_transactions").select(
            "id, description, expense_category"
        ).eq("company_id", COMPANY_ID).eq("project", "personal").lt("amount", 0).gte("date", date_from).execute()

        updated = 0
        skipped = 0
        for r in data.data:
            desc = (r.get("description") or "").lower()
            matched = None
            for keyword, category in RULES:
                if keyword.lower() in desc:
                    matched = category
                    break
            if matched and matched != r.get("expense_category"):
                supabase.table("personal_transactions").update(
                    {"expense_category": matched}
                ).eq("id", r["id"]).execute()
                updated += 1
            else:
                skipped += 1

        return {"ok": True, "updated": updated, "skipped": skipped}

    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}


# ── GET /analytics/obligations-fact ───────────────────────────
@router.get("/obligations-fact", summary="Обязательства: план vs факт")
async def obligations_fact(year: int, month: int):
    try:
        from app.database import supabase
        import calendar as _cal
        import re as _re

        last_day  = _cal.monthrange(year, month)[1]
        date_to   = f"{year}-{month:02d}-{last_day:02d}T23:59:59"
        # Расширяем поиск на 5 дней назад — платежи могут приходить в конце предыдущего месяца
        from datetime import date as _dt, timedelta as _td
        date_from_ext = (_dt(year, month, 1) - _td(days=5)).isoformat()
        date_from     = f"{year}-{month:02d}-01"

        # Все активные обязательства с match_rule
        obs = supabase.table("obligations").select("*").eq(
            "company_id", COMPANY_ID).eq("is_active", True).not_.is_("match_rule", "null").execute()

        # Банковские транзакции за месяц + 5 дней предыдущего
        bank = supabase.table("bank_transactions").select(
            "id, date, amount, description, counterparty"
        ).eq("company_id", COMPANY_ID).gte("date", date_from_ext).lte("date", date_to).lt("amount", 0).execute()

        # Личные транзакции за месяц + 5 дней предыдущего
        personal = supabase.table("personal_transactions").select(
            "id, date, amount, description"
        ).eq("company_id", COMPANY_ID).gte("date", date_from_ext).lte("date", date_to).lt("amount", 0).execute()

        result = []
        for o in obs.data:
            rule    = o.get("match_rule") or ""
            source  = o.get("match_source") or "bank"
            pattern = _re.compile(rule, _re.IGNORECASE)

            matched_txs = []

            amt_min = float(o.get("match_amount_min") or 0)
            amt_max = float(o.get("match_amount_max") or 999999999)

            if source in ("bank", "both"):
                for t in bank.data:
                    text = f"{t.get('description','')} {t.get('counterparty','')}".lower()
                    amt  = abs(float(t["amount"] or 0))
                    if pattern.search(text) and amt_min <= amt <= amt_max:
                        matched_txs.append({
                            "source":  "bank",
                            "date":    t["date"][:10],
                            "amount":  round(amt),
                            "description": (t.get("description") or "")[:80],
                        })

            if source in ("personal", "both"):
                for t in personal.data:
                    text = (t.get("description") or "").lower()
                    amt  = abs(float(t["amount"] or 0))
                    if pattern.search(text) and amt_min <= amt <= amt_max:
                        matched_txs.append({
                            "source":  "personal",
                            "date":    t["date"][:10],
                            "amount":  round(amt),
                            "description": (t.get("description") or "")[:80],
                        })

            fact_total = sum(t["amount"] for t in matched_txs)
            plan       = float(o["amount"] or 0)
            diff       = fact_total - plan

            result.append({
                "id":          o["id"],
                "description": o["description"],
                "project":     o["project"],
                "type":        o["type"],
                "day_of_month": o.get("day_of_month"),
                "plan":        round(plan),
                "fact":        round(fact_total),
                "diff":        round(diff),
                "ok":          abs(diff) < plan * 0.05 + 500,
                "transactions": matched_txs,
                "match_rule":  rule,
                "match_source": source,
            })

        # Сортируем по дню месяца
        result.sort(key=lambda x: x["day_of_month"] or 99)

        total_plan = sum(r["plan"] for r in result)
        total_fact = sum(r["fact"] for r in result)

        return {
            "month":      f"{year}-{month:02d}",
            "obligations": result,
            "total_plan": round(total_plan),
            "total_fact": round(total_fact),
            "total_diff": round(total_fact - total_plan),
        }

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


# ── GET /analytics/self-transfers ────────────────────────────
@router.get("/self-transfers", summary="Переводы себе по месяцам")
async def self_transfers(date_from: str = "2026-01-01"):
    try:
        from app.database import supabase
        from collections import defaultdict

        # Исходные переводы себе
        data = fetch_all(supabase, lambda: supabase.table("personal_transactions").select(
            "id, date, amount, description, expense_category, card"
        ).eq("company_id", COMPANY_ID).eq("description", "Дмитрий В.").eq(
            "card", "*4531"
        ).lt("amount", 0).gte("date", date_from).order("date"))

        # Уже размеченные записи
        marked = fetch_all(supabase, lambda: supabase.table("personal_transactions").select(
            "date, amount"
        ).eq("company_id", COMPANY_ID).eq(
            "category", "Переводы себе (разметка)"
        ).eq("project", "personal").lt("amount", 0).gte("date", date_from))

        # Сумма размеченного по месяцам
        marked_by_month = defaultdict(float)
        for r in marked:
            m = r["date"][:7]
            marked_by_month[m] += abs(float(r["amount"] or 0))

        by_month = defaultdict(list)
        for r in data:
            m   = r["date"][:7]
            amt = round(abs(float(r["amount"] or 0)))
            by_month[m].append({
                "id":      r["id"],
                "date":    r["date"][:10],
                "amount":  amt,
                "purpose": r.get("expense_category") or "",
            })

        # Детализация разметки по месяцам
        marked_detail = fetch_all(supabase, lambda: supabase.table("personal_transactions").select(
            "id, date, amount, description, expense_category"
        ).eq("company_id", COMPANY_ID).eq(
            "category", "Переводы себе (разметка)"
        ).eq("project", "personal").lt("amount", 0).gte("date", date_from))

        marked_items_by_month = defaultdict(list)
        for r in marked_detail:
            m = r["date"][:7]
            marked_items_by_month[m].append({
                "id":     r["id"],
                "desc":   r.get("description") or "",
                "cat":    r.get("expense_category") or "",
                "amount": round(abs(float(r["amount"] or 0))),
            })

        months = []
        for m in sorted(by_month.keys(), reverse=True):
            txs        = by_month[m]
            total      = sum(t["amount"] for t in txs)
            marked_amt = round(marked_by_month.get(m, 0))
            remaining  = round(total - marked_amt)
            months.append({
                "month":        m,
                "total":        round(total),
                "count":        len(txs),
                "marked":       marked_amt,
                "remaining":    remaining,
                "done":         remaining <= 0,
                "transactions": txs,
                "breakdown":    marked_items_by_month.get(m, []),
            })

        return {"months": months}

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


# ── POST /analytics/obligation-payment ────────────────────────
@router.post("/obligation-payment", summary="Добавить платёж по обязательству")
async def add_obligation_payment(body: dict = Body(...)):
    try:
        from app.database import supabase
        result = supabase.table("obligation_payments").insert({
            "company_id":    COMPANY_ID,
            "obligation_id": body["obligation_id"],
            "amount":        body["amount"],
            "payment_date":  body["payment_date"],
            "notes":         body.get("notes", ""),
            "source":        body.get("source", "manual"),
        }).execute()
        return {"ok": True, "payment": result.data[0] if result.data else {}}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── POST /analytics/self-transfer-breakdown ───────────────────
@router.post("/self-transfer-breakdown", summary="Разметка перевода себе")
async def self_transfer_breakdown(body: dict = Body(...)):
    try:
        from app.database import supabase
        import calendar as _cal

        month = body["month"]  # "2026-05"
        items = body["items"]  # [{amount, desc, cat}, ...]
        y, m  = map(int, month.split("-"))
        last_day = _cal.monthrange(y, m)[1]

        rows = []
        for item in items:
            amt  = float(item["amount"] or 0)
            desc = item.get("desc") or ""
            cat  = item.get("cat") or "other"
            if amt <= 0:
                continue
            rows.append({
                "company_id":       COMPANY_ID,
                "date":             f"{month}-{last_day:02d}",
                "amount":           -amt,
                "description":      desc,
                "expense_category": cat,
                "project":          "personal",
                "category":         "Переводы себе (разметка)",
            })

        if rows:
            supabase.table("personal_transactions").insert(rows).execute()

        return {"ok": True, "created": len(rows)}

    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}


# ══════════════════════════════════════════════════════════════
# ПРОДАЖИ ТОВАРОВ
# ══════════════════════════════════════════════════════════════

STAFF_LIST = [
    "Александра", "Анастасия", "Анна", "Екатерина",
    "Марина", "Мария", "Светлана", "София", "Татьяна"
]

# ── DELETE /analytics/transactions/{tx_id} ────────────────────
@router.delete("/transactions/{tx_id}", summary="Удалить запись разметки перевода")
async def delete_transaction(tx_id: int):
    try:
        from app.database import supabase
        # Удаляем только записи разметки переводов себе
        result = supabase.table("personal_transactions").delete().eq(
            "id", tx_id
        ).eq("company_id", COMPANY_ID).eq(
            "category", "Переводы себе (разметка)"
        ).execute()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/products", summary="Справочник товаров")
async def get_products():
    try:
        from app.database import supabase
        result = supabase.table("products").select("*").eq(
            "company_id", COMPANY_ID).eq("is_active", True).order("name").execute()
        return {"products": result.data}
    except Exception as e:
        return {"error": str(e)}


@router.post("/products", summary="Добавить товар")
async def add_product(body: dict = Body(...)):
    try:
        from app.database import supabase
        result = supabase.table("products").insert({
            "company_id": COMPANY_ID,
            "name": body["name"],
            "price": body.get("price"),
            "is_active": True,
        }).execute()
        return {"ok": True, "product": result.data[0]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/product-sales", summary="Продажи товаров")
async def get_product_sales(month: str = None, staff: str = None):
    try:
        from app.database import supabase
        import calendar as _cal

        q = supabase.table("product_sales").select(
            "*, products(name, price)"
        ).eq("company_id", COMPANY_ID)

        if month:
            y, m = map(int, month.split("-"))
            last_day = _cal.monthrange(y, m)[1]
            q = q.gte("date", f"{month}-01").lte("date", f"{month}-{last_day:02d}")
        if staff:
            q = q.eq("staff_name", staff)

        result = q.order("date", desc=True).execute()

        # Итого по мастерам
        from collections import defaultdict
        by_staff = defaultdict(float)
        total = 0.0
        for r in result.data:
            by_staff[r["staff_name"]] += float(r["amount"] or 0)
            total += float(r["amount"] or 0)

        bonuses = {s: round(v * 0.1) for s, v in by_staff.items()}

        return {
            "rows": result.data,
            "total": round(total),
            "by_staff": dict(by_staff),
            "bonuses": bonuses,
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


@router.post("/product-sales", summary="Добавить продажу")
async def add_product_sale(body: dict = Body(...)):
    try:
        from app.database import supabase
        result = supabase.table("product_sales").insert({
            "company_id": COMPANY_ID,
            "date":       body["date"],
            "staff_name": body["staff_name"],
            "product_id": body.get("product_id"),
            "quantity":   body.get("quantity", 1),
            "amount":     body["amount"],
            "account":    body.get("account", "cash"),
            "notes":      body.get("notes", ""),
        }).execute()
        return {"ok": True, "sale": result.data[0]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.delete("/product-sales/{sale_id}", summary="Удалить продажу")
async def delete_product_sale(sale_id: int):
    try:
        from app.database import supabase
        supabase.table("product_sales").delete().eq("id", sale_id).execute()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
