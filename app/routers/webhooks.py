from fastapi import APIRouter, Request
from app.database import deactivate_salon
import json
import os
import logging
import httpx

router = APIRouter(prefix="/webhook", tags=["Вебхуки YCLIENTS"])


async def _forward_to_asya(body: dict):
    """Проброс события Yclients в Асю (триггерные сообщения). No-op, если ASYA_TRIGGERS_URL не задан."""
    url = os.getenv("ASYA_TRIGGERS_URL", "").strip()
    if not url:
        return
    secret = os.getenv("ASYA_TRIGGERS_SECRET", "").strip()
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            await client.post(url, params={"secret": secret} if secret else None, json=body)
    except Exception as e:
        logging.warning(f"[asya] forward failed: {e}")


@router.post(
    "/yclients",
    summary="Входящие события",
    description="YCLIENTS отправляет сюда события в реальном времени — новые записи, изменения, отмены. В будущем будет использоваться для мгновенного обновления данных без синхронизации."
)
async def webhook_yclients(request: Request):
    body = await request.json()
    print("=== Webhook ===", json.dumps(body, ensure_ascii=False))

    resource = body.get("resource")
    status = body.get("status")
    data = body.get("data", {})

    # Проброс в Асю — на все события записи (create/edit/delete). Ася сама решит, что делать.
    if resource == "record":
        await _forward_to_asya(body)

    if resource != "record":
        return {"status": "ok"}

    record_id = data.get("id")
    if not record_id:
        return {"status": "ok"}

    from app.database import supabase
    from datetime import datetime

    # Ищем бронь в Lovi по yclients_record_id
    res = supabase.table("bookings").select("*")        .eq("yclients_record_id", record_id).execute()
    if not res.data:
        return {"status": "ok"}

    booking = res.data[0]

    if status == "edit":
        # Салон перенёс запись
        new_dt = data.get("datetime")  # unix timestamp
        new_staff_id = (data.get("staff") or {}).get("id")
        update = {"status": "rescheduled"}
        if new_dt:
            from datetime import timezone
            update["datetime"] = datetime.fromtimestamp(new_dt, tz=timezone.utc).isoformat()
        if new_staff_id:
            update["master_id"] = new_staff_id
        supabase.table("bookings").update(update).eq("id", booking["id"]).execute()

        # Email клиенту
        try:
            import resend as _resend, os
            from app.emails.utils import render_template
            _resend.api_key = os.getenv("RESEND_API_KEY")
            if booking.get("client_email"):
                html = render_template(
                    template="booking_confirmed",
                    subject="Ваша запись перенесена",
                    email=booking["client_email"],
                    client_name=booking.get("client_name", ""),
                    service_title=booking.get("service_title", ""),
                    datetime=update.get("datetime", booking.get("datetime", "")),
                )
                _resend.Emails.send({
                    "from": "«Лови» <noreply@lovi.today>",
                    "to": booking["client_email"],
                    "subject": "Ваша запись перенесена салоном",
                    "html": html,
                })
        except Exception as e:
            import logging
            logging.error(f"webhook edit email error: {e}")

    elif status == "delete":
        # Салон отменил запись
        supabase.table("bookings").update({
            "status": "cancelled_by_salon"
        }).eq("id", booking["id"]).execute()

        # Email клиенту
        try:
            import resend as _resend, os
            from app.emails.utils import render_template
            _resend.api_key = os.getenv("RESEND_API_KEY")
            if booking.get("client_email"):
                html = render_template(
                    template="booking_cancelled",
                    subject="Ваша запись отменена",
                    email=booking["client_email"],
                    client_name=booking.get("client_name", ""),
                    service_title=booking.get("service_title", ""),
                    datetime=booking.get("datetime", ""),
                )
                _resend.Emails.send({
                    "from": "«Лови» <noreply@lovi.today>",
                    "to": booking["client_email"],
                    "subject": "Запись отменена салоном — возврат средств",
                    "html": html,
                })
        except Exception as e:
            import logging
            logging.error(f"webhook delete email error: {e}")

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

@router.post(
    "/lovi/disconnect",
    summary="Отключение Lovi приложения",
    description="YCLIENTS отправляет сюда уведомление когда салон отключает приложение Lovi из маркетплейса."
)
async def webhook_lovi_disconnect(request: Request):
    body = await request.json()
    company_id = body.get("company_id")
    print(f"=== Lovi Disconnect: компания {company_id} ===")
    if company_id:
        await deactivate_salon(company_id)
    return {"status": "ok"}


@router.get("/lovi/disconnect")
async def webhook_lovi_disconnect_get():
    return {"status": "ok", "info": "This endpoint accepts POST requests from YCLIENTS"}
