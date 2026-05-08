from fastapi import APIRouter, Request, Body, HTTPException
from fastapi.responses import JSONResponse
from app.database import supabase
import os
import uuid

router = APIRouter(prefix="/payments", tags=["Оплата"])

def get_yookassa():
    from yookassa import Configuration, Payment
    Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
    Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    return Payment

def _send_booking_email(template: str, subject: str, booking_id, extra: dict = {}):
    """Вспомогательная функция отправки письма по брони"""
    try:
        from app.emails.utils import render_template
        import resend as _resend
        from datetime import datetime

        booking_res = supabase.table("bookings").select("*").eq("id", booking_id).execute()
        if not booking_res.data:
            return
        b = booking_res.data[0]

        email = b.get("client_email") or ""
        name  = b.get("client_name") or ""
        if not email and b.get("user_id"):
            user_res = supabase.table("users").select("email,name").eq("id", b["user_id"]).execute()
            if user_res.data:
                email = user_res.data[0]["email"]
                name  = name or user_res.data[0]["name"]
        if not email:
            return

        dt = datetime.fromisoformat(b["datetime"].replace("Z", ""))

        kwargs = dict(
            name=name,
            email=email,
            service_title=b.get("service_title", ""),
            date=dt.strftime("%-d %B %Y"),
            time=dt.strftime("%H:%M"),
            duration=f"{round(b.get('duration', 0) / 60)} мин",
            booking_code=b.get("booking_code") or f"LV-{str(booking_id).zfill(5)}",
            total_price=str(b.get("total_price", 0)),
            base_price=str(b.get("base_price", 0)),
            discount_pct=str(b.get("discount_pct", "")),
        )
        kwargs.update(extra)

        _resend.api_key = os.getenv("RESEND_API_KEY")
        html = render_template(template=template, subject=subject, **kwargs)
        _resend.Emails.send({
            "from": "«Лови» <noreply@lovi.today>",
            "to": email,
            "subject": subject,
            "html": html,
        })
        print(f"[EMAIL] {template} → {email}")
    except Exception as e:
        print(f"[EMAIL] Error {template}: {e}")


@router.post("/create")
async def create_payment(data: dict = Body(...)):
    """Создать платёж в ЮKassa"""
    Payment = get_yookassa()
    booking_id = data.get("booking_id")
    amount = data.get("amount", 2000)
    base_url = os.getenv("BOOKING_BASE_URL", "https://insalon.onrender.com")

    payment = Payment.create({
        "amount": {"value": f"{amount}.00", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            "return_url": f"{base_url}/booking/?booking_id={booking_id}"
        },
        "capture": True,
        "description": f"Бронирование #{booking_id} — HeadSPA Beauty",
        "metadata": {"booking_id": booking_id}
    }, uuid.uuid4())

    supabase.table("bookings").update({
        "payment_id": payment.id,
        "status": "waiting_payment"
    }).eq("id", booking_id).execute()

    return {"payment_url": payment.confirmation.confirmation_url, "payment_id": payment.id}


@router.post("/webhook")
async def yookassa_webhook(request: Request):
    """Webhook от ЮKassa"""
    body = await request.json()
    event = body.get("event")
    obj = body.get("object", {})
    metadata = obj.get("metadata", {})
    booking_id = metadata.get("booking_id")

    if not booking_id:
        return JSONResponse({"ok": True})

    if event == "payment.succeeded":
        supabase.table("bookings").update({"status": "confirmed"}).eq("id", booking_id).execute()
        print(f"[PAYMENT] Оплачено booking_id={booking_id}")
        _send_booking_email("booking_confirmed", "Окошко закреплено — «Лови»", booking_id)

        # Создаём запись в YCLIENTS после успешной оплаты
        print(f"[PAYMENT] Начинаем создание записи в YCLIENTS для booking_id={booking_id}")
        try:
            print("[PAYMENT] step 1: получаем booking")
            booking = supabase.table("bookings").select("*").eq("id", booking_id).single().execute().data
            print(f"[PAYMENT] step 2: booking={booking is not None}, company_id={booking.get('company_id') if booking else None}")
            print("[PAYMENT] step 3: получаем salon")
            salon = supabase.table("salons").select("user_token").eq("company_id", booking["company_id"]).single().execute().data
            print(f"[PAYMENT] step 4: salon={salon is not None}, token_len={len(salon.get('user_token','')) if salon else 0}")
            token = salon.get("user_token", "") if salon else ""
            print(f"[PAYMENT] step 5: token={bool(token)}, service_id={booking.get('service_id')}, master_id={booking.get('master_id')}")
            if token and booking.get("service_id") and booking.get("master_id"):
                from app.yclients import create_record, create_client, find_client_by_phone
                import re

                raw_phone = booking.get("client_phone", "")
                normalized = "+" + re.sub(r"\D", "", raw_phone)
                if normalized.startswith("+8"):
                    normalized = "+7" + normalized[2:]

                # Используем системного клиента Lovi
                system_client_id = int(os.getenv("LOVI_SYSTEM_CLIENT_ID", "396205299"))
                source = booking.get("source", "insalon")
                dt_raw = booking.get("datetime", "").replace(" ", "T")
                # Добавляем timezone если нет
                if dt_raw and "+" not in dt_raw and "Z" not in dt_raw:
                    dt = dt_raw + "+03:00"
                else:
                    dt = dt_raw
                # Берём длительность из YCLIENTS
                seance_length = booking.get("duration", 3600)
                try:
                    import httpx as _httpx
                    partner_token = os.getenv("YCLIENTS_PARTNER_TOKEN", "").strip()
                    async with _httpx.AsyncClient(timeout=5) as _client:
                        _r = await _client.get(
                            f"https://api.yclients.com/api/v1/services/{booking['company_id']}/{booking['service_id']}",
                            headers={"Authorization": f"Bearer {partner_token}, User {token}", "Accept": "application/vnd.api.v2+json"}
                        )
                        _svc = _r.json().get("data", {})
                        if _svc.get("duration"):
                            seance_length = _svc["duration"]
                except Exception as e:
                    print(f"[PAYMENT] service duration fetch error: {e}")
                print(f"[PAYMENT] seance_length={seance_length}")
                record_data = {
                    "staff_id": booking["master_id"],
                    "services": [{"id": booking["service_id"]}],
                    "client": {"id": system_client_id},
                    "datetime": dt,
                    "seance_length": seance_length,
                    "comment": f"{'lovi.today' if source == 'lovi' else 'insalon'} | {booking.get('client_name','')} {normalized} | booking_id={booking_id}",
                }
                result = await create_record(booking["company_id"], token, record_data)
                print(f"[PAYMENT] YCLIENTS result: {result}")
                if result and result.get("success"):
                    supabase.table("bookings").update({
                        "yclients_record_id": result["data"]["id"],
                    }).eq("id", booking_id).execute()
                    print(f"[PAYMENT] Запись создана id={result['data']['id']}")
                else:
                    supabase.table("bookings").update({
                        "yclients_sync_error": result.get("meta", {}).get("message", "unknown")
                    }).eq("id", booking_id).execute()
        except Exception as e:
            import traceback
            print(f"[PAYMENT] YCLIENTS exception: {e}")
            print(traceback.format_exc())

    elif event in ("payment.canceled",):
        supabase.table("bookings").update({"status": "cancelled"}).eq("id", booking_id).execute()
        print(f"[PAYMENT] Отменено booking_id={booking_id}")
        _send_booking_email("booking_cancelled", "Бронирование отменено — «Лови»", booking_id)

    return JSONResponse({"ok": True})


@router.post("/create-token")
async def create_payment_token(data: dict):
    """Создаёт платёж в ЮKassa, возвращает confirmation_token для Checkout.js"""
    from yookassa import Configuration, Payment
    Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
    Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

    idempotence_key = str(uuid.uuid4())
    payment = Payment.create({
        "amount": {"value": str(data["amount"]), "currency": "RUB"},
        "confirmation": {"type": "embedded"},
        "capture": True,
        "description": data.get("description", "Запись в HeadSPA"),
        "metadata": {"booking_data": str(data.get("booking_data", {}))}
    }, idempotence_key)

    return {
        "payment_id": payment.id,
        "confirmation_token": payment.confirmation.confirmation_token
    }


@router.post("/confirm-booking")
async def confirm_booking_after_payment(data: dict):
    """После успешной оплаты создаём бронь в YCLIENTS"""
    from yookassa import Configuration, Payment
    Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
    Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

    payment = Payment.find_one(data["payment_id"])
    if payment.status != "succeeded":
        raise HTTPException(status_code=400, detail=f"Payment status: {payment.status}")

    booking_data = data.get("booking_data", {})
    return {
        "status": "confirmed",
        "payment_id": data["payment_id"],
        "booking": booking_data
    }


@router.post("/pay-with-token")
async def pay_with_token(data: dict = Body(...)):
    """Принимает paymentToken от Checkout.js, создаёт платёж в ЮKassa"""
    Payment = get_yookassa()
    booking_id = data.get("booking_id")
    if not booking_id:
        raise HTTPException(status_code=400, detail="booking_id обязателен")
    payment_token = data.get("payment_token")
    amount = data.get("amount", 2000)

    payment = Payment.create({
        "amount": {"value": f"{amount}.00", "currency": "RUB"},
        "payment_method_data": {
            "type": "bank_card",
            "payment_method_token": payment_token,
        },
        "capture": True,
        "description": f"Бронирование #{booking_id} — HeadSPA Beauty",
        "metadata": {"booking_id": str(booking_id)},
        "confirmation": {
            "type": "redirect",
            "return_url": os.getenv("BOOKING_BASE_URL", "https://insalon.onrender.com") + "/booking/?booking_id=" + str(booking_id)
        },
    }, str(uuid.uuid4()))

    supabase.table("bookings").update({
        "payment_id": payment.id,
        "status": "waiting_payment"
    }).eq("id", booking_id).execute()

    if payment.status == "pending" and payment.confirmation:
        return {"status": "redirect", "redirect_url": payment.confirmation.confirmation_url}

    return {"status": payment.status, "payment_id": payment.id}
