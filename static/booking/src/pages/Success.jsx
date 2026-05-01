import { useEffect, useState } from "react";
import { getBooking } from "../api/booking";

function formatDateTime(dt) {
  if (!dt) return "";
  const d = new Date(dt);
  return d.toLocaleDateString("ru-RU", {
    weekday: "long", day: "numeric", month: "long", year: "numeric"
  }) + ", " + d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

export default function Success() {
  const params = new URLSearchParams(window.location.search);
  const bookingId = params.get("booking_id");
  const [booking, setBooking] = useState(null);

  useEffect(() => {
    if (bookingId) getBooking(bookingId).then(setBooking);
  }, [bookingId]);

  return (
    <div style={{ maxWidth: 480, margin: "0 auto", padding: 24, fontFamily: "sans-serif" }}>
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <div style={{ fontSize: 56 }}>✅</div>
        <h2 style={{ margin: "8px 0" }}>Запись подтверждена!</h2>
        <div style={{ color: "#555", fontSize: 14 }}>Номер записи #{bookingId}</div>
      </div>

      {booking && (
        <div style={{
          border: "2px solid #000",
          borderRadius: 16,
          overflow: "hidden",
          marginBottom: 24,
        }}>
          <div style={{ background: "#000", color: "#fff", padding: "16px 20px" }}>
            <div style={{ fontSize: 12, opacity: 0.6, marginBottom: 4 }}>HeadSPA Beauty</div>
            <div style={{ fontSize: 18, fontWeight: "bold" }}>{booking.service_title}</div>
          </div>

          <div style={{ padding: "16px 20px" }}>
            {[
              { label: "📅 Дата и время", value: formatDateTime(booking.datetime) },
              { label: "⏱ Длительность", value: `${Math.floor(booking.duration / 60)} мин` },
              { label: "👤 Мастер", value: booking.master_name || "Любой свободный" },
              { label: "💰 Стоимость", value: `${booking.total_price?.toLocaleString("ru-RU")} ₽` },
              { label: "📋 Статус", value: booking.status === "pending" ? "⏳ Ожидает оплаты" : "✅ Оплачено" },
            ].map(({ label, value }) => (
              <div key={label} style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "10px 0",
                borderBottom: "1px solid #f0f0f0",
                fontSize: 14,
              }}>
                <span style={{ color: "#555" }}>{label}</span>
                <span style={{ fontWeight: "bold", textAlign: "right", maxWidth: "60%" }}>{value}</span>
              </div>
            ))}

            {booking.extras?.length > 0 && (
              <div style={{ padding: "10px 0", fontSize: 14 }}>
                <div style={{ color: "#555", marginBottom: 4 }}>➕ Дополнения</div>
                {booking.extras.map((e, i) => (
                  <div key={i} style={{ fontWeight: "bold" }}>{e.title}</div>
                ))}
              </div>
            )}
          </div>

          <div style={{ background: "#f5f5f5", padding: "16px 20px", fontSize: 13, color: "#555" }}>
            <p style={{ margin: "4px 0" }}>📍 Приходите за 10 минут до начала</p>
            <p style={{ margin: "4px 0" }}>❌ Отмена — не позднее чем за 24 часа</p>
            <p style={{ margin: "4px 0" }}>📞 +7 977 883-23-47</p>
          </div>
        </div>
      )}

      <button
        onClick={() => {
          const url = window.location.href;
          navigator.clipboard.writeText(url);
          alert("Ссылка скопирована!");
        }}
        style={{
          width: "100%",
          padding: 14,
          background: "#fff",
          border: "2px solid #000",
          borderRadius: 8,
          cursor: "pointer",
          fontSize: 15,
          marginBottom: 12,
          color: "#000",
        }}
      >
        Скопировать ссылку на запись
      </button>

      <button
        onClick={() => window.top.location.href = "https://headspa.beauty"}
        style={{
          width: "100%",
          padding: 14,
          background: "#000",
          color: "#fff",
          border: "none",
          borderRadius: 8,
          cursor: "pointer",
          fontSize: 15,
        }}
      >
        Вернуться на сайт
      </button>
    </div>
  );
}
