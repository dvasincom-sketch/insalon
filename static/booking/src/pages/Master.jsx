import { useEffect, useRef, useState } from "react";
import { getStaff } from "../api/booking";
import { T, s, LoadingScreen, BackBtn, NextBtn } from "../theme";

export default function Master({ booking, next, back }) {
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [picked, setPicked] = useState(null);
  const calledRef = useRef(false);

  useEffect(() => {
    if (calledRef.current) return;
    calledRef.current = true;
    getStaff([], booking.datetime, booking.totalDuration, booking.service.id).then((data) => {
      setStaff(data);
      setLoading(false);
      if (data.length === 1) {
        next({ master: data[0] });
      }
    });
  }, []);

  if (loading) return <LoadingScreen />;
  if (staff.length === 1) return null;

  const handlePick = (master) => {
    setPicked(master);
    setTimeout(() => next({ master }), 260);
  };

  return (
    <div style={{ paddingBottom: 100 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 10 }}>
        {staff.map((m) => {
          const isPicked = picked?.id === m.id;
          return (
            <div
              key={m.id}
              onClick={() => handlePick(m)}
              style={{
                ...s.row,
                ...(isPicked ? s.rowPicked : {}),
                transform: isPicked ? "scale(0.98)" : "scale(1)",
              }}
            >
              {isPicked && (
                <div style={{
                  position: "absolute", left: 0, top: 0,
                  width: 3, height: "100%",
                  background: `linear-gradient(to bottom, ${T.goldDim}, ${T.gold})`,
                  borderRadius: "3px 0 0 3px",
                }} />
              )}

              <div style={{
                width: 46, height: 46, borderRadius: "50%",
                border: `1.5px solid ${isPicked ? T.goldDim : T.border}`,
                overflow: "hidden", flexShrink: 0,
                background: T.s3, transition: "border-color 0.25s",
              }}>
                {m.avatar
                  ? <img src={m.avatar} alt={m.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  : <div style={{
                      width: "100%", height: "100%",
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      <svg width="26" height="26" viewBox="0 0 26 26" fill="none">
                        <circle cx="13" cy="10" r="5" stroke={isPicked ? T.gold : T.textMuted} strokeWidth="1.2"/>
                        <path d="M5 23c0-4.4 3.6-8 8-8s8 3.6 8 8" stroke={isPicked ? T.gold : T.textMuted} strokeWidth="1.2" strokeLinecap="round"/>
                      </svg>
                    </div>
                }
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontFamily: T.font, fontSize: 14, fontWeight: 500,
                  color: isPicked ? T.gold : T.text, marginBottom: 2,
                  transition: "color 0.25s",
                }}>
                  {m.name}
                </div>
                <div style={{ fontFamily: T.font, fontSize: 11, color: T.textMuted, fontWeight: 300 }}>
                  {m.specialization || "Специалист"}
                </div>
              </div>

              {m.rating > 0 && (
                <div style={{ display: "flex", alignItems: "center", gap: 3, color: T.gold, fontFamily: T.font, fontSize: 12, flexShrink: 0 }}>
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                    <path d="M6 1l1.3 2.9 3.2.3-2.3 2.2.5 3.3L6 8l-2.7 1.5.5-3.3L1.5 4l3.2-.1z"/>
                  </svg>
                  {m.rating}
                </div>
              )}
            </div>
          );
        })}

        <div
          onClick={() => handlePick(null)}
          style={{
            ...s.row,
            borderStyle: "dashed",
            ...(picked === null && picked !== undefined ? s.rowPicked : {}),
          }}
        >
          <div style={{
            width: 46, height: 46, borderRadius: "50%",
            border: `1px dashed ${T.border}`,
            background: T.s3, flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="9" cy="9" r="7" stroke={T.textMuted} strokeWidth="1" strokeDasharray="2 2"/>
              <path d="M6 9h6M9 6v6" stroke={T.textMuted} strokeWidth="1.2" strokeLinecap="round"/>
            </svg>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: T.font, fontSize: 14, fontWeight: 400, color: T.textMid }}>
              Любой мастер
            </div>
            <div style={{ fontFamily: T.font, fontSize: 11, color: T.textMuted, fontWeight: 300 }}>
              Выберем наиболее подходящего
            </div>
          </div>
        </div>
      </div>

      <div style={s.footer}>
        <div style={s.footerInner}>
          <BackBtn onClick={back} />
          <NextBtn
            disabled={picked === undefined}
            onClick={() => picked !== undefined && next({ master: picked })}
          />
        </div>
      </div>
    </div>
  );
}
