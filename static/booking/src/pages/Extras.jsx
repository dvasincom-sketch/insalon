import { useEffect, useState } from "react";
import { getServices } from "../api/booking";

const EXTRAS_CATEGORY_ID = 19468211;

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60);
  return `${m} мин`;
}

export default function Extras({ booking, next, back }) {
  const [extras, setExtras] = useState([]);
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getServices(EXTRAS_CATEGORY_ID).then((data) => {
      setExtras(data);
      setLoading(false);
    });
  }, []);

  const toggle = (extra) => {
    setSelected((prev) =>
      prev.find((e) => e.id === extra.id)
        ? prev.filter((e) => e.id !== extra.id)
        : [...prev, extra]
    );
  };

  const totalDuration = booking.service.seance_length + selected.reduce((s, e) => s + e.seance_length, 0);
  const totalPrice = booking.service.price_min + selected.reduce((s, e) => s + e.price_min, 0);

  if (loading) return <p>Загрузка...</p>;

  return (
    <div>
      <button onClick={back} style={{ marginBottom: 16 }}>← Назад</button>
      <h2>Дополнительные услуги</h2>
      <p style={{ color: "#555" }}>Можно пропустить</p>

      {extras.map((e) => {
        const isSelected = selected.find((s) => s.id === e.id);
        return (
          <div
            key={e.id}
            onClick={() => toggle(e)}
            style={{
              border: `2px solid ${isSelected ? "#000" : "#ddd"}`,
              borderRadius: 8,
              padding: 16,
              marginBottom: 12,
              cursor: "pointer",
            }}
          >
            <strong>{e.title}</strong>
            <div style={{ marginTop: 8, color: "#555" }}>
              {formatDuration(e.seance_length)} · +{e.price_min.toLocaleString("ru-RU")} ₽
            </div>
          </div>
        );
      })}

      <div style={{ marginTop: 16, padding: 16, background: "#f5f5f5", borderRadius: 8 }}>
        <strong>Итого: {Math.floor(totalDuration / 60)} мин · {totalPrice.toLocaleString("ru-RU")} ₽</strong>
      </div>

      <button
        onClick={() => next({ extras: selected, totalDuration, totalPrice })}
        style={{ marginTop: 16, width: "100%", padding: 16, background: "#000", color: "#fff", border: "none", borderRadius: 8, cursor: "pointer", fontSize: 16 }}
      >
        Продолжить
      </button>
    </div>
  );
}
