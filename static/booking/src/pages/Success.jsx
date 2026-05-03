import { useEffect, useState } from "react";
import { getBooking } from "../api/booking";
import { T, Ambient } from "../theme";

const PREPAYMENT = 2000;
const TEA_TIME_MIN = 30;
const DRESS_TIME_MIN = 15;
const SALON_FLOOR = "3 этаж";
const SALON_ADDRESS = "Москва, ул. Садовническая, 14с2";
const SALON_METRO = "3 мин от м. Новокузнецкая · 3 этаж";
const SALON_PHONE = "+7 977 883-23-47";
const OFERTA_URL = "https://headspa.beauty/oferta";
const WHATSAPP_NUM = "79778832347";

function formatDate(dt) {
  if (!dt) return "";
  const d = new Date(dt.replace(" ", "T"));
  return d.toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" });
}
function formatTime(dt) {
  if (!dt) return "";
  const d = new Date(dt.replace(" ", "T"));
  return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}
function arriveTime(dt) {
  if (!dt) return "";
  const d = new Date(dt.replace(" ", "T"));
  d.setMinutes(d.getMinutes() - 10);
  return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

const D = "1px dashed #2e2e2a";
const S = "1px solid #2a2a26";

function Row({ label, value, valueColor }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "5px 0" }}>
      <div style={{ fontSize: 12, color: "#8a8480", fontWeight: 300, fontFamily: "'Outfit',sans-serif" }}>{label}</div>
      <div style={{ fontSize: 13, color: valueColor || "#e8e0d4", fontFamily: "'Outfit',sans-serif" }}>{value}</div>
    </div>
  );
}

function SecTitle({ children }) {
  return (
    <div style={{
      fontSize: 10, color: "#6a6660", letterSpacing: "0.10em",
      textTransform: "uppercase", fontWeight: 400, marginBottom: 10,
      fontFamily: "'Outfit',sans-serif", textAlign: "left",
    }}>
      {children}
    </div>
  );
}

function FieldLabel({ children }) {
  return (
    <div style={{
      fontSize: 10, color: "#6a6660", letterSpacing: "0.12em",
      textTransform: "uppercase", fontWeight: 300,
      fontFamily: "'Outfit',sans-serif", marginBottom: 3,
    }}>
      {children}
    </div>
  );
}

function IconBox({ size = 28, bg = "#222220", border = "1px solid #2a2a26", radius = 8, children }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: radius, background: bg,
      border, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
    }}>
      {children}
    </div>
  );
}

function QRDecor() {
  return (
    <svg width="34" height="34" viewBox="0 0 42 42" fill="none">
      <rect x="3" y="3" width="13" height="13" rx="2" fill="#252520"/>
      <rect x="6" y="6" width="7" height="7" rx="1" fill="#c8a96e" opacity="0.5"/>
      <rect x="26" y="3" width="13" height="13" rx="2" fill="#252520"/>
      <rect x="29" y="6" width="7" height="7" rx="1" fill="#c8a96e" opacity="0.5"/>
      <rect x="3" y="26" width="13" height="13" rx="2" fill="#252520"/>
      <rect x="6" y="29" width="7" height="7" rx="1" fill="#c8a96e" opacity="0.5"/>
      <rect x="26" y="26" width="4" height="4" rx="1" fill="#333330"/>
      <rect x="32" y="26" width="4" height="4" rx="1" fill="#333330"/>
      <rect x="38" y="26" width="4" height="4" rx="1" fill="#333330"/>
      <rect x="26" y="32" width="4" height="4" rx="1" fill="#333330"/>
      <rect x="32" y="32" width="4" height="4" rx="1" fill="#333330"/>
      <rect x="26" y="38" width="4" height="4" rx="1" fill="#333330"/>
      <rect x="38" y="38" width="4" height="4" rx="1" fill="#333330"/>
    </svg>
  );
}

// П.16: аватар мастера — фото если есть, иначе инициал
function MasterAvatar({ name, avatarUrl }) {
  const initial = name ? name.charAt(0).toUpperCase() : "М";
  if (avatarUrl) {
    return (
      <img src={avatarUrl} alt={name} style={{
        width: 40, height: 40, borderRadius: "50%",
        objectFit: "cover", flexShrink: 0,
        border: "1.5px solid #3a3a36",
      }} />
    );
  }
  return (
    <div style={{
      width: 40, height: 40, borderRadius: "50%",
      background: "#252520", border: "1.5px solid #3a3a36",
      display: "flex", alignItems: "center", justifyContent: "center",
      flexShrink: 0, fontFamily: "'Outfit',sans-serif",
      fontSize: 15, fontWeight: 400, color: "#c8a96e",
    }}>
      {initial}
    </div>
  );
}

export default function Success() {
  const params = new URLSearchParams(window.location.search);
  const bookingId = params.get("booking_id");
  const [booking, setBooking] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!bookingId) return;
    let attempts = 0;
    const poll = async () => {
      const data = await getBooking(bookingId);
      setBooking(data);
      if (data.status !== "paid" && attempts < 10) {
        attempts++;
        setTimeout(poll, 2000);
      }
    };
    poll();
  }, [bookingId]);

  const isPaid = booking?.status === "paid";
  const durationMin = booking ? Math.floor(booking.duration / 60) : 0;
  const remaining = booking ? booking.total_price - PREPAYMENT : 0;

  const copyLink = () => {
    navigator.clipboard.writeText(`https://headspa.beauty/booking/${bookingId}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{
      background: T.bg, minHeight: "100dvh",
      display: "flex", flexDirection: "column", alignItems: "stretch",
      fontFamily: "'Outfit',sans-serif", position: "relative",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,300;1,300&family=Outfit:wght@300;400;500&display=swap');
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.45} }
        @keyframes fadeUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
      `}</style>

      {/* П.14: ambient фон как на всех экранах */}
      <Ambient />

      <div style={{
        width: "100%", maxWidth: 430, margin: "0 auto",
        minHeight: "100dvh", display: "flex", flexDirection: "column",
        animation: "fadeUp 0.4s cubic-bezier(0.22,1,0.36,1) both",
      }}>

        {/* Шапка — вне ваучера */}
        <div style={{ padding: "18px 22px 12px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 300, letterSpacing: "0.22em", color: "#8a6e42", textTransform: "uppercase", marginBottom: 3 }}>
              Insalon · Head Spa
            </div>
            <div style={{ fontFamily: "'Playfair Display',serif", fontStyle: "italic", fontWeight: 300, fontSize: 18, color: "#f2ede4" }}>
              Ваучер на визит
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 5 }}>
            <div style={{
              display: "flex", alignItems: "center", gap: 5,
              background: isPaid ? "#1a2e1e" : "#2a2414",
              border: `1px solid ${isPaid ? "#3d6b4a55" : "#8a6e4255"}`,
              borderRadius: 20, padding: "4px 10px 4px 7px",
            }}>
              <div style={{
                width: 7, height: 7, borderRadius: "50%",
                background: isPaid ? "#5a9467" : "#c8a96e",
                animation: isPaid ? "blink 2.5s ease-in-out infinite" : "none",
              }} />
              <span style={{ fontSize: 11, fontWeight: 500, color: isPaid ? "#5a9467" : "#c8a96e", letterSpacing: "0.04em" }}>
                {isPaid ? "Оплачено" : "Ожидает оплаты"}
              </span>
            </div>
            <div style={{ fontSize: 10, color: "#5a5a56", fontWeight: 300, letterSpacing: "0.06em" }}>
              № {bookingId}
            </div>
          </div>
        </div>

        {/* П.15: ваучер — отдельная карточка со скруглёнными углами */}
        {booking && (
          <div style={{ margin: "0 16px 16px", background: "#1a1a18", borderRadius: 20, border: S, overflow: "hidden" }}>

            {/* Золотой блок даты/времени */}
            <div style={{ background: "#c8a96e", padding: "16px 20px 14px", position: "relative", overflow: "hidden" }}>
              <div style={{
                position: "absolute", inset: 0, pointerEvents: "none",
                background: "repeating-linear-gradient(45deg,transparent,transparent 18px,rgba(0,0,0,0.04) 18px,rgba(0,0,0,0.04) 19px)",
              }} />
              <div style={{ fontSize: 10, fontWeight: 500, letterSpacing: "0.16em", textTransform: "uppercase", color: "rgba(17,17,16,0.5)", marginBottom: 5 }}>
                Дата и время визита
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 5, flexWrap: "wrap" }}>
                <span style={{ fontFamily: "'Playfair Display',serif", fontWeight: 300, fontSize: 21, color: "#111110", lineHeight: 1 }}>
                  {formatDate(booking.datetime)}
                </span>
                <span style={{ fontSize: 24, fontWeight: 500, color: "#111110", lineHeight: 1, letterSpacing: "-0.01em" }}>
                  {formatTime(booking.datetime)}
                </span>
              </div>
              <div style={{ fontSize: 11, color: "rgba(17,17,16,0.6)", fontWeight: 300 }}>
                Просим прийти{" "}
                <b style={{ fontWeight: 500, color: "rgba(17,17,16,0.85)" }}>в {arriveTime(booking.datetime)}</b>
                {" "}— мастер готов встретить вас
              </div>
            </div>

            {/* Услуга */}
            <div style={{ padding: "13px 20px", borderBottom: D }}>
              <FieldLabel>Услуга</FieldLabel>
              <div style={{ fontFamily: "'Playfair Display',serif", fontWeight: 300, fontSize: 18, color: "#f2ede4", lineHeight: 1.2 }}>
                {booking.service_title}
              </div>
              {booking.extras?.length > 0 && booking.extras.map((e, i) => (
                <div key={i} style={{ fontSize: 12, color: "#6a6660", fontWeight: 300, marginTop: 3 }}>+ {e.title}</div>
              ))}
            </div>

            {/* Оплата */}
            <div style={{ padding: "12px 20px", borderBottom: D }}>
              <SecTitle>Оплата</SecTitle>
              <Row label="Стоимость услуги" value={`${booking.total_price?.toLocaleString("ru-RU")} ₽`} />
              <Row label="Предоплата (оплачено)" value={`−${PREPAYMENT.toLocaleString("ru-RU")} ₽`} valueColor="#5a9467" />
              <div style={{ height: "0.5px", background: "#222220", margin: "5px 0" }} />
              {remaining > 0 && (
                <div style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "7px 12px", background: "#1f1c14",
                  border: "1px solid #c8a96e33", borderRadius: 10, marginTop: 4,
                }}>
                  <div style={{ fontSize: 12, color: "#c8a96e", fontWeight: 400 }}>Доплатить на месте</div>
                  <div style={{ fontFamily: "'Playfair Display',serif", fontWeight: 300, fontSize: 20, color: "#c8a96e" }}>
                    {remaining.toLocaleString("ru-RU")} ₽
                  </div>
                </div>
              )}
            </div>

            {/* П.16: Мастер с аватаром + кабинет в одну строку */}
            <div style={{ padding: "12px 20px", borderBottom: D }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <MasterAvatar name={booking.master_name} avatarUrl={booking.master_avatar} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <FieldLabel>Мастер</FieldLabel>
                  <div style={{ fontSize: 14, color: "#e8e0d4", fontWeight: 500 }}>
                    {booking.master_name || "Любой свободный"}
                  </div>
                </div>
                <div style={{ textAlign: "right", flexShrink: 0 }}>
                  <FieldLabel>Кабинет</FieldLabel>
                  <div style={{ fontSize: 14, color: "#e8e0d4", fontWeight: 400 }}>{SALON_FLOOR}</div>
                </div>
              </div>
            </div>

            {/* П.17: Как устроено время — левое выравнивание, компактная плашка */}
            <div style={{ padding: "12px 20px", borderBottom: D }}>
              <SecTitle>Как устроено ваше время</SecTitle>
              {[
                {
                  icon: <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><rect x="2" y="4" width="9" height="7" rx="1.5" stroke="#c8a96e" strokeWidth="1"/><path d="M5 4V3a2 2 0 0 1 3 0v1" stroke="#c8a96e" strokeWidth="1" strokeLinecap="round"/></svg>,
                  label: "Время на кушетке",
                  time: `${durationMin} мин`,
                },
                {
                  icon: <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M2.5 5c0-1 .9-2 2-2h4a2 2 0 0 1 2 2v1h-8V5z" stroke="#c8a96e" strokeWidth="1"/><path d="M1.5 6h10l-.8 4.5H2.3L1.5 6z" stroke="#c8a96e" strokeWidth="1" strokeLinejoin="round"/></svg>,
                  label: "Чаепитие и сушка волос",
                  time: `${TEA_TIME_MIN} мин`,
                },
              ].map((item, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 7 }}>
                  <IconBox>{item.icon}</IconBox>
                  <div style={{ fontSize: 13, color: "#c0bcb6", flex: 1, fontFamily: "'Outfit',sans-serif", fontWeight: 300, textAlign: "left" }}>
                    {item.label}
                  </div>
                  <div style={{ fontSize: 13, color: "#e8e0d4", fontWeight: 500, fontFamily: "'Outfit',sans-serif" }}>
                    {item.time}
                  </div>
                </div>
              ))}

              {/* Переодевание — компактная плашка, всё в одну строку */}
              <div style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "7px 10px", background: "#1c1e1a",
                border: "1px solid #2e3628", borderRadius: 10, marginTop: 2,
              }}>
                <IconBox bg="#1a2214" border="1px solid #3d5030">
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <circle cx="6.5" cy="6.5" r="4.5" stroke="#5a9467" strokeWidth="1"/>
                    <path d="M4.5 6.5l1.5 1.5 2.5-2.5" stroke="#5a9467" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </IconBox>
                <div style={{ fontSize: 12, color: "#8aaa78", fontWeight: 300, fontFamily: "'Outfit',sans-serif", flex: 1, textAlign: "left" }}>
                  Переодевание и анкета — не входит в оплачиваемое время
                </div>
                <div style={{
                  fontSize: 11, color: "#5a9467", fontWeight: 500,
                  background: "#1a2e1e", border: "1px solid #3d6b4a55",
                  borderRadius: 10, padding: "2px 8px", flexShrink: 0,
                  fontFamily: "'Outfit',sans-serif",
                }}>
                  +{DRESS_TIME_MIN} мин
                </div>
              </div>
            </div>

            {/* П.18: Адрес — без заголовка, левое выравнивание */}
            <div style={{ padding: "12px 20px", borderBottom: D }}>
              <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
                <div style={{
                  width: 30, height: 30, borderRadius: "50%",
                  background: "#1f1f1c", border: "1px solid #2a2a26",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  flexShrink: 0, marginTop: 1,
                }}>
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <path d="M6.5 1C4.3 1 2.5 2.8 2.5 5c0 3 4 7 4 7s4-4 4-7c0-2.2-1.8-4-4-4z" stroke="#8a8480" strokeWidth="1" strokeLinejoin="round"/>
                    <circle cx="6.5" cy="5" r="1.2" stroke="#8a8480" strokeWidth="1"/>
                  </svg>
                </div>
                <div>
                  <div style={{ fontSize: 13, color: "#e8e0d4", lineHeight: 1.45 }}>{SALON_ADDRESS}</div>
                  <div style={{ fontSize: 11, color: "#8a8480", fontWeight: 300, marginTop: 2 }}>{SALON_METRO}</div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => window.open(`https://yandex.ru/maps/?text=${encodeURIComponent(SALON_ADDRESS)}`, "_blank")}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "center", gap: 7,
                  width: "100%", height: 38, borderRadius: 19,
                  border: "1px solid #2e2e2a", background: "transparent",
                  color: "#8a8480", fontSize: 12, fontWeight: 300,
                  cursor: "pointer", fontFamily: "'Outfit',sans-serif", transition: "all 0.2s",
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = "#3e3e38"; e.currentTarget.style.color = "#c0bcb6"; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = "#2e2e2a"; e.currentTarget.style.color = "#8a8480"; }}
              >
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <path d="M2 6.5h9M8 3.5l3 3-3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Построить маршрут в Яндекс Картах
              </button>
            </div>

            {/* П.19: QR + permalink — одна строка с вертикальным разделителем */}
            <div style={{ padding: "12px 20px", display: "flex", alignItems: "center" }}>
              {/* QR слева */}
              <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 0 }}>
                <div style={{
                  width: 46, height: 46, flexShrink: 0,
                  background: "#1f1f1c", borderRadius: 8, border: "1px solid #2a2a26",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <QRDecor />
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "#e8e0d4", fontWeight: 400, marginBottom: 1 }}>
                    Всё в порядке
                  </div>
                  <div style={{ fontSize: 10, color: "#6a6660", fontWeight: 300 }}>
                    Вас ждут
                  </div>
                </div>
              </div>

              {/* Вертикальный разделитель */}
              <div style={{ width: "0.5px", background: "#2a2a26", alignSelf: "stretch", margin: "0 14px" }} />

              {/* Permalink справа */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 11, color: "#c0bcb6", fontWeight: 400, marginBottom: 3 }}>
                  Ваш талон здесь
                </div>
                <div style={{
                  fontSize: 10, color: "#5a5a56", fontWeight: 300,
                  whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                  letterSpacing: "0.03em", marginBottom: 6,
                }}>
                  headspa.beauty/booking/{bookingId}
                </div>
                <button
                  type="button"
                  onClick={copyLink}
                  style={{
                    fontSize: 10, color: copied ? "#5a9467" : "#c8a96e", fontWeight: 400,
                    background: "transparent",
                    border: `1px solid ${copied ? "#3d6b4a55" : "#c8a96e44"}`,
                    borderRadius: 10, padding: "3px 9px",
                    cursor: "pointer", fontFamily: "'Outfit',sans-serif",
                    transition: "all 0.2s", whiteSpace: "nowrap",
                  }}
                >
                  {copied ? "✓ скопировано" : "копировать"}
                </button>
              </div>
            </div>

          </div>
        )}

        {/* Условия — вне ваучера */}
        <div style={{ padding: "4px 22px 10px" }}>
          <SecTitle>Условия визита</SecTitle>
          {[
            ["за 10 минут", "Приходите за 10 минут — мастер готовится к процедуре заранее"],
            ["сократить программу", "При опоздании мастер может сократить программу без изменения стоимости"],
            ["менее чем за 24 ч", "Отмена или перенос менее чем за 24 ч — предоплата не возвращается"],
            [SALON_PHONE, `Вопросы — ${SALON_PHONE}`],
          ].map(([bold, text], i) => (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 6, marginBottom: i < 3 ? 5 : 0 }}>
              <div style={{ width: 3, height: 3, borderRadius: "50%", background: "#5a5a56", flexShrink: 0, marginTop: 5 }} />
              <div style={{ fontSize: 12, color: "#7a7a76", fontWeight: 300, lineHeight: 1.4, fontFamily: "'Outfit',sans-serif", textAlign: "left" }}>
                {text.split(bold).map((part, j, arr) => (
                  <span key={j}>
                    {part}
                    {j < arr.length - 1 && <b style={{ color: "#9a9490", fontWeight: 400 }}>{bold}</b>}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Перенос / Отмена */}
        <div style={{ padding: "10px 22px", display: "flex", gap: 8 }}>
          {[
            { label: "Перенести запись", icon: <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M1 6a5 5 0 1 0 5-5" stroke="currentColor" strokeWidth="1" strokeLinecap="round"/><path d="M1 2v4h4" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/></svg>, text: "Хочу перенести запись", danger: false },
            { label: "Отменить запись", icon: <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 3h8M5 3V2h2v1M4.5 9.5l-.5-5M7.5 9.5l.5-5" stroke="currentColor" strokeWidth="1" strokeLinecap="round"/><rect x="2.5" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1"/></svg>, text: "Хочу отменить запись", danger: true },
          ].map((btn, i) => (
            <button
              key={i} type="button"
              onClick={() => window.open(`https://wa.me/${WHATSAPP_NUM}?text=${encodeURIComponent(`${btn.text} №${bookingId}`)}`, "_blank")}
              style={{
                flex: 1, height: 40, borderRadius: 20,
                background: "transparent", border: "1px solid #2a2a26",
                color: "#8a8480", fontFamily: "'Outfit',sans-serif",
                fontSize: 12, fontWeight: 300, cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 5,
                transition: "all 0.2s",
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = btn.danger ? "#6a302e" : "#3e3e38"; e.currentTarget.style.color = btn.danger ? "#aa6060" : "#c0bcb6"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "#2a2a26"; e.currentTarget.style.color = "#8a8480"; }}
            >
              {btn.icon} {btn.label}
            </button>
          ))}
        </div>

        {/* Публичная оферта */}
        <div style={{ padding: "4px 22px 10px", textAlign: "center" }}>
          <a href={OFERTA_URL} target="_blank" rel="noopener noreferrer"
            style={{ fontSize: 11, color: "#4a4a46", fontWeight: 300, textDecoration: "underline", textUnderlineOffset: 2, textDecorationColor: "#3a3a36" }}>
            Публичная оферта и условия бронирования
          </a>
        </div>

        {/* Футер */}
        <div style={{ padding: "8px 22px 32px", display: "flex", flexDirection: "column", gap: 9 }}>
          <button
            type="button"
            onClick={() => { window.top.location.href = "https://headspa.beauty"; }}
            style={{
              width: "100%", height: 50, borderRadius: 25, background: "#c8a96e", border: "none", color: "#111110",
              fontFamily: "'Outfit',sans-serif", fontSize: 14, fontWeight: 500, letterSpacing: "0.04em",
              cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 7, transition: "background 0.22s",
            }}
            onMouseEnter={e => e.currentTarget.style.background = "#d4b47a"}
            onMouseLeave={e => e.currentTarget.style.background = "#c8a96e"}
          >
            Вернуться на сайт
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
              <path d="M2.5 6.5h8M7 3.5l3 3-3 3" stroke="#111110" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
          <button
            type="button" onClick={() => {}}
            style={{
              width: "100%", height: 46, borderRadius: 23, background: "transparent", border: "1px solid #2a2a26",
              color: "#7a7a76", fontFamily: "'Outfit',sans-serif", fontSize: 13, fontWeight: 300, cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6, transition: "all 0.22s",
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = "#3e3e38"; e.currentTarget.style.color = "#c0bcb6"; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "#2a2a26"; e.currentTarget.style.color = "#7a7a76"; }}
          >
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
              <rect x="2" y="4" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1"/>
              <path d="M4 4V3a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H9" stroke="currentColor" strokeWidth="1" strokeLinecap="round"/>
            </svg>
            Сохранить как изображение
          </button>
        </div>

      </div>
    </div>
  );
}
