import { useEffect, useState } from "react";
import { getSlots, getNearestSlot } from "../api/booking";
import { T, s, LoadingScreen, BackBtn, NextBtn } from "../theme";

function toISO(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function getDays(startOffset, count) {
  return Array.from({ length: count }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + startOffset + i);
    return d;
  });
}

const DAY_HEADS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"];

function buildCalendarGrid(year, month) {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startDow = (firstDay.getDay() + 6) % 7;
  const days = [];
  for (let i = 0; i < startDow; i++) days.push(null);
  for (let d = 1; d <= lastDay.getDate(); d++) days.push(new Date(year, month, d));
  return days;
}

export default function DateTime({ booking, next, back }) {
  const today = new Date();
  const [calYear, setCalYear] = useState(today.getFullYear());
  const [calMonth, setCalMonth] = useState(today.getMonth());
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedTime, setSelectedTime] = useState(null);
  const [slots, setSlots] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [nearest, setNearest] = useState(null);

  useEffect(() => {
    getNearestSlot(booking.totalDuration, booking.service.id).then((data) => {
      if (data.date) setNearest(data);
    });
  }, []);

  useEffect(() => {
    if (!selectedDate) return;
    setLoadingSlots(true);
    setSelectedTime(null);
    getSlots([], booking.totalDuration, toISO(selectedDate), booking.service.id).then((data) => {
      setSlots(data.slots || []);
      setLoadingSlots(false);
    });
  }, [selectedDate]);

  const calDays = buildCalendarGrid(calYear, calMonth);
  const todayISO = toISO(today);

  const prevMonth = () => {
    if (calMonth === 0) { setCalYear(y => y - 1); setCalMonth(11); }
    else setCalMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (calMonth === 11) { setCalYear(y => y + 1); setCalMonth(0); }
    else setCalMonth(m => m + 1);
  };

  const monthName = new Date(calYear, calMonth, 1)
    .toLocaleDateString("ru-RU", { month: "long", year: "numeric" });

  return (
    <div style={{ paddingBottom: 100 }}>
      {nearest && (
        <div
          onClick={() => next({ datetime: `${nearest.date} ${nearest.time}` })}
          className="nearest-slot"
          style={{
            display: "flex", alignItems: "center", gap: 10,
            background: T.s2,
            border: `1px solid rgba(90,148,103,0.35)`,
            borderRadius: 14,
            padding: "12px 14px",
            marginBottom: 12,
            cursor: "pointer",
          }}
        >
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: T.green, flexShrink: 0,
            boxShadow: `0 0 8px ${T.green}55`,
          }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: T.font, fontSize: 11, color: T.green, fontWeight: 400, marginBottom: 2, letterSpacing: "0.06em" }}>
              Ближайшее доступное
            </div>
            <div style={{ fontFamily: T.font, fontSize: 14, color: T.text, fontWeight: 500 }}>
              {new Date(nearest.date).toLocaleDateString("ru-RU", { weekday: "short", day: "numeric", month: "short" })}, {nearest.time}
            </div>
          </div>
          <svg className="nearest-arrow" width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3 7h8M8 4l3 3-3 3" stroke={T.green} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      )}

      <div style={{
        background: T.s2, border: `1px solid ${T.border}`,
        borderRadius: 18, padding: 16, marginBottom: 14,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <button onClick={prevMonth} className="cal-nav" style={navBtnStyle}>‹</button>
          <div style={{ fontFamily: T.serif, fontWeight: 300, fontSize: 16, color: T.text, textTransform: "capitalize" }}>
            {monthName}
          </div>
          <button onClick={nextMonth} className="cal-nav" style={navBtnStyle}>›</button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 2, marginBottom: 6 }}>
          {DAY_HEADS.map(h => (
            <div key={h} style={{ fontFamily: T.font, fontSize: 10, color: T.textMuted, textAlign: "center", fontWeight: 300, letterSpacing: "0.05em" }}>
              {h}
            </div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 3 }}>
          {calDays.map((day, i) => {
            if (!day) return <div key={`e-${i}`} />;
            const iso = toISO(day);
            const isPast = iso < todayISO;
            const isToday = iso === todayISO;
            const isSel = selectedDate && toISO(selectedDate) === iso;
            return (
              <div
                key={iso}
                onClick={() => !isPast && setSelectedDate(day)}
                className={isPast ? "" : "cal-day"}
                style={{
                  height: 34, display: "flex", alignItems: "center", justifyContent: "center",
                  fontFamily: T.font, fontSize: 12, borderRadius: 8,
                  cursor: isPast ? "default" : "pointer",
                  fontWeight: isSel ? 500 : 300,
                  color: isSel ? T.bg : isPast ? T.s3 : T.text,
                  background: isSel ? T.gold : "transparent",
                  border: isToday && !isSel ? `1px solid ${T.gold}` : "1px solid transparent",
                  transition: "all 0.18s",
                  position: "relative",
                }}
              >
                {day.getDate()}
                {isSel && (
                  <div style={{
                    position: "absolute", inset: -1, borderRadius: 8,
                    boxShadow: `0 0 12px rgba(200,169,110,0.35)`,
                    pointerEvents: "none",
                  }} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {selectedDate && (
        <div style={{ marginBottom: 8 }}>
          <div style={s.label}>
            Свободное время · {selectedDate.toLocaleDateString("ru-RU", { day: "numeric", month: "long" })}
          </div>
          {loadingSlots ? (
            <div style={{ display: "flex", justifyContent: "center", padding: 16 }}>
              <div style={{
                width: 24, height: 24,
                border: `1px solid ${T.border}`,
                borderTop: `1px solid ${T.gold}`,
                borderRadius: "50%",
                animation: "spin 0.9s linear infinite",
              }} />
            </div>
          ) : slots.length === 0 ? (
            <div style={{ fontFamily: T.font, fontSize: 14, color: T.textMuted, padding: "12px 0", fontWeight: 300 }}>
              Нет свободных слотов на этот день
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 7 }}>
              {slots.map((time) => {
                const isPicked = selectedTime === time;
                return (
                  <div
                    key={time}
                    onClick={() => setSelectedTime(time)}
                    className="time-slot"
                    style={{
                      ...s.timeSlot,
                      ...(isPicked ? s.timeSlotPicked : {}),
                    }}
                  >
                    {time}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      <div style={{
        background: T.s2, border: `1px solid rgba(138,110,66,0.2)`,
        borderRadius: 12, padding: "11px 14px",
        fontFamily: T.font, fontSize: 12, color: "#9a9490",
        fontWeight: 300, lineHeight: 1.55,
        borderLeft: "2px solid rgba(200,169,110,0.3)",
        paddingLeft: 12, marginBottom: 8, marginTop: 12,
      }}>
        Для бронирования требуется предоплата <span style={{ color: T.gold, fontWeight: 400 }}>2 000 ₽</span>.
        При отмене менее чем за 24 часа предоплата не возвращается.
      </div>

      <div style={s.footer}>
        <div style={s.footerInner}>
          <BackBtn onClick={back} />
          <NextBtn
            disabled={!selectedDate || !selectedTime}
            onClick={() => next({ datetime: `${toISO(selectedDate)} ${selectedTime}` })}
          />
        </div>
      </div>
    </div>
  );
}

const navBtnStyle = {
  width: 30, height: 30, borderRadius: "50%",
  border: `1px solid ${T.border}`, background: "transparent",
  color: T.textMuted, cursor: "pointer",
  fontFamily: T.font, fontSize: 16,
  display: "flex", alignItems: "center", justifyContent: "center",
};

// добавляем className к кнопкам месяца через замену в JSX ниже
