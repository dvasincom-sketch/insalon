# ⚠️ DEPRECATED — START_SESSION_PROMPT.md

Этот файл устарел. Содержимое перенесено в:

- **Общая DEV сессия** → `docs/sessions/START_DEV_SESSION.md`
- **P&L сессия** → `docs/sessions/START_PL_SESSION.md`

Файл сохранён как архив. Не использовать для старта новых сессий.

---
# [АРХИВ] START SESSION PROMPT — Insalon

Ты — senior fullstack разработчик и системный аналитик проекта Insalon.

Перед началом работы прочитай два документа:
1. AI_PROJECT_BRIEF.md
2. PRODUCT_ROADMAP.md

Оба файла находятся в корне репозитория:
https://github.com/dvasincom-sketch/insalon

## Быстрый контекст

**Проект:** Insalon — SaaS аналитика для HeadSPA салона поверх YCLIENTS
**Стек:** FastAPI + Supabase PostgreSQL + Tabler UI (Vanilla JS)
**Локальный путь:** /Users/dmitryvasin/insalon/
**API:** https://insalon.onrender.com
**GitHub:** https://github.com/dvasincom-sketch/insalon

## Правила работы

1. **Данные смотреть только через SQL в Supabase SQL Editor** — никогда не через curl/терминал
2. **Файлы редактировать через `python3 - << 'PYEOF'`** — zsh ломает grep и heredoc со спецсимволами
3. **Временные скрипты писать в /tmp/** — `cat > /tmp/fix.py << 'PYEOF'` затем `python3 /tmp/fix.py`
4. **Не перезаписывать достоверные данные** — только дополнять через новые поля/записи
5. **Деплой только после локальной проверки** — сначала тестируем на localhost:8000

## Data Governance (Solid-Finance)

| Таблица | Уровень | Правило |
|---|---|---|
| bank_transactions | DR1 | Только INSERT, запрещён UPDATE/DELETE |
| personal_transactions | DR1 | Только INSERT, запрещён UPDATE/DELETE |
| transactions | DR1 | Только INSERT, запрещён UPDATE/DELETE |
| records | DR1 | Только INSERT, запрещён UPDATE/DELETE |
| shifts | DR2 | Вводится вручную по расписанию |
| visit_records | DR2 | Вводится вручную по выходам под запись |
| payroll | DR2/DR3 | balance = auto (триггер), не редактировать вручную |
| payroll_audit | DR2 | Автоматический лог всех изменений payroll |

## Текущий статус данных

- ✅ Данные внесены: январь, февраль, март, апрель 1–14 (все мастера)
- 🔄 В процессе: апрель 15–30 (Расчёт ФОТ, выплата 1 мая)
- ❌ Не внесено: декабрь 2025

## Ближайшие задачи

1. Завершить Расчёт ФОТ апрель 15–30 (Светлана, Екатерина, Анастасия, Анна)
2. Автоматизация привязки выплат из personal_transactions к мастерам (staff_payment_aliases)
3. Utilization heatmap
4. Bridge Conversion SPA→Массаж
5. Расширить фильтр парных программ (добавить SPA для мужчин и другие услуги)

## Критичные anti-patterns

- ❌ Не брать выручку из records.service_cost
- ❌ Не смешивать личные расходы с бизнесом
- ❌ Не использовать ?t= cache-bust
- ❌ Не объявлять const/let после использования
- ❌ zsh ломает grep со скобками — использовать python3
- ❌ Не редактировать balance вручную — только через total_accrued и total_paid
- ❌ Не перезаписывать DR1 данные (bank_transactions, personal_transactions, transactions, records)
- ❌ Не использовать bootstrap.Modal — в Tabler нативный подход
- ❌ Не использовать dataPointSelection в ApexCharts — использовать markerClick

## Новые таблицы (добавлены 30.04.2026)

- `staff_payment_aliases` — маппинг имён мастеров к описаниям в выписке
- `payroll_audit` — лог изменений payroll
- `payroll.offset_amount` — зачёт авансов из предыдущих периодов
- `payroll.status` — draft/paid флоу
- `shifts.is_visit_only` — выход под запись (не полная смена)

## Триггеры БД

- `payroll_balance_trigger` — автопересчёт balance = total_accrued - total_paid
- `payroll_audit_trigger` — логирование всех изменений payroll
