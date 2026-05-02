import { useEffect, useState } from "react";
import { getServices } from "../api/booking";
import { T, s, LoadingScreen, CheckIcon, BackBtn, NextBtn } from "../theme";

function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h} ч ${m > 0 ? m + " мин" : ""}`.trim();
  return `${m} мин`;
}

export default function Services({ booking, next, back }) {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [picked, setPicked] = useState(null);

  useEffect(() => {
    getServices(booking.category.id).then((data) => {
      setServices(data.sort((a, b) => a.seance_length - b.seance_length));
      setLoading(false);
    });
  }, [booking.category.id]);

  if (loading) return <LoadingScreen />;

  const handlePick = (svc) => {
    setPicked(svc);
    setTimeout(() => next({ service: svc }), 260);
  };

  return (
    <div style={{ paddingBottom: 24 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 8 }}>
        {services.map((svc) => {
          const isPicked = picked?.id === svc.id;
          return (
            <div
              key={svc.id}
              onClick={() => handlePick(svc)}
              className="row-item"
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

              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="row-name" style={{
                  fontFamily: T.font, fontSize: 15, fontWeight: 500,
                  color: isPicked ? T.gold : T.text,
                  marginBottom: 4, transition: "color 0.25s",
                }}>
                  {svc.title}
                </div>
                <div style={{ fontFamily: T.font, fontSize: 12, color: T.textMuted, fontWeight: 300 }}>
                  {formatDuration(svc.seance_length)}
                </div>
              </div>

              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div style={{ fontFamily: T.font, fontSize: 15, color: T.gold, fontWeight: 400 }}>
                  {svc.price_min.toLocaleString("ru-RU")} ₽
                </div>
                {svc.price_max && svc.price_max !== svc.price_min && (
                  <div style={{ fontFamily: T.font, fontSize: 11, color: T.textMuted, fontWeight: 300 }}>
                    до {svc.price_max.toLocaleString("ru-RU")} ₽
                  </div>
                )}
              </div>

              {isPicked && (
                <div style={{
                  width: 20, height: 20, borderRadius: "50%",
                  background: T.gold, flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  animation: "checkPop 0.3s cubic-bezier(0.34,1.56,0.64,1) both",
                }}>
                  <CheckIcon />
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div style={s.footer}>
        <div style={s.footerInner}>
          <BackBtn onClick={back} />
          <NextBtn label="Далее" disabled={!picked} onClick={() => picked && next({ service: picked })} />
        </div>
      </div>
      <style>{`@keyframes checkPop{from{transform:scale(0)}to{transform:scale(1)}}`}</style>
    </div>
  );
}
