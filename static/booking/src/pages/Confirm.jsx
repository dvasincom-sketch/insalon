import { useEffect, useState } from "react";
import { T, s, Wordmark, Ambient } from "../theme";

const API = import.meta.env.DEV ? "http://localhost:8000" : "https://insalon.onrender.com";

function formatDateTime(dt) {
  if (!dt) return dt;
  const [date, time] = dt.split(" ");
  const d = new Date(date + "T" + time);
  return d.toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" }) + ", " +
    d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

function Timer({ seconds }) {
  const [left, setLeft] = useState(seconds);
  useEffect(() => {
    if (left <= 0) return;
    const t = setTimeout(() => setLeft(l => l - 1), 1000);
    return () => clearTimeout(t);
  }, [left]);
  const m = String(Math.floor(left / 60)).padStart(2, "0");
  const s = String(left % 60).padStart(2, "0");
  return <span style={{ color: left < 300 ? "#e08080" : T.gold, fontVariantNumeric: "tabular-nums" }}>{m}:{s}</span>;
}

export default function Confirm({ booking, paymentUrl, bookingId }) {
  const rows = [
    { label: "Услуга",        value: booking.service?.title,                    accent: true },
    { label: "Дата и время",  value: formatDateTime(booking.datetime) },
    { label: "Длительность",  value: `${Math.floor((booking.totalDuration || booking.service?.seance_length || 0) / 60)} мин` },
    { label: "Мастер",        value: booking.master?.name || "Любой свободный" },
    booking.extras?.length > 0 && { label: "Допы", value: booking.extras.map(e => e.title).join(", ") },
  ].filter(Boolean);

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,300;0,400;1,300&family=Outfit:wght@300;400;500&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { background: ${T.bg}; min-height: 100dvh; }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes spin { to { transform: rotate(360deg); } }
        .btn-pay:hover { background: #6aaa78 !important; }
      `}</style>

      <div style={{ ...s.phone, padding: "0 0 32px" }}>
        <Ambient />

        <div style={{ padding: "20px 24px 0", flexShrink: 0, position: "relative", zIndex: 2 }}>
          <Wordmark />
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "0 24px", zIndex: 2, scrollbarWidth: "none", animation: "fadeUp 0.4s cubic-bezier(0.22,1,0.36,1) both" }}>

          {/* Статус резерва */}
          <div style={{ textAlign: "center", padding: "24px 0 20px" }}>
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              background: "rgba(200,169,110,0.1)", border: `1px solid rgba(200,169,110,0.25)`,
              borderRadius: 20, padding: "6px 14px", marginBottom: 16,
            }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: T.gold, animation: "pulseRing 1.5s ease-out infinite" }} />
              <span style={{ fontFamily: T.font, fontSize: 12, color: T.gold, fontWeight: 400 }}>
                Слот зарезервирован · <Timer seconds={30 * 60} />
              </span>
            </div>

            <div style={{ fontFamily: T.serif, fontWeight: 300, fontSize: 24, color: T.text, marginBottom: 6 }}>
              Запись создана
            </div>
            <div style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300, lineHeight: 1.6 }}>
              № {bookingId} · подтвердите бронирование оплатой
            </div>
          </div>

          {/* Детали записи */}
          <div style={{ background: T.s2, border: `1px solid ${T.border}`, borderRadius: 18, padding: "16px 18px", marginBottom: 14 }}>
            {rows.map((row, i) => (
              <div key={row.label} style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "9px 0",
                borderBottom: i < rows.length - 1 ? `1px solid ${T.border}` : "none",
              }}>
                <span style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300 }}>{row.label}</span>
                <span style={{ fontFamily: T.font, fontSize: 13, color: row.accent ? T.gold : T.text, fontWeight: row.accent ? 500 : 400, textAlign: "right", maxWidth: "60%" }}>
                  {row.value}
                </span>
              </div>
            ))}
          </div>

          {/* Объяснение предоплаты */}
          <div style={{
            background: "rgba(200,169,110,0.06)", border: `1px solid rgba(200,169,110,0.15)`,
            borderRadius: 14, padding: "14px 16px", marginBottom: 14,
          }}>
            <div style={{ fontFamily: T.font, fontSize: 13, color: T.text, fontWeight: 400, marginBottom: 8 }}>
              Предоплата <span style={{ color: T.gold }}>2 000 ₽</span>
            </div>
            <div style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300, lineHeight: 1.65 }}>
              Включает резервирование вашего слота, подготовку кабинета и администрирование записи.
              Сумма засчитывается в стоимость процедуры.
            </div>
            <div style={{ fontFamily: T.font, fontSize: 11, color: T.textMuted, fontWeight: 300, lineHeight: 1.6, marginTop: 8, opacity: 0.7 }}>
              При неявке или отмене менее чем за 24 часа предоплата не возвращается согласно публичной оферте.
            </div>
          </div>

          {/* Кнопка оплаты */}
          <button
            onClick={() => { window.location.href = paymentUrl; }}
            className="btn-pay"
            style={{
              width: "100%", height: 52, borderRadius: 26, border: "none",
              background: T.green, color: "#fff",
              fontFamily: T.font, fontSize: 14, fontWeight: 500,
              cursor: "pointer", marginBottom: 10,
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
              transition: "background 220ms ease",
            }}
          >
            Оплатить резерв · 2 000 ₽
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
              <path d="M2.5 6.5h8M7 3l3.5 3.5L7 10" stroke="#fff" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>

          <div style={{ fontFamily: T.font, fontSize: 11, color: T.textMuted, fontWeight: 300, textAlign: "center", lineHeight: 1.6 }}>
            Вы перейдёте на защищённую страницу оплаты ЮKassa
          </div>
        </div>
      </div>
    </>
  );
}
