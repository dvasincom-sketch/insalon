# Проект: аналитика плотности массажных салонов по зонам спроса (Москва, ЮЗАО)

## Архитектура

- **Бэкенд:** FastAPI (Python), репозиторий `insalon`, деплой на Render. Основной файл — `app/routers/lovi.py`.
- **Фронтенд:** React (Vite), репозиторий `lovi-web`, деплой на Vercel/хостинг по адресу lovi.today. Страница — `src/pages/ZoneMap.jsx`.
- **База данных:** Supabase (PostgreSQL), таблица `zone_cache` — кэш результатов 2GIS.
- **Внешние данные:** 2GIS API (ключ `a0c99e2a-de74-4d58-9ed4-2b33d269050e`), эндпоинт `catalog.api.2gis.com/3.0/items`. Overpass API (OSM) — реализован, временно отключён.

## Текущее состояние (актуально на 2026-05-12)

### Бэкенд
- `GET /api/lovi/zones/search?zone_id=...` — чтение из кэша Supabase (`zone_cache`).
- `POST /api/lovi/zones/refresh` — параллельное обновление кэша из 2GIS для всех зон.
- Реализованы вспомогательные функции: `_fetch_2gis_zone`, `_fetch_overpass_zone`, `_in_bbox`, `_dedup_items`.
- Overpass включается флагом `"use_overpass": true` в теле запроса.

### Данные
- **176 объектов** в кэше по 17 зонам, данные сохранены в Supabase.
- Максимум по зоне: 15 объектов (kaluzhskaya-border, lomonosovsky-vorontsovsky).
- Минимум: 4 объекта (derevlyovskiy-prud).

### Что работает
- Параллельные запросы к 2GIS через `asyncio.gather` (таймаут 20с).
- 3 смещённых запроса на зону — обход лимита 10 объектов бесплатного ключа.
- Предохранитель: если новый `count < cached` — кэш не перезаписывается.
- Нулевые результаты не пишутся в Supabase (`to_upsert = [r for r in to_upsert if r['count'] > 0]`).
- bbox-фильтры для всех 17 зон — объекты не пересекают барьерные улицы.

### Что предстоит
- Проверить фронт: отображение объектов в карточках зон.
- Включить и протестировать Overpass API.
- Проверить bbox: ул. Миклухо-Маклая 37 должна попадать в `belyaevo-center`, не в `yabloneviy-sad`.
- Протестировать кнопку «Обновить данные» на проде через браузер.

## 17 зон (4 района ЮЗАО)

| Район | Зона | lat | lon | radius | count |
|---|---|---|---|---|---|
| Коньково | yabloneviy-sad | 55.6455 | 37.5185 | 550 | 11 |
| Коньково | konkovskie-prudy | 55.6370 | 37.5155 | 600 | 13 |
| Коньково | derevlyovskiy-prud | 55.6505 | 37.5490 | 580 | 4 |
| Коньково | belyaevo-center | 55.6468 | 37.5360 | 480 | 8 |
| Коньково | obrucheva-st | 55.6560 | 37.5310 | 560 | 9 |
| Коньково | kaluzhskaya-border | 55.6635 | 37.5145 | 520 | 15 |
| Обручевский | rudn | 55.6530 | 37.5655 | 600 | 11 |
| Обручевский | samorodinka | 55.6620 | 37.5720 | 580 | 12 |
| Обручевский | vorontsovskaya | 55.6680 | 37.5350 | 580 | 11 |
| Обручевский | novye-cheremushki | 55.6740 | 37.5440 | 560 | 11 |
| Обручевский | novatorskaya | 55.6760 | 37.5210 | 570 | 9 |
| Черёмушки | cheremushki-north | 55.6650 | 37.5580 | 560 | 10 |
| Черёмушки | cheremushki-center | 55.6720 | 37.5600 | 560 | 10 |
| Черёмушки | cheremushki-south | 55.6790 | 37.5620 | 550 | 5 |
| Ломоносовский | lomonosovsky-vorontsovsky | 55.6710 | 37.5080 | 580 | 15 |
| Ломоносовский | lomonosovsky-leninsky | 55.6820 | 37.5010 | 600 | 10 |
| Ломоносовский | lomonosovsky-nakhimovsky | 55.6790 | 37.5170 | 560 | 12 |

## Dev Log

> **Соглашение:** при закрытии сессии — предлагать обновить этот файл и логировать сессию в `dev_sessions` (Supabase) одной командой curl.

### Команда логирования
```bash
curl -X POST https://insalon.onrender.com/dev-sessions \
  -H "Content-Type: application/json" \
  -d '{"date":"YYYY-MM-DD","feature":"Название","category":"dev","duration_min":90,"tokens_approx":50000,"notes":"..."}'
```

### Категории: `dev` / `design` / `analytics`
