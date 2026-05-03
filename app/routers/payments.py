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

@router.post("/create-token")
async def create_payment_token(data: dict):
    """Создаёт платёж в ЮKassa, возвращает confirmation_token для Checkout.js"""
    import uuid
    from yookassa import Configuration, Payment

    Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
    Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

    idempotence_key = str(uuid.uuid4())
    payment = Payment.create({
        "amount": {
            "value": str(data["amount"]),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "embedded"
        },
        "capture": True,
        "description": data.get("description", "Запись в HeadSPA"),
        "metadata": {
            "booking_data": str(data.get("booking_data", {}))
        }
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

    # Проверяем статус платежа
    payment = Payment.find_one(data["payment_id"])
    if payment.status != "succeeded":
        raise HTTPException(status_code=400, detail=f"Payment status: {payment.status}")

    # TODO: создать запись в YCLIENTS через booking.py
    booking_data = data.get("booking_data", {})

    return {
        "status": "confirmed",
        "payment_id": data["payment_id"],
        "booking": booking_data
    }

@router.post("/pay-with-token")
async def pay_with_token(data: dict = Body(...)):
    """Принимает paymentToken от Checkout.js, создаёт платёж в ЮKassa"""
    from fastapi import HTTPException
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
        "confirmation": {"type": "redirect", "return_url": os.getenv("BOOKING_BASE_URL", "https://insalon.onrender.com") + "/booking/?booking_id=" + str(booking_id)},
    }, str(uuid.uuid4()))

    supabase.table("bookings").update({
        "payment_id": payment.id,
        "status": "waiting_payment"
    }).eq("id", booking_id).execute()

    # Если требуется 3DS — возвращаем redirect url
    if payment.status == "pending" and payment.confirmation:
        return {"status": "redirect", "redirect_url": payment.confirmation.confirmation_url}

    return {"status": payment.status, "payment_id": payment.id}

