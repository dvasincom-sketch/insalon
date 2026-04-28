from fastapi import APIRouter, Request
from app.database import deactivate_salon
import json

router = APIRouter(prefix="/webhook", tags=["Вебхуки YCLIENTS"])


@router.post(
    "/yclients",
    summary="Входящие события",
    description="YCLIENTS отправляет сюда события в реальном времени — новые записи, изменения, отмены. В будущем будет использоваться для мгновенного обновления данных без синхронизации."
)
async def webhook_yclients(request: Request):
    body = await request.json()
    print("=== Webhook ===", json.dumps(body, ensure_ascii=False))
    return {"status": "ok"}


@router.post(
    "/disconnect",
    summary="Отключение интеграции",
    description="YCLIENTS отправляет сюда уведомление когда владелец салона отключает интеграцию. Деактивируем салон в базе."
)
async def webhook_disconnect(request: Request):
    body = await request.json()
    company_id = body.get("company_id")
    print(f"=== Disconnect: компания {company_id} ===")
    if company_id:
        await deactivate_salon(company_id)
    return {"status": "ok"}