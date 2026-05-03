import { useEffect, useRef, useState } from "react";
import { T, BackBtn } from "../theme";

const CHECKOUT_JS_URL = "https://static.yoomoney.ru/checkout-js/v1/checkout.js";
const SHOP_ID = 1348088;
const API = import.meta.env.DEV ? "http://localhost:8000" : "https://insalon.onrender.com";

const C = {
  t1: "#e8e0d4",
  t2: "#9e9a94",
  t3: "#5a5a54",
  font: "'Outfit', sans-serif",
};

export default function Payment({ bookingId, booking, onSuccess, back }) {
  console.log("[Payment] mount bookingId=", bookingId, "booking=", booking?.service?.title);
  const checkoutRef = useRef(null);
  const [scriptReady, setScriptReady] = useState(false);
  const [fields, setFields] = useState({ number: "", month: "", year: "", cvc: "" });
  const [errors, setErrors] = useState({});
  const [phase, setPhase] = useState("idle"); // idle | processing | error | done
  const [globalError, setGlobalError] = useState(null);

  const totalAmount = (booking.service?.price_min || 0) +
    (booking.extras || []).reduce((sum, e) => sum + (e.price_min || 0), 0);

  useEffect(() => {
    if (window.YooMoneyCheckout) { initCheckout(); return; }
    const script = document.createElement("script");
    script.src = CHECKOUT_JS_URL;
    script.onload = initCheckout;
    script.onerror = () => setGlobalError("Не удалось загрузить форму оплаты");
    document.head.appendChild(script);
  }, []);

  function initCheckout() {
    try {
      checkoutRef.current = window.YooMoneyCheckout(SHOP_ID);
      setScriptReady(true);
    } catch (e) {
      setGlobalError("Ошибка инициализации: " + (e?.message || e));
    }
  }

  const set = (field) => (e) => {
    let v = e.target.value.replace(/\D/g, "");
    if (field === "number") v = v.slice(0, 16);
    if (field === "month") v = v.slice(0, 2);
    if (field === "year")  v = v.slice(0, 2);
    if (field === "cvc")   v = v.slice(0, 4);
    setFields(prev => ({ ...prev, [field]: v }));
    setErrors(prev => ({ ...prev, [field]: null }));
  };

  // Форматирование номера карты 4-4-4-4
  const displayNumber = fields.number.replace(/(.{4})/g, "$1 ").trim();

  async function handlePay() {
    if (!checkoutRef.current) return;
    setPhase("processing");
    setGlobalError(null);
    setErrors({});

    const res = await checkoutRef.current.tokenize({
      number: fields.number,
      cvc: fields.cvc,
      month: fields.month,
      year: fields.year,
    });

    if (res.status === "error") {
      if (res.error.type === "validation_error") {
        const errs = {};
        (res.error.params || []).forEach(p => {
          if (p.code.includes("number")) errs.number = p.message;
          if (p.code.includes("cvc"))    errs.cvc = p.message;
          if (p.code.includes("month") || p.code.includes("expiry")) errs.month = p.message;
          if (p.code.includes("year"))   errs.year = p.message;
        });
        setErrors(errs);
        setPhase("idle");
        return;
      }
      setGlobalError("Ошибка обработки карты. Попробуйте ещё раз.");
      setPhase("idle");
      return;
    }

    const { paymentToken } = res.data.response;

    // Отправляем токен на бэкенд
    try {
      const r = await fetch(`${API}/payments/pay-with-token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          booking_id: bookingId,
          payment_token: paymentToken,
          amount: 2000,
        }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Ошибка платежа");
      if (data.status === "redirect" && data.redirect_url) {
        // 3DS — открываем страницу подтверждения банка
        window.location.href = data.redirect_url;
        return;
      }
      setPhase("done");
      onSuccess();
    } catch (e) {
      setGlobalError(e.message);
      setPhase("idle");
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, paddingBottom: 100 }}>

      {/* Итог */}
      <div style={{ background: T.s1, border: `1px solid ${T.s2}`, borderRadius: 12, padding: "14px 16px", display: "flex", flexDirection: "column", gap: 8 }}>
        {booking.service && <SummaryRow label={booking.service.title} amount={booking.service.price_min} />}
        {(booking.extras || []).map(e => <SummaryRow key={e.id} label={e.title} amount={e.price_min} dim />)}
        <div style={{ borderTop: `1px solid ${T.s2}`, paddingTop: 8, marginTop: 4, display: "flex", justifyContent: "space-between" }}>
          <span style={{ fontFamily: C.font, fontSize: 13, color: C.t2 }}>Предоплата</span>
          <span style={{ fontFamily: C.font, fontSize: 15, fontWeight: 500, color: T.gold }}>2 000 ₽</span>
        </div>
      </div>

      {/* Форма карты */}
      <div style={{ background: T.s1, border: `1px solid ${T.s2}`, borderRadius: 12, padding: "16px" }}>
        <CardField
          label="Номер карты"
          value={displayNumber}
          onChange={set("number")}
          placeholder="0000 0000 0000 0000"
          inputMode="numeric"
          error={errors.number}
        />
        <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
          <div style={{ flex: 1 }}>
            <CardField label="ММ" value={fields.month} onChange={set("month")} placeholder="05" inputMode="numeric" error={errors.month} />
          </div>
          <div style={{ flex: 1 }}>
            <CardField label="ГГ" value={fields.year} onChange={set("year")} placeholder="28" inputMode="numeric" error={errors.year} />
          </div>
          <div style={{ flex: 1 }}>
            <CardField label="CVC" value={fields.cvc} onChange={set("cvc")} placeholder="•••" inputMode="numeric" type="password" error={errors.cvc} />
          </div>
        </div>
      </div>

      {/* Глобальная ошибка */}
      {globalError && (
        <div style={{ background: "#2a1a1a", border: "1px solid #5a2a2a", borderRadius: 10, padding: "12px 14px", fontFamily: C.font, fontSize: 13, color: "#e08080" }}>
          {globalError}
        </div>
      )}

      {/* Безопасность */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, justifyContent: "center", color: C.t3, fontFamily: C.font, fontSize: 11 }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
        Данные карты защищены ЮKassa · PCI DSS
      </div>

      {/* Кнопки */}
      <div style={{ position: "fixed", bottom: 0, left: "50%", transform: "translateX(-50%)", width: "100%", maxWidth: 390, padding: "12px 16px 28px", background: "linear-gradient(to top, #0e0e0c 70%, transparent)", display: "flex", gap: 10, zIndex: 10 }}>
        <BackBtn onClick={back} />
        <button
          onClick={handlePay}
          disabled={phase === "processing" || !scriptReady}
          className="btn-pay"
          style={{
            flex: 1, height: 50, borderRadius: 12, border: "none",
            background: phase === "processing" ? T.greenDim : T.green,
            color: "#fff", fontFamily: C.font, fontSize: 14, fontWeight: 500,
            cursor: phase === "processing" ? "default" : "pointer",
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
          }}
        >
          {phase === "processing"
            ? <><Spinner color="#fff" /> Обработка…</>
            : <>Оплатить 2 000 ₽ <span className="btn-arrow">→</span></>}
        </button>
      </div>
    </div>
  );
}

function CardField({ label, value, onChange, placeholder, inputMode, type = "text", error }) {
  return (
    <div>
      <div style={{ fontFamily: C.font, fontSize: 10, color: C.t3, letterSpacing: "0.06em", marginBottom: 5 }}>{label}</div>
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        inputMode={inputMode}
        type={type}
        className="input-field"
        style={{
          width: "100%", height: 44, borderRadius: 8, border: `1px solid ${error ? "#5a2a2a" : T.s2}`,
          background: "#111110", color: C.t1, fontFamily: C.font, fontSize: 15,
          padding: "0 12px", outline: "none", letterSpacing: type === "password" ? "0.2em" : "0.05em",
        }}
      />
      {error && <div style={{ fontFamily: C.font, fontSize: 11, color: "#e08080", marginTop: 4 }}>{error}</div>}
    </div>
  );
}

function SummaryRow({ label, amount, dim }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
      <span style={{ fontFamily: C.font, fontSize: 13, color: dim ? C.t3 : C.t2, flex: 1 }}>{label}</span>
      <span style={{ fontFamily: C.font, fontSize: 13, color: dim ? C.t3 : C.t1, whiteSpace: "nowrap" }}>{amount?.toLocaleString("ru-RU")} ₽</span>
    </div>
  );
}

function Spinner({ color = C.t3 }) {
  return (
    <div style={{ width: 14, height: 14, border: `2px solid ${color}44`, borderTop: `2px solid ${color}`, borderRadius: "50%", animation: "spin 0.8s linear infinite", flexShrink: 0 }} />
  );
}
