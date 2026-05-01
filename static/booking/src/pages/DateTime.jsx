import { useEffect, useState } from "react";
import { getSlots, getNearestSlot } from "../api/booking";

function formatDate(date) {
  return date.toLocaleDateString("ru-RU", { weekday: "short", day: "numeric", month: "short" });
}

function toISO(date) {
  return date.toISOString().split("T")[0];
}

function getDays(startOffset, count) {
  return Array.from({ length: count }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + startOffset + i);
    return d;
  });
}

export default function DateTime({ booking, next, back }) {
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedTime, setSelectedTime] = useState(null);
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [nearest, setNearest] = useState(null);
  const [weekOffset, setWeekOffset] = useState(1);

  const days = getDays(weekOffset, 7);

  useEffect(() => {
    getNearestSlot(booking.totalDuration).then((data) => {
      if (data.date) setNearest(data);
    });
  }, []);

  useEffect(() => {
    if (!selectedDate) return;
    setLoading(true);
    setSelectedTime(null);
    getSlots([], booking.totalDuration, toISO(selectedDate)).then((data) => {
      setSlots(data.slots || []);
      setLoading(false);
    });
  }, [selectedDate]);

  const selectNearest = () => {
    if (!nearest) return;
    const d = new Date(nearest.date);
    setSelectedDate(d);
    setSelectedTime(nearest.time);
  };

  return (
    <div>
      <button onClick={back} style={{ marginBottom: 16 }}>← Назад</button>
      <h2>Выберите дату</h2>

      {nearest && (
        <div
          onClick={selectNearest}
          style={{
            background: "#f0faf0",
            border: "2px solid #4caf50",
            borderRadius: 8,
            padding: 16,
            marginBottom: 16,
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 13, color: "#4caf50", marginBottom: 4 }}>✓ Ближайшее доступное время</div>
          <strong>
            {new Date(nearest.date).toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}, {nearest.time}
          </strong>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 8 }}>
        {days.map((d) => (
          <div
            key={toISO(d)}
            onClick={() => setSelectedDate(d)}
            style={{
              minWidth: 80,
              padding: "10px 8px",
              borderRadius: 8,
              border: `2px solid ${selectedDate && toISO(d) === toISO(selectedDate) ? "#000" : "#ddd"}`,
              textAlign: "center",
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            {formatDate(d)}
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        {weekOffset > 1 && (
          <button
            onClick={() => { setWeekOffset(w => w - 7); setSelectedDate(null); }}
            style={{ flex: 1, padding: 8, borderRadius: 8, border: "1px solid #555", cursor: "pointer", background: "#fff", color: "#000" }}
          >
            ← Предыдущая неделя
          </button>
        )}
        <button
          onClick={() => { setWeekOffset(w => w + 7); setSelectedDate(null); }}
          style={{ flex: 1, padding: 8, borderRadius: 8, border: "1px solid #555", cursor: "pointer", background: "#fff", color: "#000" }}
        >
          Следующая неделя →
        </button>
      </div>

      {selectedDate && (
        <>
          <h3 style={{ marginTop: 24 }}>Выберите время</h3>
          {loading && <p>Загрузка...</p>}
          {!loading && slots.length === 0 && (
            <p style={{ color: "#999" }}>Нет свободных слотов на этот день</p>
          )}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {slots.map((time) => (
              <div
                key={time}
                onClick={() => setSelectedTime(time)}
                style={{
                  padding: "10px 16px",
                  borderRadius: 8,
                  border: `2px solid ${selectedTime === time ? "#000" : "#ddd"}`,
                  cursor: "pointer",
                  fontWeight: selectedTime === time ? "bold" : "normal",
                }}
              >
                {time}
              </div>
            ))}
          </div>
        </>
      )}

      <div style={{ marginTop: 24, padding: 16, background: "#fff8e1", borderRadius: 8, fontSize: 14 }}>
        ⚠️ Для бронирования требуется предоплата 2 000 ₽. При отмене менее чем за 24 часа предоплата не возвращается.
      </div>

      <button
        disabled={!selectedDate || !selectedTime}
        onClick={() => next({ datetime: `${toISO(selectedDate)} ${selectedTime}` })}
        style={{
          marginTop: 16,
          width: "100%",
          padding: 16,
          background: selectedDate && selectedTime ? "#000" : "#ccc",
          color: "#fff",
          border: "none",
          borderRadius: 8,
          cursor: selectedDate && selectedTime ? "pointer" : "default",
          fontSize: 16,
        }}
      >
        Продолжить
      </button>
    </div>
  );
}
