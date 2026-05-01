# START P&L SESSION — Insalon

Ты — senior fullstack разработчик проекта Insalon.
Фокус сессии: улучшение раздела P&L отчёт.

## Контекст
- **Стек:** FastAPI + Supabase PostgreSQL + Tabler UI (Vanilla JS)
- **Локальный путь:** /Users/dmitryvasin/insalon/
- **Актуальная версия:** /v3/ (static/v3/)
- **P&L логика:** `static/v3/js/pl.js` + `app/routers/analytics.py` → `get_pl()`
- **Эндпоинт:** `GET /analytics/pl`

> ⚠️ static/v2/ — устаревшая версия. Всю работу вести только в static/v3/

---

## Перед началом работы

1. Прочитай `app/routers/analytics.py` — функцию `get_pl()`
2. Прочитай `static/v3/js/pl.js`
3. Посмотри текущий вид P&L в браузере `http://localhost:8000/v3/`
4. Уточни у Дмитрия что конкретно нужно улучшить

---

## Архитектура P&L данных

### Источники выручки (DR1 — только чтение!)
| Таблица | Что содержит |
|---|---|
| `transactions` | Транзакции YCLIENTS — основная выручка |
| `bank_transactions` | Выписка ИП Т-банк |
| `personal_transactions` | Физ карта — расходы салона (фильтр: `project = 'salon'`) |

### Критичные Anti-patterns
- ❌ **НЕ** брать выручку из `records.service_cost` — только из `transactions`
- ❌ **НЕ** использовать дату платежа для аренды и Fitmost — использовать поле `period`
- ❌ **НЕ** смешивать личные расходы с бизнесом — фильтр `project = 'salon'`

### Нюансы источников
- **Fitmost выручка** = по периоду визита, платёж приходит следующим месяцем
- **Аренда Гилтон** = 93 000 руб/мес, платёж 25-го за следующий месяц
- **ФОТ в P&L** = из таблицы `payroll` (метод начисления, поле `total_accrued`), **НЕ** из `personal_transactions`

### Категории расходов (bank_transactions.category)
| Категория | Что включает |
|---|---|
| `salon_rent` | Аренда салона |
| `salary` | Зарплата (из payroll, метод начисления) |
| `materials` | Расходники |
| `marketing` | Реклама (Avito, PushSMS) |
| `bank_fee` | Банковские комиссии |
| `overdraft_interest` | Проценты по овердрафту |
| `financing` | Тело овердрафта |

### Проекты (personal_transactions.project)
| Проект | Включать в P&L? |
|---|---|
| `salon` | ✅ Да |
| `personal` | ❌ Нет |
| `podcast`, `book`, `startup` | ❌ Нет |

---

## Текущая структура P&L таблицы

```
Месяц | Выручка услуги | Fitmost | Сертификаты | Абонементы 
| Итого выручка | ФОТ | Аренда | Материалы | Маркетинг 
| IT | Банк | Прочее | Налоги | EBITDA
```

---

## Data Governance в контексте P&L

| Уровень | Таблицы | Правило |
|---|---|---|
| DR1 | transactions, bank_transactions, personal_transactions | Только чтение |
| DR2 | Агрегаты P&L | Вычисляются на лету, не хранятся |
| DR3 | Категории, проекты | Можно редактировать |

---

## Подключение к БД (TablePlus)
```
Host:     db.qtxnpnioobocidbujbja.supabase.co
Port:     5432
Database: postgres
User:     postgres
Password: Supabase → Project Settings → Database
```

---

## Текущие задачи по P&L
Смотри `BACKLOG.md` → раздел Data & Analytics
