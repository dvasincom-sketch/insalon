# BACKLOG — Insalon
> Единый источник истины. Обновляется после каждой сессии.
> Последнее обновление: 01.05.2026

## P0 — Критичные (блокируют работу)

- [ ] Внести исторические данные payroll за 2025 год (146 смен: Александра, Ольга, Светлана, Екатерина, Анна, Татьяна) → DEV сессия
- [ ] Перевыпустить YCLIENTS Partner Token (засвечен в репозитории!) → DEV сессия
- [ ] Исправить balance Марии январь (5500₽ при status=paid) → DEV сессия

## P1 — Важные (следующий спринт)

### Data & Analytics
- [ ] L2 Event-Driven: воронка клиента через attendance (Cancel Rate, No-Show Rate) → ANALYTICS → DEV
- [ ] Bridge Conversion SPA→Массаж — измерение конверсии → ANALYTICS → DEV
- [ ] Utilization heatmap с реальными данными из shifts → DEV

### ФОТ & Payroll
- [ ] Автоматизация привязки выплат из personal_transactions к мастерам (staff_payment_aliases) → DEV
- [ ] visit_pay в payroll вычислять динамически из visit_records (не хранить отдельно) → ANALYTICS → DEV
- [ ] Расширить фильтр парных программ (SPA для мужчин и др.) → DEV

### Качество данных
- [ ] Неизвестные получатели в personal_transactions (Юлия С., Мирзамагомед М. и др.) → DEV
- [ ] Проверка 4 из checks.py — смены без payroll за 2025 добавить как автопроверку → DEV

## P2 — Желательные (следующие спринты)

### Системные принципы Клеппмана
- [ ] Least Privilege — RLS в Supabase по ролям → ANALYTICS → DEV
- [ ] Наблюдаемость — health dashboard (% синхронизации YCLIENTS, gaps в данных) → ANALYTICS → DEV
- [ ] Resilience — retry логика в YCLIENTS клиенте (Circuit Breaker) → DEV
- [ ] Webhook обработка удалённых записей YCLIENTS → DEV

### Аналитика
- [ ] L3 Unit-Economic Modeling — сценарный P&L (что если ставка 6000₽?) → PRODUCT → ANALYTICS → DEV
- [ ] L4 Behavioral Nudges — триггеры реактивации клиентов → PRODUCT → ANALYTICS → DEV
- [ ] Многоуровневый P&L с проектами → DEV

### Инфраструктура
- [ ] Cron автосинхронизация данных YCLIENTS → DEV
- [ ] Данные за декабрь 2025 (выписка физ карты отсутствует) → DEV

## ✅ Сделано (архив)

### Сессия 30.04.2026
- [x] Payroll январь 2026 — все мастера (shifts, visit_records, payroll)
- [x] Таб 🧮 Расчёт ФОТ — полный цикл draft→paid→ведомость
- [x] Кнопка печати чека PDF
- [x] Колонка "Зачёт" в ведомости оплаты труда
- [x] Data Governance: триггер balance, audit trail, защита DR1
- [x] Новые таблицы: staff_payment_aliases, payroll_audit
- [x] Принцип ENMV задокументирован

### Сессия 01.05.2026
- [x] Таб периодов в ФОТ — оранжевая плашка незакрытых периодов
- [x] Переход к следующему периоду после закрытия всех выплат
- [x] Модальное окно выплаты с выбором наличные/безнал
- [x] Расписание мая 1–14 внесено в shifts
- [x] Идемпотентность импорта — upsert в import_bank.py и import_personal.py
- [x] UNIQUE constraint на bank_transactions и personal_transactions
- [x] Принципы Клеппмана задокументированы
- [x] Модель зрелости аналитики L1-L4 задокументирована
- [x] Три специализированных промта: DEV, ANALYTICS, PRODUCT

## 🔧 Следующая сессия — начать с этого

1. Настроить TablePlus — подключение к Supabase PostgreSQL
   - Host: db.qtxnpnioobocidbujbja.supabase.co
   - Port: 5432 / Database: postgres / User: postgres
   - Password: найти в Supabase Project Settings → Database

2. Настроить алиасы в ~/.zshrc
   - insalon = cd + activate venv
   - rundev = uvicorn app.main:app --reload

3. Настроить SQLTools в VS Code (расширение установлено)

4. Перейти к P0 задачам из backlog:
   - Исторические данные payroll за 2025 год
   - Исправить balance Марии январь
   - Перевыпустить YCLIENTS Partner Token
