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
                "category", "salon_rent" if category in ("rent", "salon_rent") else "marketing"
            ).or_(f"date.gte.{date_from},period.gte.{date_from}").or_(
                f"date.lte.{date_to},period.lte.{date_to}"
            ).execute()
            # Фильтруем по периоду
            rows = []
            for t in result.data:
                period = (t.get("period") or t["date"])[:7]
                if period == month:
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
