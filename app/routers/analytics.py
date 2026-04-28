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


@router.get("/pl", summary="P&L по месяцам")
async def analytics_pl():
    try:
        from app.database import supabase

        # Загружаем все данные с пагинацией
        transactions_data = fetch_all(supabase, lambda: supabase.table("transactions").select("date, amount, type_title").eq("company_id", COMPANY_ID).gt("amount", 0))

        fitmost_data = fetch_all(supabase, lambda: supabase.table("bank_transactions").select("period, date, amount").eq("company_id", COMPANY_ID).eq("type", "Кредит").ilike("counterparty", "%фитмост%"))

        expenses_data = fetch_all(supabase, lambda: supabase.table("personal_transactions").select("date, amount, expense_category").eq("company_id", COMPANY_ID).lt("amount", 0).not_.in_("expense_category", ["internal", "personal", "transfer_in"]))

        bank_fees_data = fetch_all(supabase, lambda: supabase.table("bank_transactions").select("date, amount").eq("company_id", COMPANY_ID).eq("category", "bank_fee").lt("amount", 0))

        salon_rent_data = fetch_all(supabase, lambda: supabase.table("bank_transactions").select("period, date, amount, description").eq("company_id", COMPANY_ID).eq("category", "salon_rent").lt("amount", 0))

        cosmetics_data = fetch_all(supabase, lambda: supabase.table("bank_transactions").select("date, amount").eq("company_id", COMPANY_ID).eq("category", "cosmetics").lt("amount", 0))

        monthly = defaultdict(lambda: {
            "revenue_services": 0, "revenue_certificates": 0,
            "revenue_abonements": 0, "revenue_fitmost": 0,
            "salary": 0, "rent": 0, "materials": 0,
            "marketing": 0, "credit_card": 0, "it": 0,
            "equipment": 0, "transport": 0,
            "bank_fees": 0, "cosmetics": 0, "other": 0
        })

        for t in transactions_data:
            month = t["date"][:7]
            amount = float(t["amount"] or 0)
            type_title = t.get("type_title", "")
            if "услуг" in type_title.lower():
                monthly[month]["revenue_services"] += amount
            elif "сертификат" in type_title.lower():
                monthly[month]["revenue_certificates"] += amount
            elif "абонемент" in type_title.lower():
                monthly[month]["revenue_abonements"] += amount

        for f in fitmost_data:
            period = f.get("period") or f["date"]
            month = period[:7]
            monthly[month]["revenue_fitmost"] += float(f["amount"] or 0)

        known_cats = ["salary", "rent", "materials", "marketing", "credit_card", "it", "equipment", "transport"]
        for e in expenses_data:
            month = e["date"][:7]
            cat = e["expense_category"]
            amount = abs(float(e["amount"] or 0))
            if cat in known_cats:
                monthly[month][cat] += amount
            else:
                monthly[month]["other"] += amount

        for b in bank_fees_data:
            month = b["date"][:7]
            monthly[month]["bank_fees"] += abs(float(b["amount"] or 0))

        for c in cosmetics_data:
            month = c["date"][:7]
            monthly[month]["cosmetics"] += abs(float(c["amount"] or 0))

        for r in salon_rent_data:
            period = r.get("period") or r["date"]
            month = period[:7]
            amount = abs(float(r["amount"] or 0))
            if "рекламного" in (r.get("description") or "").lower():
                monthly[month]["marketing"] += amount
            else:
                monthly[month]["rent"] += amount

        result = []
        for month in sorted(monthly.keys()):
            d = monthly[month]
            total_revenue = (
                d["revenue_services"] + d["revenue_certificates"] +
                d["revenue_abonements"] + d["revenue_fitmost"]
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

        return {"months": result}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}
