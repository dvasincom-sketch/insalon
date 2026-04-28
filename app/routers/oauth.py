from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from app.database import save_salon, get_salon
import os
import json
import hashlib
import hmac

router = APIRouter(tags=["OAuth и подключение"])

PARTNER_TOKEN = os.getenv("YCLIENTS_PARTNER_TOKEN", "").strip()
COMPANY_ID = int(os.getenv("YCLIENTS_COMPANY_ID"))


@router.get(
    "/connect",
    summary="Страница подключения",
    description="Редиректит владельца салона на страницу подключения приложения в маркетплейсе YCLIENTS."
)
async def connect():
    return RedirectResponse("https://yclients.com/e/mp_41238_check/")


@router.get(
    "/oauth/callback",
    summary="OAuth callback",
    description="YCLIENTS редиректит сюда после того как владелец подтвердил доступ. Получаем user_token и запускаем синхронизацию данных за 12 месяцев."
)
async def oauth_callback(request: Request, background_tasks: BackgroundTasks):
    from app.routers.sync import sync_company_data
    params = dict(request.query_params)
    print("=== OAuth callback ===")
    print(json.dumps(params, ensure_ascii=False, indent=2))

    user_token = params.get("user_token") or params.get("token")
    company_id = params.get("company_id")
    user_data_raw = params.get("user_data", "{}")

    try:
        user_data = json.loads(user_data_raw)
    except:
        user_data = {}

    salon_name = user_data.get("salon_name", "")
    user_phone = user_data.get("phone", "")

    if not user_token or not company_id:
        return HTMLResponse(f"""
            <h2>Параметры получены:</h2>
            <pre>{json.dumps(params, ensure_ascii=False, indent=2)}</pre>
        """)

    company_id = int(company_id)

    await save_salon(
        company_id=company_id,
        user_token=user_token,
        company_data={"title": salon_name, "phone": user_phone, "city": ""}
    )

    background_tasks.add_task(
        sync_company_data,
        company_id=company_id,
        user_token=user_token,
        months=12
    )

    return HTMLResponse("""
        <html><head><meta charset="utf-8"></head>
        <body style="font-family:sans-serif;text-align:center;padding:60px">
            <h1 style="color:#2ecc71">✅ Insalon успешно подключён!</h1>
            <p>Мы уже загружаем данные вашего салона за последний год.</p>
            <p>Через несколько минут аналитика будет готова.</p>
        </body></html>
    """)


@router.get(
    "/auth",
    summary="Получить user_token",
    description="Получает user_token по логину и паролю от YCLIENTS. Используется только для тестирования — в продакшне токен приходит через OAuth callback."
)
async def auth(login: str, password: str):
    from app.yclients import get_user_token
    try:
        token = await get_user_token(login, password)
        return {"user_token": token}
    except Exception as e:
        return {"error": str(e)}