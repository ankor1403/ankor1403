#!/bin/bash

# Скрипт для добавления импорта requests в main.py
# Запускать на сервере root@ixhyswhgny

set -e

echo "🔧 Добавление импорта requests в /opt/avito-service/app/main.py"
echo ""

cd /opt/avito-service

# Создаем бэкап
echo "1️⃣ Создание бэкапа..."
cp app/main.py app/main.py.backup.import.$(date +%Y%m%d_%H%M%S)

# Показываем текущие импорты
echo ""
echo "2️⃣ Текущие импорты в файле:"
head -20 app/main.py | grep -E "^import|^from"

echo ""
echo "3️⃣ Проверка наличия импорта requests..."
if grep -q "^import requests" app/main.py; then
    echo "✅ Импорт requests уже есть!"
else
    echo "❌ Импорт requests отсутствует, добавляем..."

    # Добавляем импорт после других импортов
    # Ищем строку с "from fastapi" и добавляем после неё
    sed -i '/^from fastapi import/a import requests' app/main.py

    echo "✅ Импорт добавлен!"
fi

echo ""
echo "4️⃣ Проверка результата:"
head -20 app/main.py | grep -E "^import|^from"

echo ""
echo "5️⃣ Перезапуск контейнера..."
docker compose down
docker compose build --no-cache
docker compose up -d

echo ""
echo "6️⃣ Ожидание запуска..."
sleep 5

echo ""
echo "7️⃣ Проверка логов:"
docker compose logs --tail=30

echo ""
echo "✅ ГОТОВО!"
echo ""
echo "Теперь попробуйте снова подключить Avito профиль!"
echo ""
