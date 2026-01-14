#!/bin/bash

# Quick restart script for Avito Service
# Run this on root@ixhyswhgny server

set -e

echo "🔄 Перезапуск Avito Service с обновленными OAuth scopes..."
echo ""

cd /opt/avito-service

echo "1️⃣ Остановка контейнера..."
docker compose down

echo ""
echo "2️⃣ Удаление старого образа..."
docker rmi -f avito-service:latest 2>/dev/null || true

echo ""
echo "3️⃣ Сборка нового образа..."
docker compose build --no-cache

echo ""
echo "4️⃣ Запуск контейнера..."
docker compose up -d

echo ""
echo "5️⃣ Ожидание запуска (10 секунд)..."
sleep 10

echo ""
echo "6️⃣ Проверка статуса..."
docker ps | grep avito-service

echo ""
echo "7️⃣ Последние логи:"
docker compose logs --tail=20

echo ""
echo "✅ Готово!"
echo ""
echo "📝 Теперь:"
echo "   1. Откройте браузер в режиме ИНКОГНИТО (или очистите кэш)"
echo "   2. Перейдите на https://avito.afonin-lisa.ru"
echo "   3. Попробуйте подключить профиль Avito снова"
echo ""
echo "Новые scopes должны быть:"
echo "messenger:read,messenger:write,items:info,items:apply_vas,stats:read,autoload:reports,user:read"
echo ""
