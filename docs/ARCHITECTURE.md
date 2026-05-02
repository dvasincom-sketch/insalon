# ARCHITECTURE.md
> Insalon — SaaS аналитика для HeadSPA салона поверх YCLIENTS  
> Последнее обновление: май 2026

---

## Структура frontend

```
static/v2/
├── index.html        ← только HTML-разметка + <script src> теги, без инлайн JS
└── js/
    ├── config.js     ← константы и справочники
    ├── utils.js      ← форматирование
    ├── api.js        ← транспортный слой
    ├── router.js     ← навигация между экранами
    ├── pulse.js      ← экран "Пульс системы"
    ├── pl.js         ← экран "P&L"
    ├── staff.js      ← экран "Сотрудники / Эффективность"
    ├── schedule.js   ← таб "Расписание" + таб-навигация
    ├── payroll.js    ← таб "Ведомость"
    ├── checks.js     ← таб "Проверки"
    ├── obligations.js← экран "Обязательства"
    ├── modal.js      ← drill-down модал (клик по неделе → детали)
    ├── fot.js        ← расчёт ФОТ (самый крупный модуль)
    └── main.js       ← точка входа, вызывает init()
```

---

## Порядок подключения скриптов (критичен)

```html
<!-- Внешние библиотеки — до наших модулей -->
<script src="apexcharts"></script>
<script src="tabler.min.js"></script>

<!-- Наши модули — строго в этом порядке -->
<script src="js/config.js"></script>   <!-- 1. Константы — нужны всем -->
<script src="js/utils.js"></script>    <!-- 2. Форматирование — нужно всем -->
<script src="js/api.js"></script>      <!-- 3. fetchData — нужен всем экранам -->
<script src="js/router.js"></script>   <!-- 4. showScreen — нужен навигации -->
<!-- экраны могут идти в любом порядке между собой -->
<script src="js/pulse.js"></script>
<script src="js/pl.js"></script>
<script src="js/staff.js"></script>
<script src="js/schedule.js"></script> <!-- вызывает loadFotData() из fot.js -->
<script src="js/payroll.js"></script>
<script src="js/checks.js"></script>
<script src="js/obligations.js"></script>
<script src="js/modal.js"></script>
<script src="js/fot.js"></script>      <!-- должен быть ДО main.js -->
<script src="js/main.js"></script>     <!-- последний — точка входа -->
```

> ⚠️ Используем обычные `<script>` теги (не `type="module"`).  
> Все функции глобальны. Порядок подключения = порядок зависимостей.

---

## Модули: ответственность и зависимости

### `config.js`
**Экспортирует (глобально):** `API`, `TODAY`, `YEAR`, `MONTH`, `MONTHS_RU`, `MONTHS_RU_LC`, `STAFF_COLORS`  
**Зависит от:** ничего  
**Правило:** только константы, никакой логики

### `utils.js`
**Экспортирует:** `formatMoney(n)`, `formatK(n)`  
**Зависит от:** ничего  
**Правило:** чистые функции, без side effects

### `api.js`
**Экспортирует:** `fetchData(url)`  
**Зависит от:** `API` из config.js  
**Правило:** единственное место где происходит `fetch`. Все остальные модули используют только `fetchData`.

### `router.js`
**Экспортирует:** `showScreen(name)`  
**Зависит от:** `loadPL`, `loadStaff`, `loadObligations` (из соответствующих модулей)  
**Содержит:** флаги lazy-load (`let plLoaded`, `staffLoaded`, `oblLoaded`)  
**Правило:** `window.*` флаги запрещены — только локальные `let`

### `fot.js`
**Экспортирует:** `loadFotData()`, `fotData`, `fotPeriod` + все функции управления ФОТ  
**Зависит от:** `fetchData`, `formatMoney`, `formatK`, `TODAY`, `YEAR`, `MONTH`, `MONTHS_RU_LC`  
**Стейт:** `let fotData = {}` и `let fotPeriod = {}` — глобальные переменные модуля  
**Правило:** единственный модуль где разрешён изменяемый глобальный стейт (fotData/fotPeriod)

---

## Архитектурные решения и причины

| Решение | Причина |
|---|---|
| Без ES modules (`import/export`) | Проект обслуживается через простой файловый сервер, нет билд-процесса |
| `MONTHS_RU` в `config.js` | Был задублирован в 3 местах в оригинале — единый источник правды |
| `window.plLoaded` → `let plLoaded` в router.js | Глобальное пространство имён не загрязняем без необходимости |
| `#payment-modal` только в DOM | В оригинале был "дубль" внутри `printFotStaff()` — это отдельный документ для `window.open()`, не дубль |
| Lazy-load экранов P&L / Staff / Obligations | Тяжёлые запросы не делаются при старте — только при первом открытии таба |

---

## Что планируется (следующие шаги)

- [ ] Перейти на ES modules (`type="module"`) после стабилизации
- [ ] Вынести хардкод имён сотрудников из `staff.js` в `config.js`
- [ ] Заменить `Math.random()` в heatmap на реальные данные загрузки
- [ ] Добавить централизованный error handler в `api.js`

---

## Виджет онлайн-записи
static/booking/          ← React + Vite SPA
├── src/
│   ├── api/booking.js   ← все запросы к FastAPI /booking/*
│   ├── pages/
│   │   ├── Categories.jsx
│   │   ├── Services.jsx
│   │   ├── Extras.jsx
│   │   ├── DateTime.jsx
│   │   ├── Master.jsx
│   │   ├── Contacts.jsx
│   │   └── Success.jsx
│   └── App.jsx          ← роутер между шагами
└── package.json

**Запуск локально:** `cd static/booking && npm run dev` → http://localhost:5174/  
**API эндпоинты:** `/booking/categories`, `/booking/services`, `/booking/slots`, `/booking/staff`, `/booking/nearest_slot`, `/booking/create`, `/booking/booking/{id}`  
**Таблицы БД:** `bookings`, `leads`, `service_categories`  
**Стейт флоу:** categories → services → extras → datetime → master → contacts → success  
**YCLIENTS интеграция:** POST через `run_in_executor` (синхронный httpx внутри async FastAPI)

---

## Оплата (ЮKassa)

**Роутер:** `app/routers/payments.py`  
**Режим:** тестовый (`test_` ключ), редирект на страницу ЮKassa  
**Переменные окружения:** `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`  
**Флоу:** POST `/booking/create` → создаёт платёж → редирект на ЮKassa → webhook `/payments/webhook` → обновляет `bookings.status`  
**Webhook события:** `payment.succeeded`, `payment.canceled`  
**Return URL:** `https://insalon.onrender.com/booking/?booking_id={id}`  

### Переход на боевой режим
1. Заменить `YOOKASSA_SECRET_KEY` на боевой ключ в Render env vars
2. В личном кабинете ЮKassa добавить webhook: `https://insalon.onrender.com/payments/webhook`
3. События: `payment.succeeded`, `payment.canceled`

## YCLIENTS API — использование в виджете

| Эндпоинт | Назначение |
|---|---|
| `/book_times/{company_id}/{staff_id}/{date}` | Свободные слоты для услуги |
| `/clients/{company_id}` POST | Создание клиента |
| `/records/{company_id}` POST | Создание записи |
| `staff_id=0` | Любой доступный мастер |

**Важно:** POST запросы к YCLIENTS через `run_in_executor` (синхронный httpx) из-за конфликта anyio event loop.
