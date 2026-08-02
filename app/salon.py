"""Единый контекст салона (мультиарендность).

Заменяет продублированную в роутерах константу COMPANY_ID и хардкод 1166484.
- DEFAULT_COMPANY_ID — дефолтный салон (переходный период, поведение не меняется);
- current_salon(request) — FastAPI-зависимость: резолвит салон из запроса
  (JWT салона -> явный company_id в query/header -> дефолт; Host/домен добавим позже).

Названа current_salon, а не get_salon, чтобы не конфликтовать с database.get_salon().
"""
import os
from fastapi import Request
from app.database import supabase

DEFAULT_COMPANY_ID = int(os.getenv("YCLIENTS_COMPANY_ID", "1166484"))


def get_salon_row(company_id: int):
    res = supabase.table("salons").select("*").eq("company_id", company_id).limit(1).execute()
    return res.data[0] if res.data else None


def get_user_token(company_id: int) -> str:
    row = get_salon_row(company_id)
    return (row or {}).get("user_token", "") or ""


def _company_id_from_jwt(authorization):
    if not authorization:
        return None
    try:
        from jose import jwt as jose_jwt
        token = authorization.replace("Bearer ", "")
        secret = os.getenv("JWT_SECRET", "lovi-secret-change-in-prod")
        payload = jose_jwt.decode(token, secret, algorithms=["HS256"])
        return int(payload["company_id"])
    except Exception:
        return None


def resolve_company_id(request: Request) -> int:
    # 1) JWT салона (кабинет/CRM)
    cid = _company_id_from_jwt(request.headers.get("authorization"))
    if cid:
        return cid
    # 2) явный company_id (query или X-Salon-Id) — виджет/служебные вызовы
    raw = request.query_params.get("company_id") or request.headers.get("x-salon-id")
    if raw and str(raw).isdigit():
        return int(raw)
    # 3) TODO: Host -> salons.domain (свой домен салона)
    # 4) дефолтный салон (переходный период)
    return DEFAULT_COMPANY_ID


async def current_salon(request: Request) -> dict:
    company_id = resolve_company_id(request)
    row = get_salon_row(company_id)
    if row is None:
        row = {"company_id": company_id, "user_token": ""}
    return row
