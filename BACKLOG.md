# BACKLOG — Insalon
> Единый источник истины. Обновляется после каждой сессии.
> Последнее обновление: 02.05.2026

---

## P0 — Критичные (блокируют работу)

- [ ] **Перевыпустить YCLIENTS Partner Token** — засвечен в репозитории → DEV
- [ ] **Внести исторические данные payroll за 2025 год** (146 смен: Александра, Ольга, Светлана, Екатерина, Анна, Татьяна) → DEV
- [ ] **Исправить balance Марии январь** (5500₽ при status=paid) → DEV
- [ ] **Загрузить выписку физ карты за ноябрь 2025** (данные отсутствуют) → DEV

---

## P1 — Важные (следующий спринт)

### Виджет онлайн-записи
- [ ] Интеграция ЮKassa — реальная оплата предоплаты 2000₽ → DEV
- [ ] Webhook ЮKassa → обновление статуса booking → DEV
- [ ] Натянуть дизайн на виджет (стили headspa.beauty) → DEV
- [ ] widget.js для встройки в Tilda через iframe → DEV
- [ ] Адрес салона в билете подтверждения → DEV
- [ ] Защита от двойного бронирования (проверка при оплате) → DEV

### Data & Analytics
- [ ] L2 Event-Driven: воронка клиента через `attendance` (Cancel Rate, No-Show Rate) → ANALYTICS → DEV
- [ ] Bridge Conversion SPA→Массаж — измерение конверсии → ANALYTICS → DEV
- [ ] **Utilization heatmap с реальными данными** из `shifts` (сейчас `Math.random()` заглушка) → DEV
- [ ] Selektор проектов в P&L (salon/podcast/книга/консалтинг/консолидированный) → DEV
- [ ] Многоуровневый P&L с раскрывающимися строками → DEV
- [ ] Cash Flow прогноз на конец месяца → ANALYTICS → DEV

### ФОТ & Payroll
- [ ] **Автоматизация привязки выплат** из `personal_transactions` к мастерам (`staff_payment_aliases`) → DEV
- [ ] `visit_pay` в payroll вычислять динамически из `visit_records` (сейчас хранится отдельно) → ANALYTICS → DEV
- [ ] **Расширить фильтр парных программ** — добавить "SPA для мужчин" и другие услуги → DEV
- [ ] Форма ввода расписания смен в UI (сейчас только через SQL) → DEV
- [ ] Форма ввода выхода под запись в UI (сейчас через SQL) → DEV
- [ ] Автозаполнение `visit_records` из парных программ для новых месяцев → DEV

### Качество данных
- [ ] Неизвестные получатели в `personal_transactions` (Юлия С., Мирзамагомед М. и др.) → DEV
- [ ] Проверка 4 из `checks.py` — смены без payroll за 2025 добавить как автопроверку → DEV
- [ ] Уточнить источник записей "Мастер" в `shifts` (ручные vs YCLIENTS синк) + добавить очистку дублей → DEV

---

## P2 — Желательные (следующие спринты)

### Системные принципы Клеппмана
- [ ] Least Privilege — RLS в Supabase по ролям → ANALYTICS → DEV
- [ ] Наблюдаемость — health dashboard (% синхронизации YCLIENTS, gaps в данных) → ANALYTICS → DEV
- [ ] Resilience — retry логика в YCLIENTS клиенте (Circuit Breaker) → DEV
- [ ] Webhook обработка удалённых записей YCLIENTS → DEV

### Аналитика
- [ ] L3 Unit-Economic Modeling — сценарный P&L (что если ставка 6000₽?) → PRODUCT → ANALYTICS → DEV
- [ ] L4 Behavioral Nudges — триггеры реактивации клиентов → PRODUCT → ANALYTICS → DEV

### Инфраструктура
- [ ] Cron автосинхронизация данных YCLIENTS → DEV
- [ ] Подключить домен api.check.moscow → DEV
- [ ] Настроить TablePlus подключение к Supabase → DEV
- [ ] Настроить алиасы в `~/.zshrc` (`insalon`, `rundev`) → DEV
- [ ] Makefile для команд проекта → DEV

### Frontend
- [ ] **Dev Log — фикс padding на десктопе 1280px** (первая карточка обрезается сайдбаром) → DEV
- [ ] Перейти на ES modules (`type="module"`) после стабилизации → DEV
- [ ] Вынести хардкод имён сотрудников из `STAFF_COLORS` в конфиг или API → DEV
- [ ] Добавить централизованный error handler в `api.js` → DEV

---

## ✅ Сделано (архив)

### Sprint 5 — 2026-05-02
- [x] **Dev Log экран** — трекер dev-сессий (`dev_sessions` в Supabase, FastAPI роутер, `devlog.js` модуль)
- [x] Виджет онлайн-записи (React + Vite) в `static/booking/`
- [x] Категории услуг из БД с фильтрацией служебных
- [x] Услуги с длительностью и ценой (seance_length из YCLIENTS)
- [x] Дополнительные услуги с пересчётом итога
- [x] Выбор даты и времени с реальными слотами
- [x] Ближайший свободный слот + навигация по неделям
- [x] Выбор мастера с фото и рейтингом (только активные)
- [x] Форма контактов с валидацией телефона и маской
- [x] Создание бронирования → лид → клиент в YCLIENTS
- [x] Страница подтверждения (билет) с уникальной ссылкой
- [x] Таблицы: `bookings`, `leads`, `service_categories`
- [x] Поле `is_active` в `staff` (6 активных мастеров)
- [x] Синк категорий и `seance_length` из YCLIENTS API
- [x] `run_in_executor` для синхронных POST запросов к YCLIENTS



### Sprint 2 — 2026-04-29
- [x] Tabler UI v2 дашборд с 4 экранами
- [x] North Star CM/LH
- [x] Эффективность мастеров (коэффициент, абонементы, двойные смены)
- [x] Расписание смен (календарь с цветами)
- [x] Ведомость оплаты труда + сверка с выписками
- [x] Разметка проектов (salon/podcast/book/startup/consulting)
- [x] P&L очищен от личных расходов
- [x] Таблица `shifts` создана (март и апрель заполнены)
- [x] Таблица `payroll` создана (март полностью, апрель 1–14)
- [x] Пагинация `fetch_all()` для Supabase 1000+ строк

### Sprint 3 — 2026-04-30
- [x] Таб 🧮 Расчёт ФОТ — полный цикл draft→paid→ведомость
- [x] Модальное окно выплаты (наличные/безнал)
- [x] Кнопка печати чека PDF
- [x] Колонка "Зачёт" в ведомости оплаты труда
- [x] `staff_payment_aliases`, `payroll_audit`, `offset_amount`, `payroll.status`
- [x] Триггеры `payroll_balance_trigger` и `payroll_audit_trigger`
- [x] `upsert` с `on_conflict` в импорте выписок (вместо DELETE+INSERT)
- [x] Data Governance DR1/DR2/DR3 задокументированы
- [x] Принцип ENMV задокументирован

### Sprint 4 — 2026-05-01
- [x] Таблица `visit_records` — фактические выходы под запись
- [x] Таб "Статус проверок" — автоматические проверки shifts/payroll/visit_records
- [x] Незакрытые периоды ФОТ — оранжевая плашка
- [x] Переход к следующему периоду после закрытия всех выплат
- [x] UNIQUE constraint на `bank_transactions` и `personal_transactions`
- [x] ФОТ в P&L → метод начисления из `payroll.total_accrued`
- [x] Парсер notes два формата (стандартный и произвольный)
- [x] Принципы Клеппмана задокументированы
- [x] Модель зрелости аналитики L1-L4 задокументирована

### Модуляризация frontend — 2026-05-01
- [x] `static/v2/index.html` (2472 строки) → `static/v3/js/` (14 модулей)
- [x] `index.html` — только HTML (726 строк)
- [x] `MONTHS_RU` дубли → единая константа в `config.js`
- [x] `window.*` флаги → `let` в `router.js`
- [x] Система знаний: `README_AI.md`, `ARCHITECTURE.md`, `SESSION_LOG.md`, `KNOWLEDGE_SYNC_PROMPT.md`, `KNOWLEDGE_HARVEST_PROMPT.md`

---

## 🔧 Следующая сессия — начать с этого

1. Дизайн виджета онлайн-записи — мобильный, современный, с анимацией
2. Интеграция ЮKassa — реальная оплата предоплаты 2000₽
3. widget.js для встройки в Tilda через iframe
4. **P0 бэклог:** Перевыпустить YCLIENTS Partner Token

## 📋 Dev Log — логирование сессий

После каждой сессии логировать в Dev Log через curl:

```bash
curl -X POST https://insalon.onrender.com/dev-sessions \
  -H "Content-Type: application/json" \
  -d '{"date":"YYYY-MM-DD","feature":"Название задачи","category":"dev","duration_min":120,"tokens_approx":50000,"notes":"..."}'
```

Категории: `dev` / `design` / `analytics`
Просмотр: https://insalon.onrender.com/dev-sessions/stats

## Безопасность виджета записи [P1]

### booking_id enumeration attack
- Текущая проблема: GET /booking/booking/56 доступен без авторизации — можно перебирать ID и смотреть чужие записи
- Решение: добавить `access_token` (UUID) в таблицу bookings при создании
- Возвращать токен в response createBooking → хранить в URL как /booking/?token=UUID
- Эндпоинт GET /booking/booking/{id} требует совпадения token
- Success экран работает по токену, не по числовому ID

### Дополнительно
- Rate limiting на /booking/create (макс 5 запросов в минуту с одного IP)
- Webhook от ЮKassa валидировать по IP whitelist

## Magic Link / личный кабинет записи [P2]
- Уникальная ссылка по booking_id без авторизации
- История визита, рекомендации мастера, чаевые, повторная запись
- iOS Wallet / PKPass
- Скачать чек
- Оставить отзыв

## html2canvas — Сохранить как изображение [P2]
- Реализовать кнопку на Success экране
