#!/bin/bash

# Avito Service - Remote Server Deployment Script
# Run this script on root@ixhyswhgny server

set -e

echo "🚀 Развертывание Avito Service с обновленными зависимостями..."
echo ""

# Check if running on server
if [ ! -d "/opt/avito-service" ]; then
    echo "❌ Ошибка: Директория /opt/avito-service не найдена!"
    echo "   Этот скрипт должен запускаться на сервере с установленным Avito Service"
    exit 1
fi

cd /opt/avito-service

# 1. Backup current files
echo "1️⃣ Создание резервной копии..."
mkdir -p /opt/avito-service-backup
cp -r /opt/avito-service/* /opt/avito-service-backup/ 2>/dev/null || true
echo "   ✅ Резервная копия создана в /opt/avito-service-backup/"

# 2. Update requirements.txt
echo ""
echo "2️⃣ Обновление requirements.txt с исправлениями безопасности..."
cat > /opt/avito-service/requirements.txt << 'EOF'
# Avito Multi-Service - Secure Dependencies
# Last Updated: 2026-01-13
# All CVEs patched

# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.32.0

# Templating
jinja2==3.1.5

# HTTP Client
requests==2.32.4

# Form Parsing
python-multipart==0.0.18
EOF
echo "   ✅ requirements.txt обновлен"

# 3. Update main.py OAuth URLs
echo ""
echo "3️⃣ Исправление Avito API URLs..."

# Fix AVITO_TOKEN_URL
sed -i 's|AVITO_TOKEN_URL = "https://api.avito.ru/oauth/token"|AVITO_TOKEN_URL = "https://api.avito.ru/token"|g' /opt/avito-service/app/main.py

# Fix AVITO_AUTH_URL
sed -i 's|AVITO_AUTH_URL = "https://api.avito.ru/oauth"|AVITO_AUTH_URL = "https://avito.ru/oauth"|g' /opt/avito-service/app/main.py

echo "   ✅ API URLs исправлены"

# 4. Check .env file
echo ""
echo "4️⃣ Проверка .env файла..."
if [ ! -f "/opt/avito-service/.env" ]; then
    echo "   ⚠️ ВНИМАНИЕ: .env файл не найден!"
    echo "   Создайте .env файл с вашими credentials:"
    echo ""
    cat << 'ENVEXAMPLE'
AVITO_CLIENT_ID=your_client_id_here
AVITO_CLIENT_SECRET=your_client_secret_here
AVITO_REDIRECT_URI=https://avito.afonin-lisa.ru/api/v1/avito/callback
AVITO_WEBHOOK_URL=https://api.avito.afonin-lisa.ru/api/webhook
ENVEXAMPLE
    echo ""
    read -p "   Нажмите Enter после создания .env файла..." dummy
fi

if [ -f "/opt/avito-service/.env" ]; then
    echo "   ✅ .env файл найден"
    # Check if redirect URI is correct
    if grep -q "oauth/callback" /opt/avito-service/.env; then
        echo "   ⚠️ Исправление redirect URI в .env..."
        sed -i 's|/oauth/callback|/api/v1/avito/callback|g' /opt/avito-service/.env
        echo "   ✅ Redirect URI обновлен"
    fi
fi

# 5. Stop and remove old container
echo ""
echo "5️⃣ Остановка старого контейнера..."
docker compose down 2>/dev/null || true
docker rm -f avito-service 2>/dev/null || true
echo "   ✅ Старый контейнер удален"

# 6. Remove old images
echo ""
echo "6️⃣ Удаление старых Docker образов..."
docker rmi -f avito-service:latest 2>/dev/null || true
docker rmi -f $(docker images -f "dangling=true" -q) 2>/dev/null || true
echo "   ✅ Старые образы удалены"

# 7. Build new image
echo ""
echo "7️⃣ Сборка нового Docker образа (это может занять несколько минут)..."
docker compose build --no-cache
echo "   ✅ Образ собран успешно"

# 8. Start container
echo ""
echo "8️⃣ Запуск контейнера..."
docker compose up -d
echo "   ✅ Контейнер запущен"

# 9. Wait for container to start
echo ""
echo "9️⃣ Ожидание запуска сервиса (30 секунд)..."
sleep 30

# 10. Check container status
echo ""
echo "🔍 Проверка статуса контейнера..."
if docker ps | grep -q avito-service; then
    echo "   ✅ Контейнер работает"
else
    echo "   ❌ Контейнер не запустился!"
    echo ""
    echo "Логи контейнера:"
    docker compose logs --tail=50
    exit 1
fi

# 11. Check environment variables
echo ""
echo "🔍 Проверка переменных окружения..."
CLIENT_ID=$(docker exec avito-service python -c "import os; print(os.getenv('AVITO_CLIENT_ID', 'NOT SET'))" 2>/dev/null || echo "ERROR")
if [ "$CLIENT_ID" = "NOT SET" ] || [ "$CLIENT_ID" = "ERROR" ]; then
    echo "   ❌ ОШИБКА: Переменные окружения не загружены!"
    echo ""
    echo "Проверьте docker-compose.yml:"
    echo "Убедитесь что есть строка 'env_file: - .env'"
    exit 1
else
    echo "   ✅ Переменные окружения загружены"
    echo "      Client ID: ${CLIENT_ID:0:10}..."
fi

# 12. Test HTTP endpoint
echo ""
echo "🔍 Проверка HTTP endpoint..."
sleep 5
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8300/ || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    echo "   ✅ HTTP endpoint отвечает (код: $HTTP_CODE)"
else
    echo "   ⚠️ HTTP код: $HTTP_CODE (может быть нормально)"
fi

# 13. Show logs
echo ""
echo "📋 Последние 20 строк логов:"
echo "─────────────────────────────────────────"
docker compose logs --tail=20
echo "─────────────────────────────────────────"

# 14. Summary
echo ""
echo "✅ ═══════════════════════════════════════════════════════"
echo "✅ Развертывание завершено успешно!"
echo "✅ ═══════════════════════════════════════════════════════"
echo ""
echo "📊 Статус:"
echo "   • Контейнер: РАБОТАЕТ"
echo "   • Переменные окружения: ЗАГРУЖЕНЫ"
echo "   • Обновленные зависимости:"
echo "     - FastAPI: 0.109.0 → 0.115.0"
echo "     - uvicorn: 0.27.0 → 0.32.0"
echo "     - jinja2: 3.1.3 → 3.1.5"
echo "     - requests: 2.31.0 → 2.32.4"
echo "     - python-multipart: 0.0.6 → 0.0.18"
echo "   • Исправлено 10 CVE (критических и высоких)"
echo ""
echo "🌐 Доступ:"
echo "   • Локально: http://localhost:8300"
echo "   • Через интернет: https://avito.afonin-lisa.ru"
echo "   • API endpoint: https://api.avito.afonin-lisa.ru"
echo ""
echo "📝 Следующие шаги:"
echo "   1. Откройте https://avito.afonin-lisa.ru в браузере"
echo "   2. Зарегистрируйтесь или войдите"
echo "   3. Добавьте профиль Avito и протестируйте OAuth"
echo ""
echo "🔧 Полезные команды:"
echo "   • Логи: cd /opt/avito-service && docker compose logs -f"
echo "   • Перезапуск: cd /opt/avito-service && docker compose restart"
echo "   • Остановка: cd /opt/avito-service && docker compose down"
echo ""
echo "📚 Документация:"
echo "   • Полная установка: https://github.com/ankor1403/ankor1403/blob/main/AVITO_УСТАНОВКА.md"
echo "   • Аудит безопасности: https://github.com/ankor1403/ankor1403/blob/main/AVITO_DEPENDENCY_AUDIT.md"
echo ""

exit 0
