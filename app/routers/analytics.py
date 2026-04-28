from fastapi import APIRouter
from app.analytics import (
    get_revenue_by_weeks,
    get_new_vs_returning,
    get_churn_risk,
    get_top_services,
    get_summary
)
import os

router = APIRouter(prefix="/analytics", tags=["Аналитика"])

COMPANY_ID = int(os.getenv("YCLIENTS_COMPANY_ID"))


@router.get(
    "/summary",
    summary="Сводка за месяц",
    description="Возвращает выручку, количество визитов и уникальных клиентов за текущий и прошлый месяц. Используется для главных KPI карточек на дашборде."
)
async def analytics_summary():
    try:
        return await get_summary(COMPANY_ID)
    except Exception as e:
        return {"error": str(e)}


@router.get(
    "/revenue",
    summary="Выручка по неделям",
    description="Возвращает выручку по неделям за последние N недель. Используется для линейного графика на дашборде."
)
async def analytics_revenue(weeks: int = 12):
    try:
        return await get_revenue_by_weeks(COMPANY_ID, weeks)
    except Exception as e:
        return {"error": str(e)}


@router.get(
    "/clients",
    summary="Новые vs повторные клиенты",
    description="Разбивка клиентов по неделям — новые и повторные. Помогает оценить эффективность удержания."
)
async def analytics_clients(weeks: int = 12):
    try:
        return await get_new_vs_returning(COMPANY_ID, weeks)
    except Exception as e:
        return {"error": str(e)}


@router.get(
    "/churn",
    summary="Риск оттока клиентов",
    description="Список клиентов которые не приходили более N дней. Основа для рекомендации 'Позвоните этим клиентам'."
)
async def analytics_churn(days: int = 45):
    try:
        return await get_churn_risk(COMPANY_ID, days)
    except Exception as e:
        return {"error": str(e)}


@router.get(
    "/services",
    summary="Топ услуги по выручке",
    description="Рейтинг услуг по выручке, количеству визитов и среднему чеку за весь период."
)
async def analytics_services():
    try:
        return await get_top_services(COMPANY_ID)
    except Exception as e:
        return {"error": str(e)}