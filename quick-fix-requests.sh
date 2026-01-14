#!/bin/bash

# Быстрое исправление - добавление импорта requests
# Запускать на сервере root@ixhyswhgny

cd /opt/avito-service

echo "🔧 Исправление импорта requests..."

# Проверяем есть ли импорт
if grep -q "^import requests" app/main.py; then
    echo "✅ Импорт requests уже есть!"
else
    echo "❌ Добавляем импорт requests..."

    # Добавляем импорт после строки 5 (после import json)
    sed -i '5 a import requests' app/main.py

    echo "✅ Импорт добавлен!"
fi

echo ""
echo "Проверка импортов:"
head -15 app/main.py

echo ""
echo "🔄 Перезапуск контейнера..."
docker compose down
docker compose build --no-cache
docker compose up -d

echo ""
sleep 3
echo "✅ Готово! Попробуйте снова подключить Avito профиль в режиме инкогнито!"
