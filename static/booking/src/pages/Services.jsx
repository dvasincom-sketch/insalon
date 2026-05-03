import { useEffect, useState } from "react";
import { getServices } from "../api/booking";
import { T, s, LoadingScreen, BackBtn, NextBtn } from "../theme";

function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h} ч ${m > 0 ? m + " мин" : ""}`.trim();
  return `${m} мин`;
}

// Чекбокс — круглый, в стиле Extras
function Checkbox({ checked }) {
  return (
    <div style={{
      width: 22, height: 22, borderRadius: "50%", flexShrink: 0,
      border: `1px solid ${checked ? T.gold : T.border}`,
      background: checked ? T.gold : "transparent",
      display: "flex", alignItems: "center", justifyContent: "center",
      transition: "all 0.22s",
    }}>
      {checked && (
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M2 5l2 2.5L8 2.5" stroke="#111110" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      )}
    </div>
  );
}

export default function Services({ booking, next, back }) {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState([]);

  useEffect(() => {
    getServices(booking.category.id).then((data) => {
      setServices(data.sort((a, b) => a.seance_length - b.seance_length));
      setLoading(false);
    });
  }, [booking.category.id]);

  if (loading) return <LoadingScreen />;

  const toggle = (svc) => {
    setSelected((prev) =>
      prev.find((s) => s.id === svc.id)
        ? prev.filter((s) => s.id !== svc.id)
        : [...prev, svc]
    );
  };

  const totalDuration = selected.reduce((acc, s) => acc + s.seance_length, 0);
  const totalPrice = selected.reduce((acc, s) => acc + s.price_min, 0);

  const handleNext = () => {
    if (selected.length === 0) return;
    const [main, ...extras] = selected;
    // Первая выбранная = основная услуга
    // Остальные = extras (суммируются по времени и цене)
    next({
      service: main,
      extras: extras,
      totalDuration: totalDuration,
      totalPrice: totalPrice,
    });
  };

  return (
    <div style={{ paddingBottom: 100 }}>
      <style>{`
        @keyframes checkPop {
          from { transform: scale(0); opacity: 0; }
          to   { transform: scale(1); opacity: 1; }
        }
      `}</style>

      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 8 }}>
        {services.map((svc) => {
          const isSelected = !!selected.find((s) => s.id === svc.id);
          return (
            <div
              key={svc.id}
              onClick={() => toggle(svc)}
              className="row-item"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "13px 14px",
                background: T.s2,
                border: `1px solid ${isSelected ? T.gold : T.border}`,
                borderRadius: 16,
                cursor: "pointer",
                position: "relative",
                overflow: "hidden",
                transition: "border-color 0.22s",
              }}
            >
              {/* Gold bar при выборе */}
              {isSelected && (
                <div style={{
                  position: "absolute", left: 0, top: 0,
                  width: 3, height: "100%",
                  background: `linear-gradient(to bottom, ${T.goldDim}, ${T.gold})`,
                  borderRadius: "3px 0 0 3px",
                }} />
              )}

              {/* Название — левый край, растягивается */}
              <div style={{
                flex: 1,
                fontFamily: T.font, fontSize: 15, fontWeight: 500,
                color: isSelected ? T.gold : T.text,
                lineHeight: 1.35,
                transition: "color 0.22s",
                textAlign: "left",
                wordBreak: "break-word",
              }}>
                {svc.title}
              </div>

              {/* Цена + длительность */}
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div style={{
                  fontFamily: T.font, fontSize: 15,
                  color: T.gold, fontWeight: 400, lineHeight: 1.2,
                }}>
                  {svc.price_min.toLocaleString("ru-RU")} ₽
                </div>
                <div style={{
                  fontFamily: T.font, fontSize: 11,
                  color: T.textMuted, fontWeight: 300, marginTop: 3,
                }}>
                  {formatDuration(svc.seance_length)}
                </div>
              </div>

              {/* Чекбокс */}
              <Checkbox checked={isSelected} />
            </div>
          );
        })}
      </div>

      {/* Итого — появляется при выборе */}
      {selected.length > 0 && (
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          background: T.s2, border: `1px solid rgba(200,169,110,0.25)`,
          borderRadius: 20, padding: "5px 12px 5px 8px",
          fontFamily: T.font, fontSize: 11, color: T.textMuted,
          marginBottom: 6,
        }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: T.gold, flexShrink: 0 }} />
          <span>Итого:&nbsp;</span>
          <span style={{ color: T.gold, fontWeight: 500 }}>
            {formatDuration(totalDuration)} · {totalPrice.toLocaleString("ru-RU")} ₽
          </span>
        </div>
      )}

      <div style={{ ...s.footer, borderTop: "none" }}>
        <div style={s.footerInner}>
          <BackBtn onClick={back} />
          <NextBtn
            label="Далее"
            disabled={selected.length === 0}
            onClick={handleNext}
          />
        </div>
      </div>
    </div>
  );
}
