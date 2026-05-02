import { useEffect, useState } from "react";
import { getBooking } from "../api/booking";
import { T, s, Wordmark, Ambient } from "../theme";

function formatDateTime(dt) {
  if (!dt) return "";
  const d = new Date(dt);
  return (
    d.toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" }) +
    ", " +
    d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
  );
}

export default function Success() {
  const params = new URLSearchParams(window.location.search);
  const bookingId = params.get("booking_id");
  const [booking, setBooking] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (bookingId) getBooking(bookingId).then(setBooking);
  }, [bookingId]);

  const copyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const rows = booking
    ? [
        { label: "Услуга",        value: booking.service_title,                                    accent: true },
        { label: "Дата и время",  value: formatDateTime(booking.datetime) },
        { label: "Длительность",  value: `${Math.floor(booking.duration / 60)} мин` },
        { label: "Мастер",        value: booking.master_name || "Любой свободный" },
        { label: "Статус",        value: booking.status === "pending" ? "Ожидает оплаты" : "Оплачено",
          color: booking.status === "pending" ? T.gold : T.green },
      ]
    : [];

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,300;0,400;1,300&family=Outfit:wght@300;400;500&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { background: ${T.bg}; min-height: 100dvh; }
        @keyframes pulseRing {
          0%   { opacity: 0.7; transform: scale(1); }
          100% { opacity: 0;   transform: scale(1.4); }
        }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div style={{ ...s.phone, padding: "0 0 32px" }}>
        <Ambient />

        <div style={{ padding: "20px 24px 0", flexShrink: 0, position: "relative", zIndex: 2 }}>
          <Wordmark />
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "0 24px", zIndex: 2, scrollbarWidth: "none", animation: "fadeUp 0.4s cubic-bezier(0.22,1,0.36,1) both" }}>

          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "28px 0 22px" }}>
            <div style={{ position: "relative", width: 72, height: 72, marginBottom: 20 }}>
              <div style={{
                position: "absolute", inset: -6, borderRadius: "50%",
                border: `1px solid rgba(90,148,103,0.25)`,
                animation: "pulseRing 2.5s ease-out infinite",
              }} />
              <div style={{
                position: "absolute", inset: -13, borderRadius: "50%",
                border: `1px solid rgba(90,148,103,0.12)`,
                animation: "pulseRing 2.5s ease-out 0.55s infinite",
              }} />
              <div style={{
                width: 72, height: 72, borderRadius: "50%",
                background: T.s2, border: `1px solid rgba(90,148,103,0.3)`,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <svg width="30" height="30" viewBox="0 0 30 30" fill="none">
                  <path d="M7 15l6 6L23 9" stroke={T.green} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
            </div>

            <div style={{ fontFamily: T.serif, fontWeight: 300, fontSize: 26, color: T.text, marginBottom: 6, textAlign: "center" }}>
              Запись подтверждена
            </div>
            <div style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300, textAlign: "center", lineHeight: 1.6 }}>
              {bookingId && `№ ${bookingId} · `}Напоминание придёт за 2 часа
            </div>
          </div>

          {booking && (
            <div style={{
              background: T.s2, border: `1px solid ${T.border}`,
              borderRadius: 18, padding: "16px 18px", marginBottom: 14,
            }}>
              {rows.map((row, i) => (
                <div key={row.label} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "9px 0",
                  borderBottom: i < rows.length - 1 ? `1px solid ${T.border}` : "none",
                }}>
                  <span style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300 }}>{row.label}</span>
                  <span style={{ fontFamily: T.font, fontSize: 13, color: row.color || (row.accent ? T.gold : T.text), fontWeight: row.accent ? 500 : 400 }}>
                    {row.value}
                  </span>
                </div>
              ))}

              {booking.extras?.length > 0 && (
                <div style={{ padding: "9px 0", borderTop: `1px solid ${T.border}`, marginTop: 0 }}>
                  <div style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300, marginBottom: 4 }}>Допы</div>
                  {booking.extras.map((e, i) => (
                    <div key={i} style={{ fontFamily: T.font, fontSize: 13, color: T.text, fontWeight: 400 }}>{e.title}</div>
                  ))}
                </div>
              )}

              <div style={{
                display: "flex", justifyContent: "space-between", alignItems: "baseline",
                paddingTop: 14, marginTop: 6,
                borderTop: `1px solid rgba(200,169,110,0.2)`,
              }}>
                <span style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300 }}>Итого</span>
                <span style={{ fontFamily: T.serif, fontWeight: 300, fontSize: 24, color: T.gold }}>
                  {booking.total_price?.toLocaleString("ru-RU")} ₽
                </span>
              </div>
            </div>
          )}

          <div style={{
            background: T.s2, border: `1px solid ${T.border}`,
            borderRadius: 14, padding: "12px 14px", marginBottom: 14,
          }}>
            {[
              { icon: "📍", text: "Приходите за 10 минут до начала" },
              { icon: "❌", text: "Отмена — не позднее чем за 24 часа" },
              { icon: "📞", text: "+7 977 883-23-47" },
            ].map((item) => (
              <div key={item.text} style={{
                display: "flex", gap: 8, alignItems: "flex-start",
                padding: "5px 0",
                fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300, lineHeight: 1.5,
              }}>
                <span style={{ fontSize: 13 }}>{item.icon}</span>
                <span>{item.text}</span>
              </div>
            ))}
          </div>

          <button
            onClick={copyLink}
            style={{
              width: "100%", height: 50, borderRadius: 25,
              background: "transparent", border: `1px solid ${T.border}`,
              color: copied ? T.green : T.textMid,
              fontFamily: T.font, fontSize: 13, fontWeight: 400,
              cursor: "pointer", marginBottom: 8,
              transition: "all 0.25s",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
            }}
          >
            {copied ? (
              <>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M2 7l4 4 6-7" stroke={T.green} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Скопировано
              </>
            ) : "Скопировать ссылку на запись"}
          </button>

          <button
            onClick={() => { window.top.location.href = "https://headspa.beauty"; }}
            style={{
              width: "100%", height: 50, borderRadius: 25,
              background: T.gold, border: "none",
              color: T.bg, fontFamily: T.font, fontSize: 13, fontWeight: 500,
              cursor: "pointer", letterSpacing: "0.04em",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
            }}
          >
            Вернуться на сайт
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
              <path d="M2.5 6.5h8M7 3l3.5 3.5L7 10" stroke={T.bg} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </div>
    </>
  );
}
