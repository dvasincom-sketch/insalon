import { useState } from "react";
import Categories from "./pages/Categories";
import Services from "./pages/Services";
import Extras from "./pages/Extras";
import DateTime from "./pages/DateTime";
import Master from "./pages/Master";
import Contacts from "./pages/Contacts";
import Success from "./pages/Success";
import { T, s, Wordmark, Ambient, ProgressBar } from "./theme";

const STEPS = ["categories", "services", "extras", "datetime", "master", "contacts", "success"];

const STEP_META = {
  categories: { num: "01 / 07", title: "Выберите", titleEm: "категорию", hint: "С чего начнём сегодня?" },
  services:   { num: "02 / 07", title: "Выберите", titleEm: "услугу",    hint: "Выбрана категория" },
  extras:     { num: "03 / 07", title: "Добавьте", titleEm: "допы",      hint: "Можно пропустить" },
  datetime:   { num: "04 / 07", title: "Дата",     titleEm: "& время",   hint: "Выберите удобное время" },
  master:     { num: "05 / 07", title: "Ваш",      titleEm: "мастер",    hint: "Кто проведёт процедуру" },
  contacts:   { num: "06 / 07", title: "Ваши",     titleEm: "контакты",  hint: "Почти готово — последний шаг" },
  success:    { num: "07 / 07", title: "Всё",       titleEm: "готово!",   hint: "Запись подтверждена" },
};

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const [step, setStep] = useState(params.get("booking_id") ? "success" : "categories");
  const [booking, setBooking] = useState({
    category: null,
    service: null,
    extras: [],
    datetime: null,
    master: null,
    contact: null,
    paymentUrl: null,
  });

  const stepIndex = STEPS.indexOf(step);

  const next = (data) => {
    setBooking((prev) => ({ ...prev, ...data }));
    setStep(STEPS[stepIndex + 1]);
  };

  const back = () => {
    if (stepIndex > 0) setStep(STEPS[stepIndex - 1]);
  };

  const meta = STEP_META[step] || STEP_META.categories;
  const props = { booking, next, back };
  const isSuccess = step === "success";

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,300;0,400;1,300&family=Outfit:wght@300;400;500&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        html, body { background: ${T.bg}; min-height: 100dvh; }
        ::-webkit-scrollbar { display: none; }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulseRing {
          0%   { opacity: 0.8; transform: scale(1); }
          100% { opacity: 0;   transform: scale(1.35); }
        }

        /* ── HOVER ── */
        @media (hover: hover) {

          /* Кнопка Далее (gold) */
          .btn-next:hover { background: #d4b47a !important; }
          .btn-next:hover .btn-arrow { transform: translateX(3px); }

          /* Кнопка К оплате (green) */
          .btn-pay:hover { background: #6aaa78 !important; }
          .btn-pay:hover .btn-arrow { transform: translateX(3px); }

          /* Кнопка Назад (ghost) */
          .btn-back:hover { border-color: #484840 !important; }
          .btn-back:hover svg { color: #c0bcb6; }

          /* Скопировать ссылку */
          .btn-copy:hover { border-color: #c8a96e55 !important; color: #d0ccc4 !important; }

          /* Вернуться на сайт */
          .btn-site:hover { background: #d4b47a !important; }
          .btn-site:hover .btn-arrow { transform: translateX(3px); }

          /* Слот времени */
          .time-slot:hover { border-color: #c8a96e55 !important; color: #c8a96e !important; }

          /* День календаря */
          .cal-day:hover { background: #2a2a26 !important; color: #e8e0d4 !important; }

          /* Кнопки месяца */
          .cal-nav:hover { border-color: #484840 !important; color: #d0ccc4 !important; }

          /* Ближайшее доступное */
          .nearest-slot:hover { border-color: #5a946755 !important; }
          .nearest-slot:hover .nearest-arrow { transform: translateX(2px); }

          /* Поле ввода */
          .input-field:hover { border-color: #3e3e38 !important; }

          /* Строка услуги / мастера */
          .row-item:hover { background: #222220 !important; }
          .row-item:hover .row-name { color: #f2ede4 !important; }

          /* Карточка категории */
          .cat-card:hover { border-color: #3e3e38 !important; transform: translateY(-2px); }

          /* Строка экстры */
          .extra-row:hover .extra-check { border-color: #c8a96e66 !important; }
        }

        /* Transition базовые */
        .btn-next, .btn-pay, .btn-back, .btn-copy, .btn-site { transition: background 220ms ease, border-color 220ms ease; }
        .btn-arrow { transition: transform 220ms ease; display: inline-block; }
        .time-slot { transition: border-color 180ms ease, color 180ms ease; }
        .cal-day { transition: background 150ms ease, color 150ms ease; }
        .cal-nav { transition: border-color 180ms ease, color 180ms ease; }
        .nearest-slot { transition: border-color 200ms ease; }
        .nearest-arrow { transition: transform 200ms ease; display: inline-block; }
        .input-field { transition: border-color 150ms ease; }
        .row-item { transition: background 180ms ease; }
        .cat-card { transition: border-color 200ms ease, transform 200ms ease; }
        .extra-check { transition: border-color 180ms ease; }
      `}</style>

      <div style={s.phone}>
        <Ambient />

        {!isSuccess && (
          <div style={s.header}>
            <Wordmark />
            <ProgressBar step={stepIndex + 1} total={STEPS.length} />
            <div style={s.stepMeta}>
              <div style={s.stepNum}>{meta.num}</div>
              <StepDots current={stepIndex} total={STEPS.length} />
            </div>
            <div style={s.screenTitle}>
              {meta.title} <em style={{ fontStyle: "italic", color: T.gold }}>{meta.titleEm}</em>
            </div>
            <div style={s.screenHint}>
              {step === "services" && booking.category
                ? `Категория: ${booking.category.title}`
                : step === "extras" && booking.service
                ? `${booking.service.title} · ${Math.floor(booking.service.seance_length / 60)} мин`
                : step === "master" && booking.datetime
                ? booking.datetime
                : meta.hint}
            </div>
          </div>
        )}

        <div style={s.body} key={step}>
          <div style={{ animation: "fadeUp 0.35s cubic-bezier(0.22,1,0.36,1) both" }}>
            {step === "categories" && <Categories {...props} />}
            {step === "services"   && <Services   {...props} />}
            {step === "extras"     && <Extras      {...props} />}
            {step === "datetime"   && <DateTime    {...props} />}
            {step === "master"     && <Master      {...props} />}
            {step === "contacts"   && <Contacts    {...props} />}
            {step === "success"    && <Success      {...props} />}
          </div>
        </div>
      </div>
    </>
  );
}

function StepDots({ current, total }) {
  return (
    <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 5,
            width: i < current ? 5 : i === current ? 16 : 5,
            borderRadius: i === current ? 3 : "50%",
            background: i < current ? T.green : i === current ? T.gold : T.s3,
            transition: "all 0.4s cubic-bezier(0.34,1.56,0.64,1)",
          }}
        />
      ))}
    </div>
  );
}
