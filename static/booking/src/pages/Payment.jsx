import { useEffect, useRef, useState } from "react";
import { T, s, Wordmark, Ambient } from "../theme";

export default function Payment({ booking, confirmationToken, bookingId, onSuccess }) {
  const containerRef = useRef(null);
  const [error, setError] = useState(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    // Загружаем ЮKassa SDK
    const script = document.createElement("script");
    script.src = "https://yookassa.ru/checkout-widget/v1/checkout-widget.js";
    script.onload = () => setLoaded(true);
    script.onerror = () => setError("Не удалось загрузить форму оплаты");
    document.head.appendChild(script);
    return () => document.head.removeChild(script);
  }, []);

  useEffect(() => {
    if (!loaded || !confirmationToken || !containerRef.current) return;

    const checkout = new window.YooMoneyCheckoutWidget({
      confirmation_token: confirmationToken,
      return_url: `${window.location.origin}/booking/?booking_id=${bookingId}`,
      customization: {
        colors: {
          controlPrimary: T.gold,
          controlPrimaryContent: T.bg,
          background: { enabled: true, value: T.s2 },
          border: { enabled: true, value: T.border },
          text: { enabled: true, value: T.text },
        },
        payment_methods: ["bank_card"],
      },
      error_callback: (err) => {
        console.error("ЮKassa error:", err);
        setError("Ошибка при оплате. Попробуйте ещё раз.");
      },
    });

    checkout.render("yookassa-container");

    return () => checkout.destroy();
  }, [loaded, confirmationToken]);

  return (
    <div style={{ paddingBottom: 32 }}>
      <div style={{
        background: T.s2, border: `1px solid ${T.border}`,
        borderRadius: 16, padding: "14px 16px", marginBottom: 18,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <span style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300 }}>
            Предоплата за бронирование
          </span>
          <span style={{ fontFamily: T.serif, fontWeight: 300, fontSize: 22, color: T.gold }}>
            2 000 ₽
          </span>
        </div>
      </div>

      {error && (
        <div style={{
          background: "rgba(138,48,48,0.1)", border: "1px solid rgba(138,48,48,0.3)",
          borderRadius: 12, padding: "12px 14px", marginBottom: 14,
          fontFamily: T.font, fontSize: 13, color: "#c07070",
        }}>
          {error}
        </div>
      )}

      {!loaded && !error && (
        <div style={{ display: "flex", justifyContent: "center", padding: 32 }}>
          <div style={{
            width: 28, height: 28,
            border: `1px solid ${T.border}`,
            borderTop: `1px solid ${T.gold}`,
            borderRadius: "50%",
            animation: "spin 0.9s linear infinite",
          }} />
        </div>
      )}

      <div
        id="yookassa-container"
        ref={containerRef}
        style={{ borderRadius: 16, overflow: "hidden" }}
      />

      <div style={{
        fontFamily: T.font, fontSize: 11, color: T.textMuted,
        fontWeight: 300, lineHeight: 1.55, marginTop: 14, textAlign: "center",
      }}>
        При отмене менее чем за 24 часа предоплата не возвращается
      </div>
    </div>
  );
}
