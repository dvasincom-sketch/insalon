import { useEffect, useRef, useState } from 'react'

const CHECKOUT_JS_URL = 'https://static.yoomoney.ru/checkout-js/v1/checkout.js'
const API_BASE = 'https://insalon.onrender.com'

export default function Payment({ bookingData, amount, onSuccess, onBack }) {
  const checkoutRef = useRef(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [processing, setProcessing] = useState(false)

  useEffect(() => {
    // Загружаем Checkout.js если ещё не загружен
    if (document.querySelector(`script[src="${CHECKOUT_JS_URL}"]`)) {
      initCheckout()
      return
    }
    const script = document.createElement('script')
    script.src = CHECKOUT_JS_URL
    script.onload = initCheckout
    script.onerror = () => setError('Не удалось загрузить форму оплаты')
    document.head.appendChild(script)

    return () => {
      // Cleanup checkout instance
      if (checkoutRef.current) {
        try { checkoutRef.current.destroy() } catch {}
        checkoutRef.current = null
      }
    }
  }, [])

  function initCheckout() {
    try {
      const checkout = new window.YooMoneyCheckoutWidget({
        confirmation_token: null, // получим через бэкенд
        return_url: window.location.href,
        embedded_3ds: true,
        error_callback: (err) => setError(`Ошибка: ${err.error}`),
        complete_callback: async (result) => {
          if (result.status === 'succeeded') {
            await confirmBooking(result)
          }
        }
      })

      checkoutRef.current = checkout
      setLoading(false)
    } catch (e) {
      setError('Ошибка инициализации формы оплаты')
      setLoading(false)
    }
  }

  async function handlePay() {
    setProcessing(true)
    setError(null)

    try {
      // 1. Получаем confirmation_token от нашего бэкенда
      const res = await fetch(`${API_BASE}/payments/create-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: amount,
          description: `Запись в HeadSPA: ${bookingData.service_title}`,
          booking_data: bookingData
        })
      })

      if (!res.ok) throw new Error('Ошибка создания платежа')
      const { confirmation_token, payment_id } = await res.json()

      // 2. Передаём токен в виджет и открываем форму карты
      await checkoutRef.current.setConfirmationToken(confirmation_token)
      checkoutRef.current.render('payment-form')

      // Сохраняем payment_id для подтверждения
      window._pendingPaymentId = payment_id

    } catch (e) {
      setError(e.message || 'Ошибка оплаты')
      setProcessing(false)
    }
  }

  async function confirmBooking(paymentResult) {
    try {
      const res = await fetch(`${API_BASE}/payments/confirm-booking`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          payment_id: window._pendingPaymentId,
          booking_data: bookingData
        })
      })

      if (!res.ok) throw new Error('Ошибка подтверждения брони')
      const data = await res.json()
      onSuccess(data)
    } catch (e) {
      setError('Оплата прошла, но бронь не создана. Позвоните нам.')
      setProcessing(false)
    }
  }

  return (
    <div className="payment-step">
      <h2 className="step-title">Оплата</h2>

      <div className="payment-summary">
        <div className="service-line">
          <span>{bookingData.service_title}</span>
          <strong>{amount.toLocaleString('ru-RU')} ₽</strong>
        </div>
        {bookingData.extras?.length > 0 && bookingData.extras.map(e => (
          <div key={e.id} className="service-line extra">
            <span>{e.title}</span>
            <strong>{e.price.toLocaleString('ru-RU')} ₽</strong>
          </div>
        ))}
      </div>

      {error && (
        <div className="error-banner">{error}</div>
      )}

      {loading && (
        <div className="loading-text">Загрузка формы оплаты...</div>
      )}

      {/* Контейнер для iframe ЮKassa */}
      <div id="payment-form" className="yookassa-form" />

      <div className="step-actions">
        <button className="btn-back" onClick={onBack} disabled={processing}>
          ← Назад
        </button>
        {!processing && !loading && (
          <button className="btn-pay" onClick={handlePay}>
            Оплатить {amount.toLocaleString('ru-RU')} ₽
          </button>
        )}
        {processing && (
          <button className="btn-pay" disabled>
            Обрабатывается...
          </button>
        )}
      </div>
    </div>
  )
}
