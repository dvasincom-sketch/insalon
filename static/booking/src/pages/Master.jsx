import { useEffect, useState } from "react";
import { getStaff } from "../api/booking";

export default function Master({ booking, next, back }) {
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStaff([], booking.datetime, booking.totalDuration).then((data) => {
      setStaff(data);
      setLoading(false);
    });
  }, []);

  if (loading) return <p>Загрузка...</p>;

  // Если один мастер — пропускаем шаг
  if (staff.length === 1) {
    next({ master: staff[0] });
    return null;
  }

  return (
    <div>
      <button onClick={back} style={{ marginBottom: 16 }}>← Назад</button>
      <h2>Выберите мастера</h2>

      {staff.map((s) => (
        <div
          key={s.id}
          onClick={() => next({ master: s })}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            border: "1px solid #ddd",
            borderRadius: 8,
            padding: 16,
            marginBottom: 12,
            cursor: "pointer",
          }}
        >
          <img
            src={s.avatar}
            alt={s.name}
            style={{ width: 56, height: 56, borderRadius: "50%", objectFit: "cover" }}
          />
          <div>
            <strong>{s.name}</strong>
            <div style={{ fontSize: 13, color: "#555", marginTop: 4 }}>{s.specialization}</div>
            {s.rating > 0 && (
              <div style={{ fontSize: 13, color: "#f5a623", marginTop: 4 }}>★ {s.rating}</div>
            )}
          </div>
        </div>
      ))}

      <div
        onClick={() => next({ master: null })}
        style={{
          border: "1px dashed #ddd",
          borderRadius: 8,
          padding: 16,
          textAlign: "center",
          cursor: "pointer",
          color: "#555",
        }}
      >
        Не важно — выберите за меня
      </div>
    </div>
  );
}
