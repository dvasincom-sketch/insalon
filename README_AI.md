# README_AI.md — Навигатор по знаниям проекта Insalon
> Это первый файл который нужно прочитать в любой новой AI-сессии.
> Здесь нет деталей — только маршруты к нужным документам.

---

## Что такое Insalon
SaaS аналитика для HeadSPA салона поверх YCLIENTS.  
Backend: Python/FastAPI + Supabase. Frontend: vanilla JS, Tabler UI, ApexCharts.  
GitHub: https://github.com/dvasincom-sketch/insalon

**Актуальная версия frontend:** `static/v3/` (v2 устарела, не трогать)

---

## С чего начать сессию

| Ты пришёл чтобы... | Прочитай сначала |
|---|---|
| Спроектировать фичу / обновить backlog | `AI_PROJECT_BRIEF.md` → `BACKLOG.md` → `docs/sessions/START_ANALYTICS_SESSION.md` |
| Написать или починить код (общее) | `docs/ARCHITECTURE.md` → `docs/sessions/START_DEV_SESSION.md` |
| Работать с P&L отчётом | `docs/sessions/START_PL_SESSION.md` |
| Работать с данными / SQL / Supabase | `AI_PROJECT_BRIEF.md` → `docs/sessions/START_DEV_SESSION.md` |
| Продуктовые решения / roadmap | `PRODUCT_ROADMAP.md` → `docs/sessions/START_PRODUCT_SESSION.md` |
| Синхронизировать новый чат с проектом | `docs/KNOWLEDGE_SYNC_PROMPT.md` |
| Понять что менялось и когда | `docs/SESSION_LOG.md` |

---

## Карта всех документов

### Корень проекта — стратегия и задачи
```
AI_PROJECT_BRIEF.md      — контекст проекта, принципы, схема БД
PRODUCT_ROADMAP.md       — уровни зрелости L1→L4, планы
BACKLOG.md               — текущие задачи по приоритету (P0/P1/P2)
README_AI.md             — этот файл (маршрутизатор)
```

### docs/ — архитектура и знания
```
docs/ARCHITECTURE.md          — структура JS модулей v3, зависимости, решения
docs/SESSION_LOG.md           — хронология архитектурных решений
docs/KNOWLEDGE_SYNC_PROMPT.md — промпт для синхронизации нового чата
```

### docs/sessions/ — промпты для старта сессий по ролям
```
docs/sessions/START_ANALYTICS_SESSION.md  — аналитик: ТЗ, backlog, принципы
docs/sessions/START_DEV_SESSION.md        — разработка: код, SQL, деплой (v3)
docs/sessions/START_PL_SESSION.md         — P&L отчёт: данные, логика, источники
docs/sessions/START_PRODUCT_SESSION.md    — продукт: метрики, воронки, unit-economics
docs/sessions/START_SESSION_PROMPT.md     — [DEPRECATED] заменён на START_DEV_SESSION.md
```

---

## Ключевые принципы

**Data Governance:** DR1 Sacred (только INSERT) → DR2 Calculated (через UI) → DR3 Manual (свободно)  
**ENMV:** любое число в БД должно быть видно в UI  
**Модель зрелости:** L1 Descriptive ✅ → L2 Event-Driven 🔄 → L3 Unit-Economic 📋 → L4 Behavioral 📋  

Детали: `AI_PROJECT_BRIEF.md`

---

## Правило обновления документов

После каждой сессии с изменениями:
1. Добавить запись в `docs/SESSION_LOG.md`
2. Обновить `docs/ARCHITECTURE.md` если изменилась структура модулей
3. Обновить `BACKLOG.md` — закрыть выполненное, добавить новое
4. Этот файл обновлять только если добавился новый документ или сменилась актуальная версия
