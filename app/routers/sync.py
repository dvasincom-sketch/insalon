from fastapi import APIRouter, BackgroundTasks
from app.yclients import get_records, get_clients, get_staff, get_services, get_service_categories, get_transactions
from app.database import (
    save_records, save_clients, save_staff,
    save_services, save_service_categories, save_transactions, get_salon
)
from datetime import datetime, timedelta
import traceback
import os

router = APIRouter(prefix="/sync", tags=["Синхронизация"])

COMPANY_ID = int(os.getenv("YCLIENTS_COMPANY_ID"))


async def sync_company_data(company_id: int, user_token: str, months: int = 12, date_from: str = None, date_to: str = None):
    """Фоновая задача — загружает записи за N месяцев (months=0 — последние 3 дня)"""
    end_date = date_to or datetime.now().strftime("%Y-%m-%d")
    if date_from:
        start_date = date_from
        print(f"[SYNC] Синхронизация филиала {company_id} с {date_from} по {end_date}")
    elif months == 0:
        start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        print(f"[SYNC] Начинаем синхронизацию филиала {company_id} за последние 3 дня")
    else:
        start_date = (datetime.now() - timedelta(days=30 * months)).strftime("%Y-%m-%d")
        print(f"[SYNC] Начинаем синхронизацию филиала {company_id} за {months} месяцев")

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
            print(f"[SYNC] Страница {page}: записей {len(records)}, meta={data.get('meta')}, keys={list(data.keys())}")
            if not records:
                break
            all_records.extend(records)
            total = data.get("meta", {}).get("total_count", 0)
            print(f"[SYNC] Получено {len(all_records)} из {total}")
            if len(all_records) >= total:
                break
            page += 1

        saved = await save_records(all_records, company_id)
        print(f"[SYNC] Готово! Сохранено {len(saved) if saved else 0} записей")
    except Exception as e:
        print(f"[SYNC ERROR] Филиал {company_id}: {e}")
        print(traceback.format_exc())


async def sync_clients_data(company_id: int, user_token: str):
    """Фоновая задача — загружает клиентов"""
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


async def sync_transactions_data(company_id: int, user_token: str):
    """Фоновая задача — загружает финансовые транзакции за 12 месяцев"""
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
            print(f"[SYNC TRANSACTIONS] Страница {page}: получено {len(items)}")
            if len(items) < 100:
                break
            page += 1

        saved = await save_transactions(all_transactions, company_id)
        print(f"[SYNC TRANSACTIONS] Готово! Сохранено {len(saved) if saved else 0}")
    except Exception as e:
        print(f"[SYNC TRANSACTIONS ERROR] {e}")
        print(traceback.format_exc())


@router.get(
    "/records",
    summary="Синхронизация записей",
    description="Загружает записи клиентов из YCLIENTS. По умолчанию за 12 месяцев, можно указать date_from и date_to."
)
async def sync_records(background_tasks: BackgroundTasks, date_from: str = None, date_to: str = None):
    salon = await get_salon(COMPANY_ID)
    if not salon:
        return {"error": "Салон не найден в базе"}
    background_tasks.add_task(
        sync_company_data,
        company_id=COMPANY_ID,
        user_token=salon["user_token"],
        months=12,
        date_from=date_from,
        date_to=date_to
    )
    return {"status": "started", "message": "Синхронизация записей запущена в фоне"}


@router.get(
    "/records-now",
    summary="Синхронизация записей (синхронная)",
    description="Загружает записи и ждёт завершения. Не засыпает в отличие от фоновой задачи."
)
async def sync_records_now(date_from: str = None, date_to: str = None):
    salon = await get_salon(COMPANY_ID)
    if not salon:
        return {"error": "Салон не найден в базе"}
    await sync_company_data(
        company_id=COMPANY_ID,
        user_token=salon["user_token"],
        months=12,
        date_from=date_from,
        date_to=date_to
    )
    return {"status": "done", "message": f"Синхронизация завершена с {date_from} по {date_to}"}


@router.get(
    "/status",
    summary="Статус последней синхронизации"
)
async def sync_status():
    from app.database import supabase as _supabase
    # Последняя запись в records
    last_record = _supabase.table("records").select(
        "synced_at, date"
    ).eq("company_id", COMPANY_ID).order(
        "synced_at", desc=True
    ).limit(1).execute()

    # Последняя транзакция
    last_transaction = _supabase.table("transactions").select(
        "created_at, date"
    ).eq("company_id", COMPANY_ID).order(
        "created_at", desc=True
    ).limit(1).execute()

    return {
        "last_records_sync": last_record.data[0]["synced_at"] if last_record.data else None,
        "last_records_date": last_record.data[0]["date"] if last_record.data else None,
        "last_transactions_sync": last_transaction.data[0]["created_at"] if last_transaction.data else None,
        "last_transactions_date": last_transaction.data[0]["date"] if last_transaction.data else None,
    }


@router.get(
    "/recent",
    summary="Ежедневная синхронизация",
    description="Records и транзакции за последние 3 дня. Используется в ночном cron."
)
async def sync_recent(background_tasks: BackgroundTasks):
    salon = await get_salon(COMPANY_ID)
    if not salon:
        return {"error": "Салон не найден"}
    token = salon["user_token"]
    background_tasks.add_task(sync_company_data, COMPANY_ID, token, 0)
    background_tasks.add_task(sync_transactions_data, COMPANY_ID, token)
    return {"status": "started", "message": "Ежедневная синхронизация запущена"}


@router.get(
    "/clients",
    summary="Синхронизация клиентов",
    description="Загружает всю клиентскую базу из YCLIENTS и сохраняет в Supabase."
)
async def sync_clients_endpoint(background_tasks: BackgroundTasks):
    salon = await get_salon(COMPANY_ID)
    if not salon:
        return {"error": "Салон не найден"}
    background_tasks.add_task(
        sync_clients_data,
        company_id=COMPANY_ID,
        user_token=salon["user_token"]
    )
    return {"status": "started", "message": "Синхронизация клиентов запущена в фоне"}


@router.get(
    "/all",
    summary="Полная синхронизация",
    description="Загружает сотрудников, услуги и финансовые транзакции за 12 месяцев. Основной эндпоинт для первоначальной загрузки данных."
)
async def sync_all(background_tasks: BackgroundTasks):
    salon = await get_salon(COMPANY_ID)
    if not salon:
        return {"error": "Салон не найден"}

    token = salon["user_token"]

    try:
        staff_data = await get_staff(COMPANY_ID, token)
        if staff_data.get("success"):
            await save_staff(staff_data.get("data", []), COMPANY_ID)
            print(f"[SYNC] Сотрудники: {len(staff_data.get('data', []))}")

        categories_data = await get_service_categories(COMPANY_ID, token)
        if categories_data.get("success"):
            await save_service_categories(categories_data.get("data", []), COMPANY_ID)
            print(f"[SYNC] Категории: {len(categories_data.get('data', []))}")

        services_data = await get_services(COMPANY_ID, token)
        if services_data.get("success"):
            await save_services(services_data.get("data", []), COMPANY_ID)
            print(f"[SYNC] Услуги: {len(services_data.get('data', []))}")
    except Exception as e:
        print(f"[SYNC ALL ERROR] {e}")

    background_tasks.add_task(sync_transactions_data, COMPANY_ID, token)

    return {"status": "started", "message": "Полная синхронизация запущена"}

@router.get(
    "/transactions-now",
    summary="Синхронизация транзакций (синхронная)",
)
async def sync_transactions_now():
    salon = await get_salon(COMPANY_ID)
    if not salon:
        return {"error": "Салон не найден"}
    await sync_transactions_data(COMPANY_ID, salon["user_token"])
    return {"status": "done"}
