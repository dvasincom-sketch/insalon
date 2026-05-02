# Dev Log — инструкция для логирования сессии

После каждой рабочей сессии нужно залогировать затраченное время и токены в **Dev Log** дашборда Insalon.

## API endpoint

```
POST https://insalon.onrender.com/dev-sessions
Content-Type: application/json
```

## Структура запроса

```json
{
  "date": "2026-05-02",
  "feature": "Название фичи или задачи",
  "category": "dev",
  "duration_min": 120,
  "tokens_approx": 50000,
  "notes": "Опциональные заметки"
}
```

## Категории
- `dev` — разработка, бэкенд, скрипты
- `design` — UI/UX, верстка, стили  
- `analytics` — аналитика, SQL, данные

## Как использовать в конце сессии

Попроси Claude в конце сессии:

> "Залогируй эту сессию в Dev Log. Фича: [название], категория: dev, примерно [N] минут и [N] токенов"

Claude выполнит:
```bash
curl -X POST https://insalon.onrender.com/dev-sessions \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-05-02","feature":"...","category":"dev","duration_min":120,"tokens_approx":50000}'
```

## Просмотр статистики

```bash
curl https://insalon.onrender.com/dev-sessions/stats
curl https://insalon.onrender.com/dev-sessions
```
