import { useEffect, useState } from "react";
import { getServices } from "../api/booking";

function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h} ч ${m > 0 ? m + " мин" : ""}`.trim();
  return `${m} мин`;
}

export default function Services({ booking, next, back }) {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getServices(booking.category.id).then((data) => {
      setServices(data.sort((a, b) => a.seance_length - b.seance_length));
      setLoading(false);
    });
  }, [booking.category.id]);

  if (loading) return <p>Загрузка...</p>;

  return (
    <div>
      <button onClick={back} style={{ marginBottom: 16 }}>← Назад</button>
      <h2>{booking.category.title}</h2>
      {services.map((s) => (
        <div
          key={s.id}
          onClick={() => next({ service: s })}
          style={{
            border: "1px solid #ddd",
            borderRadius: 8,
            padding: 16,
            marginBottom: 12,
            cursor: "pointer",
          }}
        >
          <strong>{s.title}</strong>
          <div style={{ marginTop: 8, color: "#555" }}>
            {formatDuration(s.seance_length)} · {s.price_min.toLocaleString("ru-RU")} ₽
          </div>
        </div>
      ))}
    </div>
  );
}
