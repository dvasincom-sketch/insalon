import { useEffect, useState } from "react";
import { getServices } from "../api/booking";
import { T, s, LoadingScreen, BackBtn, NextBtn } from "../theme";

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

  const baseDuration = booking.totalDuration || booking.service.seance_length;
  const basePrice = booking.totalPrice || booking.service.price_min;
  const totalDuration = baseDuration + selected.reduce((acc, e) => acc + e.seance_length, 0);
  const totalPrice = basePrice + selected.reduce((acc, e) => acc + e.price_min, 0);

  if (loading) return <LoadingScreen />;

  return (
    <div style={{ paddingBottom: 100 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
        {extras.map((e) => {
          const isSel = !!selected.find((s) => s.id === e.id);
          return (
            <div
              key={e.id}
              onClick={() => toggle(e)}
              className="extra-row"
              style={{
                ...s.row,
                ...(isSel ? s.rowPicked : {}),
              }}
            >
              {isSel && (
                <div style={{
                  position: "absolute", left: 0, top: 0,
                  width: 3, height: "100%",
                  background: `linear-gradient(to bottom, ${T.goldDim}, ${T.gold})`,
                  borderRadius: "3px 0 0 3px",
                }} />
              )}
              {/* Название — левый край */}
              <div style={{
                flex: 1, minWidth: 0,
                fontFamily: T.font, fontSize: 15, fontWeight: 500,
                color: isSel ? T.gold : T.text,
                lineHeight: 1.35, transition: "color 0.25s",
                textAlign: "left", wordBreak: "break-word",
              }}>
                {e.title}
              </div>

              {/* Цена сверху, длительность снизу */}
              <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div style={{
                  fontFamily: T.font, fontSize: 15,
                  color: T.gold, fontWeight: 400, lineHeight: 1.2,
                }}>
                  +{e.price_min.toLocaleString("ru-RU")} ₽
                </div>
                <div style={{
                  fontFamily: T.font, fontSize: 11,
                  color: T.textMuted, fontWeight: 300, marginTop: 3,
                }}>
                  +{formatDuration(e.seance_length)}
                </div>
              </div>

              <div className="extra-check" style={{
                width: 22, height: 22, borderRadius: "50%",
                border: `1px solid ${isSel ? T.gold : T.border}`,
                background: isSel ? T.gold : "transparent",
                display: "flex", alignItems: "center", justifyContent: "center",
                flexShrink: 0, transition: "all 0.25s",
              }}>
                {isSel && (
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path d="M2 5l2 2.5L8 2.5" stroke="#111110" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </div>
            </div>
          );
        })}
      </div>

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
          {Math.floor(totalDuration / 60)} мин · {totalPrice.toLocaleString("ru-RU")} ₽
        </span>
      </div>

      <div style={{ ...s.footer, borderTop: "none" }}>
        <div style={s.footerInner}>
          <BackBtn onClick={back} />
          <NextBtn
            label={selected.length > 0 ? "Далее" : "Пропустить"}
            onClick={() => next({
              extras: [...(booking.extras || []), ...selected],
              totalDuration,
              totalPrice,
            })}
          />
        </div>
      </div>
    </div>
  );
}
