from fastapi import APIRouter, Request, Body
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

@router.post("/create")
async def create_payment(data: dict = Body(...)):
    """Создать платёж в ЮKassa"""
    Payment = get_yookassa()
    booking_id = data.get("booking_id")
    amount = data.get("amount", 2000)
    base_url = os.getenv("BOOKING_BASE_URL", "https://insalon.onrender.com")

    payment = Payment.create({
        "amount": {
            "value": f"{amount}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"{base_url}/booking/?booking_id={booking_id}"
        },
        "capture": True,
        "description": f"Бронирование #{booking_id} — HeadSPA Beauty",
        "metadata": {
            "booking_id": booking_id
        }
    }, uuid.uuid4())

    # Сохраняем payment_id в bookings
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
    payment_id = obj.get("id")
    metadata = obj.get("metadata", {})
    booking_id = metadata.get("booking_id")

    if not booking_id:
        return JSONResponse({"ok": True})

    if event == "payment.succeeded":
        supabase.table("bookings").update({
            "status": "paid"
        }).eq("id", booking_id).execute()
        print(f"[PAYMENT] Оплачено booking_id={booking_id}")

    elif event in ("payment.canceled",):
        supabase.table("bookings").update({
            "status": "cancelled"
        }).eq("id", booking_id).execute()
        print(f"[PAYMENT] Отменено booking_id={booking_id}")

    return JSONResponse({"ok": True})
