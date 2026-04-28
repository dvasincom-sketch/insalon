from app.database import supabase
from datetime import datetime, timedelta


async def get_revenue_by_weeks(company_id: int, weeks: int = 12):
    """Выручка по неделям"""
    start_date = (datetime.now() - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
    
    result = supabase.table("transactions").select(
        "date, amount"
    ).eq("company_id", company_id).gte("date", start_date).execute()
    
    transactions = result.data
    
    # Группируем по неделям
    weekly = {}
    for t in transactions:
        date = datetime.fromisoformat(t["date"][:10])
        week_start = date - timedelta(days=date.weekday())
        week_key = week_start.strftime("%Y-%m-%d")
        weekly[week_key] = weekly.get(week_key, 0) + float(t["amount"])
    
    # Сортируем
    sorted_weeks = sorted(weekly.items())
    
    return {
        "labels": [w[0] for w in sorted_weeks],
        "revenue": [round(w[1]) for w in sorted_weeks]
    }


async def get_new_vs_returning(company_id: int, weeks: int = 12):
    """Новые vs повторные клиенты по неделям"""
    start_date = (datetime.now() - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
    
    result = supabase.table("records").select(
        "date, client_id"
    ).eq("company_id", company_id).gte("date", start_date).eq("attendance", 1).execute()
    
    records = result.data
    
    # Находим первый визит каждого клиента
    first_visits = {}
    for r in records:
        if r["client_id"] and r["client_id"] not in first_visits:
            first_visits[r["client_id"]] = r["date"][:10]
    
    # Группируем по неделям
    weekly_new = {}
    weekly_returning = {}
    
    for r in records:
        if not r["client_id"]:
            continue
        date = datetime.fromisoformat(r["date"][:10])
        week_start = date - timedelta(days=date.weekday())
        week_key = week_start.strftime("%Y-%m-%d")
        
        is_new = first_visits.get(r["client_id"]) == r["date"][:10]
        
        if is_new:
            weekly_new[week_key] = weekly_new.get(week_key, 0) + 1
        else:
            weekly_returning[week_key] = weekly_returning.get(week_key, 0) + 1
    
    all_weeks = sorted(set(list(weekly_new.keys()) + list(weekly_returning.keys())))
    
    return {
        "labels": all_weeks,
        "new": [weekly_new.get(w, 0) for w in all_weeks],
        "returning": [weekly_returning.get(w, 0) for w in all_weeks]
    }


async def get_churn_risk(company_id: int, days: int = 45):
    """Клиенты под риском оттока — не приходили N дней"""
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    result = supabase.table("records").select(
        "client_id, client_name, client_phone, date"
    ).eq("company_id", company_id).eq("attendance", 1).order(
        "date", desc=True
    ).execute()
    
    records = result.data
    
    # Последний визит каждого клиента
    last_visits = {}
    for r in records:
        if not r["client_id"]:
            continue
        if r["client_id"] not in last_visits:
            last_visits[r["client_id"]] = {
                "client_id": r["client_id"],
                "name": r["client_name"],
                "phone": r["client_phone"],
                "last_visit": r["date"][:10]
            }
    
    # Фильтруем тех кто не приходил N дней
    at_risk = [
        v for v in last_visits.values()
        if v["last_visit"] < cutoff_date
    ]
    
    # Сортируем по дате последнего визита
    at_risk.sort(key=lambda x: x["last_visit"])
    
    return {
        "count": len(at_risk),
        "days_threshold": days,
        "clients": at_risk[:50]  # Топ 50 самых давних
    }


async def get_top_services(company_id: int, limit: int = 10):
    """Топ услуги по выручке"""
    result = supabase.table("records").select(
        "service_title, service_cost"
    ).eq("company_id", company_id).eq("attendance", 1).execute()
    
    records = result.data
    
    services = {}
    for r in records:
        title = r["service_title"]
        if not title:
            continue
        if title not in services:
            services[title] = {"revenue": 0, "count": 0}
        services[title]["revenue"] += r["service_cost"] or 0
        services[title]["count"] += 1
    
    sorted_services = sorted(
        services.items(),
        key=lambda x: x[1]["revenue"],
        reverse=True
    )[:limit]
    
    return {
        "services": [
            {
                "title": s[0],
                "revenue": s[1]["revenue"],
                "count": s[1]["count"],
                "avg_check": round(s[1]["revenue"] / s[1]["count"]) if s[1]["count"] > 0 else 0
            }
            for s in sorted_services
        ]
    }


async def get_summary(company_id: int):
    """Сводка за текущий и прошлый месяц"""
    now = datetime.now()
    
    # Текущий месяц
    current_start = now.replace(day=1).strftime("%Y-%m-%d")
    
    # Прошлый месяц
    last_month = now.replace(day=1) - timedelta(days=1)
    prev_start = last_month.replace(day=1).strftime("%Y-%m-%d")
    prev_end = last_month.strftime("%Y-%m-%d")
    
    # Выручка текущего месяца
    current_revenue = supabase.table("transactions").select(
        "amount"
    ).eq("company_id", company_id).gte("date", current_start).execute()
    
    # Выручка прошлого месяца
    prev_revenue = supabase.table("transactions").select(
        "amount"
    ).eq("company_id", company_id).gte("date", prev_start).lte("date", prev_end).execute()
    
    # Записи текущего месяца
    current_records = supabase.table("records").select(
        "id, client_id"
    ).eq("company_id", company_id).gte("date", current_start).eq("attendance", 1).execute()
    
    current_rev = sum(float(t["amount"]) for t in current_revenue.data)
    prev_rev = sum(float(t["amount"]) for t in prev_revenue.data)
    
    growth = round((current_rev - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0
    
    return {
        "current_month_revenue": round(current_rev),
        "prev_month_revenue": round(prev_rev),
        "revenue_growth": growth,
        "current_month_visits": len(current_records.data),
        "unique_clients": len(set(r["client_id"] for r in current_records.data if r["client_id"]))
    }