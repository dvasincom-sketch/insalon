import { useState } from "react";
import { createBooking } from "../api/booking";

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

export default function Contacts({ booking, next, back }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState({});

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

  return (
    <div>
      <button onClick={back} style={{ marginBottom: 16 }}>← Назад</button>
      <h2>Ваши данные</h2>

      <div style={{ background: "#f5f5f5", borderRadius: 8, padding: 16, marginBottom: 24 }}>
        {summary.map((s) => (
          <div key={s.label} style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: 14 }}>
            <span style={{ color: "#555" }}>{s.label}</span>
            <span><strong>{s.value}</strong></span>
          </div>
        ))}
      </div>

      {[
        { label: "Имя", value: name, setter: setName, key: "name", placeholder: "Как вас зовут?" },
        { label: "Телефон", value: phone, setter: (v) => setPhone(formatPhone(v)), key: "phone", placeholder: "+7 (900) 000-00-00" },
        { label: "Email", value: email, setter: setEmail, key: "email", placeholder: "your@email.com" },
      ].map(({ label, value, setter, key, placeholder }) => (
        <div key={key} style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: "bold" }}>{label}</label>
          <input
            value={value}
            onChange={(e) => setter(e.target.value)}
            placeholder={placeholder}
            style={{
              width: "100%",
              padding: 12,
              borderRadius: 8,
              border: `1px solid ${errors[key] ? "red" : "#ddd"}`,
              fontSize: 16,
              boxSizing: "border-box",
            }}
          />
          {errors[key] && <div style={{ color: "red", fontSize: 13, marginTop: 4 }}>{errors[key]}</div>}
        </div>
      ))}

      <div style={{ padding: 16, background: "#fff8e1", borderRadius: 8, fontSize: 14, marginBottom: 16 }}>
        ⚠️ Для бронирования требуется предоплата <strong>2 000 ₽</strong>. При отмене или переносе менее чем за 24 часа предоплата не возвращается.
      </div>

      <button
        onClick={async () => {
          if (!validate()) return;
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
        }}
        style={{
          width: "100%",
          padding: 16,
          background: "#000",
          color: "#fff",
          border: "none",
          borderRadius: 8,
          cursor: "pointer",
          fontSize: 16,
        }}
      >
        Перейти к оплате →
      </button>
    </div>
  );
}
