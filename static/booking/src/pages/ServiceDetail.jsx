import { T, s, BackBtn, NextBtn } from "../theme";

function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h} ч ${m > 0 ? m + " мин" : ""}`.trim();
  return `${m} мин`;
}

// inlineMode = true → внутри Services на Desktop (нет обёртки, нет кнопки Назад)
// inlineMode = false (default) → отдельный экран через App на мобильном
export default function ServiceDetail({ service, onBack, onSelect, inlineMode = false }) {
  if (!service) return null;

  const description = service.description || null;

  const content = (
    <>
      {/* Название */}
      <div style={{
        fontFamily: T.serif, fontWeight: 300,
        fontSize: inlineMode ? 19 : 22,
        color: T.text, lineHeight: 1.2, marginBottom: 12,
      }}>
        {service.title}
      </div>

      {/* Pill-бейджи: длительность + цена */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          background: T.s3, border: `1px solid rgba(200,169,110,0.2)`,
          borderRadius: 20, padding: "5px 12px",
        }}>
          <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
            <circle cx="5.5" cy="5.5" r="4" stroke={T.gold} strokeWidth="1"/>
            <path d="M5.5 3v2.5l1.5 1" stroke={T.gold} strokeWidth="1" strokeLinecap="round"/>
          </svg>
          <span style={{ fontFamily: T.font, fontSize: 12, color: T.gold, fontWeight: 400 }}>
            {formatDuration(service.seance_length)}
          </span>
        </div>
        <div style={{
          display: "inline-flex", alignItems: "center",
          background: T.s3, border: `1px solid rgba(200,169,110,0.2)`,
          borderRadius: 20, padding: "5px 12px",
        }}>
          <span style={{ fontFamily: T.font, fontSize: 12, color: T.gold, fontWeight: 400 }}>
            {service.price_min.toLocaleString("ru-RU")} ₽
            {service.price_max && service.price_max !== service.price_min
              ? ` — ${service.price_max.toLocaleString("ru-RU")} ₽`
              : ""}
          </span>
        </div>
      </div>

      {/* Описание */}
      <div style={{
        background: inlineMode ? T.s3 : T.s2,
        border: `1px solid ${T.border}`,
        borderRadius: 14, padding: "14px 16px",
        marginBottom: inlineMode ? 20 : 14,
      }}>
        {description ? (
          <div style={{
            fontFamily: T.font, fontSize: 13, color: T.textMid,
            fontWeight: 300, lineHeight: 1.7,
            whiteSpace: "pre-wrap",
          }}>
            {description}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{
              fontFamily: T.font, fontSize: 13, color: T.textMuted,
              fontWeight: 300, lineHeight: 1.6,
            }}>
              Описание этой услуги скоро появится.
            </div>
            <div style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "9px 12px",
              background: T.s3, borderRadius: 10,
              fontFamily: T.font, fontSize: 11,
              color: T.textMuted, fontWeight: 300,
            }}>
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <circle cx="6.5" cy="6.5" r="5" stroke={T.goldDim} strokeWidth="1"/>
                <path d="M6.5 6v3M6.5 4.5v.01" stroke={T.goldDim} strokeWidth="1.3" strokeLinecap="round"/>
              </svg>
              Подробности можно уточнить у администратора
            </div>
          </div>
        )}
      </div>

      {/* Кнопка выбора */}
      {inlineMode ? (
        // Desktop: кнопка без BackBtn
        <button
          onClick={() => onSelect(service)}
          className="btn-next"
          style={{
            width: "100%", height: 48, borderRadius: 24,
            background: T.gold, border: "none", color: T.bg,
            fontFamily: T.font, fontSize: 14, fontWeight: 500,
            letterSpacing: "0.04em", cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center", gap: 7,
            transition: "background 220ms ease",
          }}
        >
          Выбрать эту услугу
          <svg className="btn-arrow" width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3 7h8M8 4l3 3-3 3" stroke={T.bg} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      ) : (
        // Mobile: полноценный футер с Назад + Выбрать
        <div style={s.footer}>
          <div style={s.footerInner}>
            <BackBtn onClick={onBack} />
            <NextBtn
              label="Выбрать эту услугу"
              onClick={() => onSelect(service)}
            />
          </div>
        </div>
      )}
    </>
  );

  if (inlineMode) {
    return <div>{content}</div>;
  }

  // Mobile: отдельный экран, просто контент в s.body
  return <div style={{ paddingBottom: 100 }}>{content}</div>;
}
