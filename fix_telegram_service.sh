#!/bin/bash
# Скрипт для исправления проблем с Telegram Multi-Service
# Использование: bash fix_telegram_service.sh

SERVER="root@83.222.25.94"

echo "=== Исправление Telegram Multi-Service ==="
echo ""

# Функция для выполнения команды на сервере
run_remote() {
    ssh $SERVER "$1"
}

echo "1. Остановка сервиса..."
run_remote "docker stop telegram-multi-service"
echo "✓ Сервис остановлен"
echo ""

echo "2. Создание бэкапа данных..."
run_remote "docker exec telegram-multi-service cp -r /app/data /app/data.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo 'Контейнер уже остановлен, пропуск бэкапа'"
echo "✓ Бэкап создан"
echo ""

echo "3. Проверка docker-compose.yml..."
cat << 'EOF' | ssh $SERVER "cat > /tmp/check_compose.sh && bash /tmp/check_compose.sh"
if [ -f /opt/telegram_multi_service/docker-compose.yml ]; then
    echo "✓ docker-compose.yml найден"
    cat /opt/telegram_multi_service/docker-compose.yml | grep -A5 telegram-multi-service
else
    echo "✗ docker-compose.yml не найден!"
fi
EOF
echo ""

echo "4. Проверка переменных окружения..."
cat << 'EOF' | ssh $SERVER "cat > /tmp/fix_env.sh && bash /tmp/fix_env.sh"
cd /opt/telegram_multi_service
if [ ! -f .env ]; then
    echo "Создание .env файла..."
    cat > .env << 'ENVEOF'
TELEGRAM_API_ID=28561380
TELEGRAM_API_HASH=c07bd084d44bb8f3d377aa6e1ea859ff
DATABASE_PATH=/app/data/multi.db
SECRET_KEY=$(openssl rand -hex 32)
ENVEOF
    echo "✓ .env файл создан"
else
    echo "✓ .env файл существует"
    cat .env | grep TELEGRAM_API
fi
EOF
echo ""

echo "5. Пересборка контейнера..."
run_remote "cd /opt/telegram_multi_service && docker-compose build --no-cache"
echo "✓ Контейнер пересобран"
echo ""

echo "6. Запуск сервиса..."
run_remote "cd /opt/telegram_multi_service && docker-compose up -d"
echo "✓ Сервис запущен"
echo ""

echo "7. Ожидание инициализации (10 секунд)..."
sleep 10
echo ""

echo "8. Проверка логов..."
run_remote "docker logs --tail=20 telegram-multi-service"
echo ""

echo "9. Проверка здоровья сервиса..."
run_remote "curl -s http://127.0.0.1:8200/health || echo 'Сервис не отвечает'"
echo ""

echo "=== Исправление завершено ==="
echo ""
echo "Следующие шаги:"
echo "1. Откройте https://telegram.afonin-lisa.ru/"
echo "2. Зарегистрируйтесь или войдите"
echo "3. Создайте профиль с вашим номером телефона"
echo "4. Следуйте инструкциям для авторизации"
