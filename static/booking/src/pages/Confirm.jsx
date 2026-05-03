import { useEffect, useState } from "react";
import { T } from "../theme";

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
    { label: "Услуга",       value: booking.service?.title, accent: true },
    { label: "Дата и время", value: formatDateTime(booking.datetime) },
    { label: "Длительность", value: `${Math.floor((booking.totalDuration || booking.service?.seance_length || 0) / 60)} мин` },
    { label: "Мастер",       value: booking.master?.name || "Любой свободный" },
    booking.extras?.length > 0 && { label: "Допы", value: booking.extras.map(e => e.title).join(", ") },
  ].filter(Boolean);

  return (
    <div style={{ paddingBottom: 32 }}>

      {/* Заголовок */}
      <div style={{ paddingTop: 8, paddingBottom: 20 }}>
        <div style={{ fontFamily: T.serif, fontWeight: 300, fontSize: 22, color: T.text, marginBottom: 4 }}>
          Запись создана
        </div>
        <div style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300, lineHeight: 1.6 }}>
          № {bookingId} · подтвердите бронирование оплатой
        </div>
      </div>

      {/* Детали записи — без разделителей между строками */}
      <div style={{
        background: T.s2, border: `1px solid ${T.border}`,
        borderRadius: 18, padding: "14px 18px", marginBottom: 12,
      }}>
        {rows.map((row) => (
          <div key={row.label} style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "8px 0",
          }}>
            <span style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300 }}>
              {row.label}
            </span>
            <span style={{
              fontFamily: T.font, fontSize: 13,
              color: row.accent ? T.gold : T.text,
              fontWeight: row.accent ? 500 : 400,
              textAlign: "right", maxWidth: "60%",
            }}>
              {row.value}
            </span>
          </div>
        ))}
      </div>

      {/* Объяснение предоплаты */}
      <div style={{
        background: "rgba(200,169,110,0.06)", border: `1px solid rgba(200,169,110,0.15)`,
        borderRadius: 14, padding: "14px 16px", marginBottom: 16,
      }}>
        <div style={{ fontFamily: T.font, fontSize: 13, color: T.text, fontWeight: 400, marginBottom: 6 }}>
          Предоплата <span style={{ color: T.gold }}>2 000 ₽</span>
        </div>
        <div style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300, lineHeight: 1.65 }}>
          Включает резервирование вашего слота, подготовку кабинета и администрирование записи.
          Сумма засчитывается в стоимость процедуры.
        </div>
        <div style={{
          fontFamily: T.font, fontSize: 11, color: T.textMuted, fontWeight: 300,
          lineHeight: 1.6, marginTop: 8, opacity: 0.7,
        }}>
          При неявке или отмене менее чем за 24 часа предоплата не возвращается согласно публичной оферте.
        </div>
      </div>

      {/* Таймер — над кнопкой */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
        background: "rgba(200,169,110,0.08)", border: `1px solid rgba(200,169,110,0.2)`,
        borderRadius: 12, padding: "10px 16px", marginBottom: 10,
      }}>
        <div style={{
          width: 6, height: 6, borderRadius: "50%",
          background: T.gold, flexShrink: 0,
          animation: "pulseRing 1.5s ease-out infinite",
        }} />
        <span style={{ fontFamily: T.font, fontSize: 12, color: T.gold, fontWeight: 400 }}>
          Слот зарезервирован · <Timer seconds={30 * 60} />
        </span>
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
  );
}
