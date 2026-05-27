---
Generated: 2026-05-27
Version: 2.0
Next review: после каждой новой сессии разработки
---

# AI_PROJECT_BRIEF — Insalon

## 1. PROJECT IDENTITY

- **Название:** Insalon
- **Тип:** Персональный управленческий дашборд владельца HeadSPA салона
- **Ниша:** HeadSPA + SPA салон (Москва)
- **Главная цель:** Единый дашборд для управления бизнесом — P&L, сотрудники, обязательства, идеи/проекты
- **Текущая фаза:** production (активно используется)
- **API:** https://insalon.onrender.com
- **GitHub:** https://github.com/dvasincom-sketch/insalon
- **Локальная разработка:** `/Users/dmitryvasin/insalon/` (Mac OS, Python venv)

---

## 2. TECH STACK

### Frontend
- **Tabler UI** (Bootstrap 5) — дашборд `static/v3/`
- **ApexCharts** — графики
- **Vanilla JS** — без фреймворков, fetch API
- Основные JS файлы: `router.js`, `pl.js`, `schedule.js`, `staff.js`, `obligations.js`, `ideas.js`

### Backend
- **Python 3.11** + **FastAPI**
- **Supabase Python SDK**
- **httpx** — YCLIENTS API клиент
- Роутеры: `analytics.py`, `payroll.py`, `sync.py`, `obligations.py`

### База данных
- **Supabase PostgreSQL**
- Company ID: **1166484**
- RLS: включён на `hypotheses` (policy "allow all"), остальные таблицы без RLS

### Инфраструктура
- **Render** — хостинг (insalon.onrender.com), автодеплой из GitHub main
- **GitHub Actions** — daily-sync.yml, запуск в 00:00 UTC (03:00 МСК)
- **Mac OS** — локальная разработка

### Внешние интеграции
- **YCLIENTS API** — записи, транзакции, клиенты, услуги, сотрудники
  - Partner Token: Oh9H0Xglx8Q1c52t2DO4
  - Company ID: 1166484
- **Fitmost** — агрегатор, скидка 35%, платежи следующего месяца
- **Т-банк** — расчётный счёт ИП + физическая карта
- **Яндекс.Касса (ЮKassa / Аванпост)** — эквайринг

---

## 3. ARCHITECTURE MAP

| Модуль | Назначение | Статус |
|--------|-----------|--------|
| `app/routers/analytics.py` | Все аналитические эндпоинты `/analytics/*` | done |
| `app/routers/payroll.py` | Расписание смен, расчёт ФОТ `/payroll/*` | done |
| `app/routers/sync.py` | Синхронизация YCLIENTS `/sync/*` | done |
| `app/routers/obligations.py` | Обязательства `/obligations/*` | done |
| `app/yclients.py` | YCLIENTS API клиент | done |
| `app/database.py` | Supabase клиент, save функции | done |
| `static/v3/index.html` | Главный дашборд | done |
| `static/v3/js/router.js` | Навигация между разделами | done |
| `static/v3/js/pl.js` | P&L отчёт | done |
| `static/v3/js/schedule.js` | Расписание и парные программы | done |
| `static/v3/js/staff.js` | Эффективность сотрудников | done |
| `static/v3/js/obligations.js` | Обязательства и платежи | done |
| `static/v3/js/ideas.js` | Раздел Идеи/Проекты | done |
| `.github/workflows/daily-sync.yml` | Ежедневная синхронизация | done |

---

## 4. РАЗДЕЛЫ ДАШБОРДА

### Пульс системы
- KPI карточки: выручка, визиты, клиенты за 30 дней
- North Star: CM/LH (прибыль на оплаченный час)
- График выручки по неделям с drill-down
- Парные программы — список дней где нужен второй мастер

### Идеи (новый раздел, 2026-05-27)
- Таблица бизнес-гипотез и проектов
- Колонки: тип, сроки, фокус, CapEx план, прибыль план, статус
- Модал с PRD: проблема, результат, MVP, риск, ключевые результаты
- Свободные строки CapEx (статья + сумма)
- Связь с P&L через `project_key` — фактические расходы/доходы из транзакций
- Добавление через интерфейс (модал)
- Хранение: таблица `hypotheses` в Supabase

### P&L
- Проекты: salon, podcast, book, consulting, personal, internal
- Для салона: колонки Услуги/Сертиф./Абон./Fitmost/ФОТ/Аренда/Космет./Матер./Маркет./Банк
- Для других проектов: колонки ФОТ/Аренда/Продакшн/Маркет./Прочее
- Итог инвестиций под таблицей (для проектов без выручки)
- Детализация по клику на ячейку (модал с транзакциями)
- Фильтрация детализации по `project` — не смешивать салон с подкастом
- Таб Транзакции — inline редактирование категории и проекта
- Таб Сверка — план vs факт по match_rule

### Сотрудники
- Эффективность: коэффициент выручка/смена, прибыльные/убыточные смены
- Расписание: календарь смен, парные программы, назначение второго мастера
- Оплата труда: ведомость с периодами 1–14 и 15–31
- ФОТ: расчёт с учётом авансов

### Обязательства
- График платежей на месяц с автоматическим матчингом транзакций
- `match_rule` (regex) + `match_source` (bank/personal/both) + диапазон суммы
- ФОТ на 1-е = плановый ФОТ 15–31 минус авансы выплаченные за этот период
- Статусы: Оплачен / Просрочен / Ожидается / Долг

---

## 5. КЛЮЧЕВЫЕ ТАБЛИЦЫ SUPABASE

| Таблица | Назначение |
|---------|-----------|
| `records` | Записи клиентов из YCLIENTS |
| `transactions` | Транзакции из YCLIENTS (оплаты услуг) |
| `bank_transactions` | Банковская выписка ИП (Т-банк) |
| `personal_transactions` | Выписка физ карты |
| `shifts` | Расписание смен (заполняется вручную) |
| `payroll` | Ведомость оплаты труда по периодам |
| `staff_payment_aliases` | Алиасы мастеров для матчинга авансов |
| `obligations` | Обязательства и долги |
| `hypotheses` | Бизнес-гипотезы и проекты (новая) |
| `salons` | Данные салона и токен YCLIENTS |

### Поля obligations
`id, company_id, type, project, expense_category, description, amount, day_of_month, is_active, notes, start_date, end_date, last_payment_date, match_rule, match_source, match_amount_min, match_amount_max`

### Поля hypotheses
`id, company_id, name, tag, segment, pain_level, market_size, monetization, risk_text, risk_level, status, score, prd_problem, prd_outcome, prd_kr, prd_mvp, prd_diff, prd_risk, prd_data, doc_url, project_type, date_start, date_end, focus_level, capex_items (jsonb), capex_total, expected_profit_monthly, expected_profit_onetime, profit_type, project_key`

---

## 6. ПРОЕКТЫ В ТРАНЗАКЦИЯХ

| project_key | Название | Описание |
|-------------|---------|---------|
| salon | Салон HeadSPA | Основной бизнес |
| podcast | Подкаст (NOISHA) | Категории: salary/production/rent/marketing/team |
| book | Книга | Творческий актив |
| consulting | Консалтинг | — |
| personal | Личное | Личные расходы |
| internal | Внутренние | Переводы между счетами |

### Категории расходов подкаста
- `salary` — продюсер (договор 502/1, 35 000₽/мес)
- `production` — монтаж, съёмка
- `rent` — аренда студии (счета-договоры)
- `marketing` — реклама, Kwork
- `team` — гонорары команде (Фатимат, Надежда, Андрей и др.)

---

## 7. СИНХРОНИЗАЦИЯ

### GitHub Actions daily-sync.yml (00:00 UTC)
1. `GET /sync/recent` — записи за последние 3 дня + транзакции
2. `sleep 60`
3. `GET /sync/records-now?date_from=TODAY&date_to=TODAY+7d` — будущие записи
4. `GET /sync/transactions-now` — транзакции за 365 дней

### Ручная синхронизация
```bash
curl "https://insalon.onrender.com/sync/records-now?date_from=2026-05-01&date_to=2026-05-31"
curl "https://insalon.onrender.com/sync/transactions-now"
```

---

## 8. РЕШЕНИЯ И АНТИ-ПАТТЕРНЫ

### Ключевые решения
- **Выручка из `transactions` (YCLIENTS)**, не из `records.service_cost` — точнее
- **Fitmost и аренда** учитываются по `period`, не по дате платежа
- **Расписание смен** — таблица `shifts` (вручную), не из YCLIENTS API
- **Абонементы** в отчёте мастера = прайс × 0.7 (скидка 30%)
- **Парные программы** — второй мастер (`is_visit_only=True`) может добавляться несколько раз в день (исправлен баг 2026-05-27)
- **Авансы** вычитаются из ФОТ на 1-е через `staff_payment_aliases`
- **P&L для не-салонных проектов** — отдельные колонки, детализация фильтруется по `project`
- **Пагинация Supabase** — `fetch_all` обязателен (лимит 1000 строк)
- **Транзакции** — пагинация до последней страницы (не останавливаться на `len < 100`)

### Анти-паттерны
- Не брать выручку из `records.service_cost`
- Не смешивать личные расходы с бизнесом в P&L
- Не считать выплаты 1-го как зарплату текущего месяца
- Не использовать дату платежа для аренды и Fitmost
- Не делать детализацию P&L без фильтра по `project`
- Не обновлять статус обязательств вручную через SQL если есть `match_rule`
- Не использовать `bootstrap.Modal` — в Tabler нативный подход

---

## 9. КАК ДАВАТЬ КОМАНДЫ CLAUDE

- Команды для изменения файлов: всегда через `python3 -c` или `cat > /tmp/fix.py << 'PYEOF'` — никогда не скачивать файл
- Путь к роутерам: `/Users/dmitryvasin/insalon/app/routers/`
- Путь к JS: `/Users/dmitryvasin/insalon/static/v3/js/`
- Деплой: `git add ... && git commit -m "..." && git push origin main`
- Локальный сервер: `uvicorn app.main:app --reload --port 8000`
- Перезапуск: `lsof -ti:8000 | xargs kill -9 && sleep 2 && uvicorn app.main:app --reload --port 8000`

---

## 10. DEV LOG

Логирование сессий: `POST https://insalon.onrender.com/dev-sessions`

```json
{
  "date": "2026-05-27",
  "feature": "Название задачи",
  "category": "dev",
  "duration_min": 120,
  "tokens_approx": 50000,
  "notes": "Заметки"
}
```

### Последние сессии
| Дата | Фича | Мин | Токены |
|------|------|-----|--------|
| 2026-05-27 | Парные программы fix + Ideas раздел + P&L подкаст + Обязательства авансы | 240 | 180 000 |