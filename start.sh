#!/bin/bash

# Переходим в папку проекта
cd /Users/dmitryvasin/insalon

# Активируем виртуальное окружение
source venv/bin/activate

# Запускаем ngrok в фоне
ngrok http 8000 &

# Ждём секунду чтобы ngrok запустился
sleep 2

# Запускаем сервер
uvicorn app.main:app --reload