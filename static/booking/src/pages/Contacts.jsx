import { useState } from "react";
import { createBooking } from "../api/booking";
import { T, s, BackBtn, NextBtn } from "../theme";

function validatePhone(phone) {
  const cleaned = phone.replace(/[\s\-\(\)]/g, "");
  return /^(\+7|8)\d{10}$/.test(cleaned);
}

function formatPhone(value) {
  const digits = value.replace(/\D/g, "");
  const normalized = digits.startsWith("8") ? "7" + digits.slice(1) : digits;
  const d = normalized.startsWith("7") ? normalized.slice(1) : normalized;
  let result = "+7";
  if (d.length > 0) result += " (" + d.slice(0, 3);
  if (d.length >= 3) result += ") " + d.slice(3, 6);
  if (d.length >= 6) result += "-" + d.slice(6, 8);
  if (d.length >= 8) result += "-" + d.slice(8, 10);
  return result;
}

function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function FloatInput({ id, label, value, onChange, type = "text", error }) {
  const [focused, setFocused] = useState(false);
  const lifted = focused || value.length > 0;
  return (
    <div style={{ position: "relative", marginBottom: 10 }}>
      <label
        htmlFor={id}
        style={{
          position: "absolute",
          left: 16,
          top: lifted ? 8 : "50%",
          transform: lifted ? "none" : "translateY(-50%)",
          fontFamily: T.font,
          fontSize: lifted ? 10 : 13,
          letterSpacing: lifted ? "0.05em" : 0,
          color: error ? "#8a3030" : lifted ? T.goldDim : T.textMuted,
          pointerEvents: "none",
          transition: "all 0.2s cubic-bezier(0.22,1,0.36,1)",
          fontWeight: 300,
          zIndex: 1,
        }}
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className="input-field"
        style={{
          ...s.input,
          ...(error ? s.inputError : {}),
          ...(focused ? { borderColor: "rgba(200,169,110,0.3)" } : {}),
        }}
      />
      {error && (
        <div style={{ fontFamily: T.font, fontSize: 11, color: "#8a3030", marginTop: 4, fontWeight: 300 }}>
          {error}
        </div>
      )}
    </div>
  );
}

export default function Contacts({ booking, next, back }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const validate = () => {
    const e = {};
    if (!name.trim()) e.name = "Введите имя";
    if (!validatePhone(phone)) e.phone = "Введите корректный номер";
    if (!validateEmail(email)) e.email = "Введите корректный email";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const summary = [
    { label: "Услуга", value: booking.service.title },
    { label: "Дата и время", value: booking.datetime },
    { label: "Длительность", value: `${Math.floor(booking.totalDuration / 60)} мин` },
    { label: "Стоимость", value: `${booking.totalPrice.toLocaleString("ru-RU")} ₽` },
    booking.master && { label: "Мастер", value: booking.master.name },
  ].filter(Boolean);

  const handleSubmit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    try {
      const result = await createBooking({
        service_id: booking.service.id,
        service_title: booking.service.title,
        datetime: booking.datetime,
        duration: booking.totalDuration,
        total_price: booking.totalPrice,
        master_id: booking.master?.id || null,
        master_name: booking.master?.name || null,
        client_name: name,
        client_phone: phone,
        client_email: email,
        extras: booking.extras.map(e => ({ id: e.id, title: e.title })),
      });
      window.top.location.href = result.payment_url;
    } catch {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ paddingBottom: 100 }}>
      <div style={{
        background: T.s2, border: `1px solid ${T.border}`,
        borderRadius: 16, padding: "14px 16px", marginBottom: 18,
      }}>
        {summary.map((item, i) => (
          <div key={item.label} style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "8px 0",
            borderBottom: i < summary.length - 1 ? `1px solid ${T.border}` : "none",
          }}>
            <span style={{ fontFamily: T.font, fontSize: 11, color: T.textMuted, letterSpacing: "0.06em", textTransform: "none", fontWeight: 300 }}>
              {item.label}
            </span>
            <span style={{ fontFamily: T.font, fontSize: 13, color: T.text, fontWeight: 400 }}>
              {item.value}
            </span>
          </div>
        ))}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "baseline",
          paddingTop: 14, marginTop: 6,
          borderTop: `1px solid rgba(200,169,110,0.2)`,
        }}>
          <span style={{ fontFamily: T.font, fontSize: 11, color: T.textMuted, letterSpacing: "0.06em", textTransform: "none", fontWeight: 300 }}>Итого</span>
          <span style={{ fontFamily: T.serif, fontWeight: 300, fontSize: 22, color: T.gold }}>
            {booking.totalPrice.toLocaleString("ru-RU")} ₽
          </span>
        </div>
      </div>

      <FloatInput id="f-name"  label="Ваше имя"              value={name}  onChange={e => setName(e.target.value)}                         error={errors.name}  />
      <FloatInput id="f-phone" label="Телефон"               value={phone} onChange={e => setPhone(formatPhone(e.target.value))} type="tel"  error={errors.phone} />
      <FloatInput id="f-email" label="Email"                 value={email} onChange={e => setEmail(e.target.value)}              type="email" error={errors.email} />

      <div style={{
        background: T.s2, border: `1px solid rgba(138,110,66,0.2)`,
        borderRadius: 12, padding: "11px 14px",
        fontFamily: T.font, fontSize: 11, color: T.textMuted, letterSpacing: "0.06em", textTransform: "none",
        fontWeight: 300, lineHeight: 1.55, marginBottom: 10,
      }}>
        Для бронирования требуется предоплата <span style={{ color: T.gold, fontWeight: 400 }}>2 000 ₽</span>.
        При отмене или переносе менее чем за 24 часа предоплата не возвращается.
      </div>

      <div style={{ fontFamily: T.font, fontSize: 11, color: T.s3, lineHeight: 1.6, marginBottom: 8 }}>
        Подтверждая запись, вы принимаете{" "}
        <span style={{ color: "#4a4a46", textDecoration: "underline", textUnderlineOffset: 2 }}>
          условия использования
        </span>
      </div>

      <div style={s.footer}>
        <div style={s.footerInner}>
          <BackBtn onClick={back} />
          <NextBtn
            label={submitting ? "Отправка..." : "Перейти к оплате"}
            confirm
            disabled={submitting}
            onClick={handleSubmit}
          />
        </div>
      </div>
    </div>
  );
}
