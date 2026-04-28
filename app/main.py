from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
import os
import json
import traceback
import hashlib
import hmac
from datetime import datetime, timedelta
from dotenv import load_dotenv
from app.yclients import get_records, get_user_token, get_clients, get_staff, get_services, get_transactions
from app.database import save_records, get_records_by_company, save_salon, get_all_salons, save_clients, get_salon, save_staff, save_services, save_transactions
load_dotenv()

app = FastAPI(title="Insalon API")

PARTNER_TOKEN = os.getenv("YCLIENTS_PARTNER_TOKEN", "").strip()
USER_TOKEN = os.getenv("YCLIENTS_USER_TOKEN", "").strip()
COMPANY_ID = int(os.getenv("YCLIENTS_COMPANY_ID"))


# ============ ФОНОВАЯ СИНХРОНИЗАЦИЯ ============

async def sync_clients_data(company_id: int, user_token: str):
    print(f"[SYNC CLIENTS] Начинаем загрузку клиентов филиала {company_id}")
    try:
        all_clients = []
        page = 1
        while True:
            data = await get_clients(
                company_id=company_id,
                user_token=user_token,
                page=page
            )
            clients = data.get("data", [])
            if not clients:
                break
            all_clients.extend(clients)
            total = data.get("meta", {}).get("total_count", 0)
            print(f"[SYNC CLIENTS] Получено {len(all_clients)} из {total}")
            if len(all_clients) >= total:
                break
            page += 1

        saved = await save_clients(all_clients, company_id)
        print(f"[SYNC CLIENTS] Готово! Сохранено {len(saved) if saved else 0} клиентов")
    except Exception as e:
        print(f"[SYNC CLIENTS ERROR] {e}")

async def sync_company_data(company_id: int, user_token: str, months: int = 12):
    """
    Фоновая задача — загружает данные за N месяцев.
    Запускается автоматически после подключения салона.
    """
    print(f"[SYNC] Начинаем синхронизацию филиала {company_id} за {months} месяцев")

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30 * months)).strftime("%Y-%m-%d")

    try:
        all_records = []
        page = 1

        while True:
            print(f"[SYNC] Загружаем страницу {page}...")
            data = await get_records(
                company_id=company_id,
                user_token=user_token,
                start_date=start_date,
                end_date=end_date,
                page=page
            )

            records = data.get("data", [])
            if not records:
                break

            all_records.extend(records)
            total = data.get("meta", {}).get("total_count", 0)
            print(f"[SYNC] Получено {len(all_records)} из {total}")

            if len(all_records) >= total:
                break

            page += 1

        # Сохраняем в Supabase
        saved = await save_records(all_records, company_id)
        print(f"[SYNC] Готово! Сохранено {len(saved) if saved else 0} записей")

    except Exception as e:
        print(f"[SYNC ERROR] Филиал {company_id}: {e}")
        print(traceback.format_exc())


# ============ ЭНДПОИНТЫ ============

@app.get("/")
async def root():
    return {"status": "ok", "project": "Insalon"}


@app.get("/oauth/callback")
async def oauth_callback(request: Request, background_tasks: BackgroundTasks):
    params = dict(request.query_params)
    print("=== OAuth callback params ===")
    print(json.dumps(params, ensure_ascii=False, indent=2))

    # Получаем данные которые прислал YCLIENTS
    user_token = params.get("user_token")
    company_id = params.get("company_id")
    user_data_raw = params.get("user_data", "{}")
    user_data_sign = params.get("user_data_sign", "")

    # Проверяем подпись если есть
    if user_data_sign:
        expected_sign = hmac.new(
            PARTNER_TOKEN.encode(),
            user_data_raw.encode(),
            hashlib.sha256
        ).hexdigest()
        if expected_sign != user_data_sign:
            print("⚠️ Подпись не совпадает!")

    # Парсим данные пользователя
    try:
        user_data = json.loads(user_data_raw)
    except:
        user_data = {}

    salon_name = user_data.get("salon_name", "")
    user_phone = user_data.get("phone", "")

    if not user_token or not company_id:
        return HTMLResponse(f"""
            <h2>⚠️ Не получены обязательные параметры</h2>
            <pre>{json.dumps(params, ensure_ascii=False, indent=2)}</pre>
        """)

    company_id = int(company_id)

    # Сохраняем салон в БД
    await save_salon(
        company_id=company_id,
        user_token=user_token,
        company_data={"title": salon_name, "phone": user_phone, "city": ""}
    )

    # Запускаем фоновую синхронизацию за 12 месяцев
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


@app.post("/webhook/yclients")
async def webhook_yclients(request: Request):
    """Входящие события от YCLIENTS"""
    body = await request.json()
    print("=== Webhook ===", json.dumps(body, ensure_ascii=False))
    return {"status": "ok"}


@app.post("/webhook/disconnect")
async def webhook_disconnect(request: Request, background_tasks: BackgroundTasks):
    """Салон отключил интеграцию"""
    body = await request.json()
    company_id = body.get("company_id")
    print(f"=== Disconnect: компания {company_id} ===")
    return {"status": "ok"}


@app.get("/sync")
async def sync_manual(background_tasks: BackgroundTasks):
    """Ручная синхронизация для тестирования"""
    background_tasks.add_task(
        sync_company_data,
        company_id=COMPANY_ID,
        user_token=USER_TOKEN,
        months=12
    )
    return {
        "status": "started",
        "message": "Sync started in background. Check logs."
    }

@app.get("/sync/clients")
async def sync_clients_manual(background_tasks: BackgroundTasks):
    from app.database import get_salon
    salon = await get_salon(COMPANY_ID)
    background_tasks.add_task(
        sync_clients_data,
        company_id=COMPANY_ID,
        user_token=salon["user_token"]
    )
    return {"status": "started", "message": "Clients sync started"}

@app.get("/salons")
async def salons():
    """Список подключённых салонов"""
    try:
        data = await get_all_salons()
        return {"count": len(data), "salons": data}
    except Exception as e:
        return {"error": str(e)}


@app.get("/db/records")
async def db_records():
    """Записи из Supabase"""
    try:
        records = await get_records_by_company(COMPANY_ID)
        return {"count": len(records), "records": records}
    except Exception as e:
        return {"error": str(e)}

@app.get("/sync/all")

async def sync_all(background_tasks: BackgroundTasks):
    try:
        salon = await get_salon(COMPANY_ID)
        if not salon:
            return {"error": "Салон не найден"}

        token = salon["user_token"]
        print(f"[SYNC ALL] Токен: {token[:8]}...")

        staff_data = await get_staff(COMPANY_ID, token)
        print(f"[SYNC ALL] Staff response: {staff_data}")

        if staff_data.get("success"):
            await save_staff(staff_data.get("data", []), COMPANY_ID)
            print(f"[SYNC] Сотрудники: {len(staff_data.get('data', []))}")

        services_data = await get_services(COMPANY_ID, token)
        if services_data.get("success"):
            await save_services(services_data.get("data", []), COMPANY_ID)
            print(f"[SYNC] Услуги: {len(services_data.get('data', []))}")

        background_tasks.add_task(sync_transactions_data, COMPANY_ID, token)

        return {"status": "started", "message": "Sync all started"}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}
    
    salon = await get_salon(COMPANY_ID)
    if not salon:
        return {"error": "Салон не найден"}

    token = salon["user_token"]

    staff_data = await get_staff(COMPANY_ID, token)
    if staff_data.get("success"):
        await save_staff(staff_data.get("data", []), COMPANY_ID)
        print(f"[SYNC] Сотрудники: {len(staff_data.get('data', []))}")

    services_data = await get_services(COMPANY_ID, token)
    if services_data.get("success"):
        await save_services(services_data.get("data", []), COMPANY_ID)
        print(f"[SYNC] Услуги: {len(services_data.get('data', []))}")

    background_tasks.add_task(sync_transactions_data, COMPANY_ID, token)

    return {"status": "started", "message": "Sync all started"}


async def sync_transactions_data(company_id: int, user_token: str):
    from datetime import datetime, timedelta
    print(f"[SYNC TRANSACTIONS] Начинаем загрузку транзакций")
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    try:
        all_transactions = []
        page = 1
        while True:
            data = await get_transactions(
                company_id=company_id,
                user_token=user_token,
                start_date=start_date,
                end_date=end_date,
                page=page
            )
            items = data.get("data", [])
            if not items:
                break
            all_transactions.extend(items)
            print(f"[SYNC TRANSACTIONS] Страница {page}: получено {len(items)} транзакций")
            # Если получили меньше 100 — это последняя страница
            if len(items) < 100:
                break
            page += 1

        saved = await save_transactions(all_transactions, company_id)
        print(f"[SYNC TRANSACTIONS] Готово! Сохранено {len(saved) if saved else 0}")
    except Exception as e:
        print(f"[SYNC TRANSACTIONS ERROR] {e}")
        import traceback
        print(traceback.format_exc())


@app.get("/auth")
async def auth(login: str, password: str):
    """Получить user_token (только для тестирования)"""
    try:
        token = await get_user_token(login, password)
        return {"user_token": token}
    except Exception as e:
        return {"error": str(e)}