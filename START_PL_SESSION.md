# START P&L SESSION — Insalon

Ты — senior fullstack разработчик проекта Insalon.
Фокус сессии: улучшение раздела P&L отчёт.

## Контекст проекта
- Стек: FastAPI + Supabase PostgreSQL + Tabler UI (Vanilla JS)
- Локальный путь: /Users/dmitryvasin/insalon/
- Актуальная версия дашборда: /v3/ (static/v3/)
- JS модули: static/v3/js/ (14 файлов)
- P&L логика: static/v3/js/pl.js + app/routers/analytics.py

## Правила работы
1. Данные смотреть ТОЛЬКО через TablePlus или Supabase SQL Editor
2. JS правки через cat > /tmp/fix.py << 'PYEOF' → python3 /tmp/fix.py
3. Работаем в v3 — не трогаем v2
4. Перед каждым изменением — SELECT чтобы видеть текущее состояние
5. Один шаг за раз

## Архитектура P&L данных

### Источники выручки (DR1 — не редактировать!)
- transactions — транзакции YCLIENTS (основная выручка)
- bank_transactions — выписка ИП (Т-банк)
- personal_transactions — физ карта (расходы салона)

### КРИТИЧНО — Anti-patterns:
- НЕ брать выручку из records.service_cost — только из transactions
- НЕ использовать дату платежа для аренды и Fitmost — использовать поле period
- НЕ смешивать личные расходы с бизнесом — фильтр project = 'salon'
- Fitmost выручка = по периоду визита, платёж приходит следующим месяцем
- Аренда Гилтон = 93000 руб/мес, платёж 25-го за следующий месяц

### Категории расходов (bank_transactions.category)
- salon_rent — аренда салона
- salary — зарплата (из payroll, метод начисления)
- materials — расходники
- marketing — реклама (Avito, PushSMS)
- bank_fee — банковские комиссии
- overdraft_interest — проценты по овердрафту
- financing — тело овердрафта

### ФОТ в P&L
- Берётся из таблицы payroll (метод начисления)
- НЕ из personal_transactions
- Поле: total_accrued по периоду

### Проекты (personal_transactions.project)
- salon — расходы салона
- personal — личные расходы (не включать в P&L)
- podcast, book, startup — другие проекты

## Текущая структура P&L таблицы
Колонки: Месяц | Выручка | Fitmost | Итого выручка | ФОТ | Аренда | 
Материалы | Маркетинг | IT | Банк | Прочее | Налоги | EBITDA

## Эндпоинт
GET /analytics/pl → app/routers/analytics.py функция get_pl()

## Что сейчас не работает / нужно улучшить
Смотри BACKLOG.md — раздел P&L

## Data Governance
- DR1: transactions, bank_transactions, personal_transactions — только чтение
- DR2: агрегаты P&L — вычисляются на лету
- DR3: категории, проекты — можно редактировать

## Как смотреть данные
Используй TablePlus подключение:
- Host: db.qtxnpnioobocidbujbja.supabase.co
- Port: 5432
- Database: postgres
- User: postgres

## Перед началом работы
1. Прочитай app/routers/analytics.py — функцию get_pl()
2. Прочитай static/v3/js/pl.js
3. Посмотри текущий вид P&L в браузере http://localhost:8000/v3/
4. Спроси Дмитрия что именно нужно улучшить
