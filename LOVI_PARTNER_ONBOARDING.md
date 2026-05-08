# Lovi — Техническое руководство по подключению партнёра
> Версия: 08.05.2026 | Статус приложения YCLIENTS: **на модерации** (app_id: 41940)

---

## Контекст

Lovi — Yield Management платформа для wellness-салонов. Партнёр подключается через маркетплейс YCLIENTS, его горящие окошки появляются на витрине lovi.today. Клиенты бронируют со скидкой, оплачивают через YooKassa, запись появляется в расписании YCLIENTS.

**Текущее ограничение:** публичное приложение Lovi (app_id: 41940) на модерации YCLIENTS. Описаны два сценария — ручной (сейчас) и автоматический (после модерации).

---

## Шаг 1. Регистрация салона в маркетплейсе YCLIENTS

### Что происходит
Владелец нажимает "Подключить" в маркетплейсе. YCLIENTS редиректит на:
https://lovi.today/connect?salon_id={company_id}&user_data={base64_json}&user_data_sign={hmac}

user_data — base64-encoded UTF-8 JSON:
```json
{
  "id": 4299091,
  "name": "Дмитрий",
  "phone": "79269308484",
  "email": "dvasin.com@gmail.com",
  "salon_name": "Head SPA Beauty (Беляево)"
}
```

ВАЖНО: декодировать через TextDecoder("utf-8"), не через atob напрямую — иначе кириллица сломается.

### Наш обработчик POST /api/lovi/connect
- Декодируем user_data
- Сохраняем в salons (не затираем существующий user_token!)
- Генерируем JWT для кабинета партнёра
- Отправляем welcome письмо с magic link

### Активация интеграции

**Сейчас (без модерации):**
POST /api/v1/marketplace/partner/callback
{"salon_id": 1166484, "application_id": 41940, "webhook_urls": [...]}
Возвращает ошибку — YCLIENTS не принимает без прохождения модерации.

**Ручное решение:**
1. Запросить у партнёра логин/пароль от YCLIENTS
2. POST /api/v1/auth → получить user_token
3. UPDATE salons SET user_token='...' WHERE company_id=...

Риски: токен привязан к конкретному пользователю, не масштабируется, нарушает минимальные права.

**После модерации:**
YCLIENTS автоматически создаёт системного пользователя Lovi в филиале партнёра и возвращает user_token с нужными правами.

---

## Шаг 2. Кабинет партнёра /salon/dashboard

Авторизация через Magic Link:
POST /api/lovi/salon/magic-link  {"email": "owner@salon.com"}
GET  /api/lovi/salon/auth?token=...  → {jwt_token, salon}
GET  /api/lovi/salon/me  → данные салона + health-check

Health-check при каждом входе — проверяем через GET /api/v1/records/{company_id}:
- ok — токен рабочий
- no_access — токен есть но нет прав (нужна реактивация)
- no_token — токен не получен
- error — сетевая ошибка

**Без модерации:** показываем баннер "Нет прав, активируйте интеграцию".
**После модерации:** статус всегда ok автоматически.

---

## Шаг 3. Получение свободных слотов

### Старый API (не работает для витрины)
GET /api/v1/book_times/{company_id}/{staff_id}/{date}/{service_id}
Возвращает 0 слотов без конкретного staff_id.

### Новый API (работает, документация запрошена)
POST https://platform.yclients.com/api/v1/b2c/booking/availability/search-timeslots
{
"context": {"location_id": 1166484},
"filter": {
"date": "2026-05-10",
"records": [{"attendance_service_items": [{"type": "service", "id": 24560829}]}]
}
}
Возвращает правильные слоты. Используется внутренним виджетом YCLIENTS.

### Определение мастера
staff_id не возвращается в слоте. Определяем через /api/booking/staff в SlotDrawer.
Кнопка "Оплатить" заблокирована пока мастер не загружен — иначе master_id=null и запись не создастся.

---

## Шаг 4. Создание брони и оплата

### Флоу
SlotDrawer → POST /api/lovi/book (сохраняем бронь + создаём платёж YooKassa)
→ Клиент оплачивает
→ YooKassa webhook payment.succeeded → POST /payments/webhook
→ Получаем seance_length из YCLIENTS
→ Создаём запись в расписании YCLIENTS
→ Сохраняем yclients_record_id

### Критично: seance_length
YCLIENTS требует передавать seance_length. Наша БД хранит 0 — нужно запрашивать из YCLIENTS:
GET /api/v1/services/{company_id}/{service_id}
→ duration: 9600  (реальное значение)
Если передать неправильное значение (например 10200 вместо 9600) — получаем "Выбранное время недоступно".

### Системный клиент Lovi
Все записи создаются от одного клиента:
client_id: 396205299
phone: +79000000001
email: booking@lovi.today
Реальные данные клиента — в поле comment записи:
"lovi.today | Дмитрий +79999999999 | booking_id=120"

### Ошибки которые решили сегодня

| Ошибка | Причина | Решение |
|--------|---------|---------|
| Выбранное время недоступно | seance_length из нашей БД != реальный | Запрашиваем из /api/v1/services/ |
| Не передан seance_length | Убрали поле — оно обязательное | Всегда передавать |
| Нет прав на управление филиалом | Системный токен без активации | Токен администратора |
| master_id = null | staffRef не успевал заполниться | Блокируем кнопку пока staffLoading |
| Двойная попытка создания | fire-and-forget в lovi_book + webhook | Убрали из lovi_book |
| Неправильный мастер | Брали первого из таблицы staff | Только из /api/booking/staff |

**Без модерации:** используем user_token администратора салона.
**После модерации:** используем user_token системного пользователя Lovi.

---

## Шаг 5. Вебхуки — двусторонняя синхронизация

URL: https://insalon.onrender.com/webhook/yclients
Регистрируется через непубличное приложение в маркетплейсе YCLIENTS.
С 12.09.2022 — только через маркетплейс, не через настройки филиала.

record.edit (салон перенёс запись):
→ обновляем datetime и master_id
→ status: rescheduled
→ email клиенту

record.delete (салон отменил):
→ status: cancelled_by_salon
→ возврат на баланс Lovi
→ email клиенту

Статус: работает, проверено сегодня.

---

## Шаг 6. Отмена бронирования клиентом
POST /api/lovi/bookings/{id}/cancel
→ DELETE /api/v1/record/{company_id}/{yclients_record_id}
(без record_hash — работает через user_token)
→ status: cancelled_by_client
→ возврат на баланс Lovi
→ email клиенту

Политика: отмена за 2+ часа до визита.
P1: возврат на карту через YooKassa refund (не реализовано).

---

## Шаг 7. Чек-лист для нового партнёра

### Ручной процесс (сейчас, без модерации)

- [ ] Партнёр нажимает "Подключить" в маркетплейсе Lovi
- [ ] Данные сохраняются в salons, отправляется welcome письмо
- [ ] ВРУЧНУЮ: запросить логин/пароль от YCLIENTS у партнёра
- [ ] ВРУЧНУЮ: POST /api/v1/auth → получить user_token
- [ ] ВРУЧНУЮ: UPDATE salons SET user_token='...' WHERE company_id=...
- [ ] Проверить /salon/dashboard → статус "Работает"
- [ ] Добавить услуги салона в featured_services в lovi.py (ID из YCLIENTS)
- [ ] Проверить что book_times возвращает слоты для услуг партнёра
- [ ] Тестовое бронирование → запись появилась в расписании YCLIENTS
- [ ] Тест вебхука: удалить запись из YCLIENTS → status = cancelled_by_salon
- [ ] Тест отмены клиентом → запись исчезла из расписания

### Автоматический процесс (после модерации)

- [ ] Партнёр нажимает "Подключить"
- [ ] POST /marketplace/partner/callback → системный пользователь создан
- [ ] user_token сохраняется автоматически
- [ ] Вебхуки регистрируются автоматически
- [ ] /salon/dashboard → статус "Работает" сразу

---

## Текущие блокеры

| Задача | Статус | Что ждём |
|--------|--------|---------|
| Активация marketplace/partner/callback | Заблокировано | Прохождение модерации YCLIENTS |
| Новый B2C Booking API для витрины | В ожидании | Документация от поддержки YCLIENTS |
| seance_length из YCLIENTS | Решено | — |
| Системный клиент для записей | Решено | — |
| Вебхуки record.edit/delete | Решено | — |
| Отмена клиентом через API | Решено | — |
| Возврат на карту YooKassa refund | P1, не реализовано | — |

---

## Переменные окружения

```env
YCLIENTS_PARTNER_TOKEN=...       # общий для всех партнёров
YCLIENTS_COMPANY_ID=...          # индивидуально для каждого салона
LOVI_SYSTEM_CLIENT_ID=396205299  # системный клиент Lovi (общий)
YOOKASSA_SHOP_ID=...
YOOKASSA_SECRET_KEY=...
JWT_SECRET=...
RESEND_API_KEY=...
LOVI_BASE_URL=https://lovi.today
BOOKING_CODE_SECRET=...