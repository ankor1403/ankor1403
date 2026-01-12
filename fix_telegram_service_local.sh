#!/bin/bash
###############################################################################
# ЛОКАЛЬНОЕ ИСПРАВЛЕНИЕ TELEGRAM SERVICE (запускать ПРЯМО НА СЕРВЕРЕ)
###############################################################################

echo "=== Исправление Telegram Multi-Service (Локальная версия) ==="
echo ""

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

# Проверка, что мы на сервере
if [ ! -d "/opt/telegram_multi_service" ]; then
    print_error "Директория /opt/telegram_multi_service не найдена!"
    echo "Убедитесь, что вы запускаете скрипт на правильном сервере."
    exit 1
fi

echo "1. Остановка сервиса..."
docker stop telegram-multi-service 2>/dev/null && print_status "Сервис остановлен" || print_error "Не удалось остановить"
echo ""

echo "2. Создание бэкапа данных..."
BACKUP_NAME="multi.db.backup.$(date +%Y%m%d_%H%M%S)"
docker run --rm -v telegram_multi_service_data:/data -v /tmp:/backup alpine cp /data/multi.db /backup/$BACKUP_NAME 2>/dev/null && print_status "Бэкап создан: /tmp/$BACKUP_NAME" || print_warning "Бэкап не удалось создать (возможно, данных нет)"
echo ""

echo "3. Проверка и создание .env файла..."
cd /opt/telegram_multi_service
if [ ! -f .env ]; then
    print_info "Создание .env файла..."
    cat > .env << 'EOF'
TELEGRAM_API_ID=28561380
TELEGRAM_API_HASH=c07bd084d44bb8f3d377aa6e1ea859ff
DATABASE_PATH=/app/data/multi.db
SECRET_KEY=super_secret_key_change_in_production
EOF
    print_status ".env файл создан"
else
    print_status ".env файл существует"
fi
cat .env | grep TELEGRAM_API
echo ""

echo "4. Проверка docker-compose.yml..."
if [ -f docker-compose.yml ]; then
    print_status "docker-compose.yml найден"
else
    print_error "docker-compose.yml не найден!"
    exit 1
fi
echo ""

echo "5. Установка зависимостей в контейнере (если нужно)..."
print_info "Запуск контейнера для установки зависимостей..."
docker-compose up -d
sleep 5

print_info "Установка qrcode для QR авторизации..."
docker exec telegram-multi-service pip install qrcode[pil] 2>&1 | tail -5
print_info "Обновление telethon..."
docker exec telegram-multi-service pip install --upgrade telethon 2>&1 | tail -5
print_status "Зависимости установлены"
echo ""

echo "6. Пересборка контейнера (опционально)..."
read -p "Пересобрать контейнер с нуля? Это займёт время (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[YyДд]$ ]]; then
    print_info "Пересборка контейнера..."
    docker-compose build --no-cache
    print_status "Контейнер пересобран"
fi
echo ""

echo "7. Запуск сервиса..."
docker-compose up -d
print_status "Сервис запущен"
echo ""

echo "8. Ожидание инициализации (10 секунд)..."
sleep 10
echo ""

echo "9. Проверка логов..."
docker logs --tail=30 telegram-multi-service
echo ""

echo "10. Проверка здоровья сервиса..."
sleep 2
curl -s http://127.0.0.1:8200/health | head -20 || print_error "Сервис не отвечает"
echo ""

echo "11. Проверка через внешний домен..."
curl -s -I https://telegram.afonin-lisa.ru/ | head -5
echo ""

echo "12. Перезапуск Caddy (для обновления конфигурации)..."
docker exec wappi-caddy caddy reload --config /etc/caddy/Caddyfile 2>&1 || print_warning "Не удалось перезагрузить Caddy"
echo ""

echo "=== Исправление завершено ==="
echo ""
print_status "Сервис должен быть доступен!"
echo ""
print_info "Проверьте:"
echo "  1. Веб-интерфейс: https://telegram.afonin-lisa.ru/"
echo "  2. API документация: https://telegram.afonin-lisa.ru/docs"
echo "  3. Логи: docker logs -f telegram-multi-service"
echo ""
print_info "Для тестирования авторизации:"
echo "  docker exec -it telegram-multi-service python3 /tmp/test_telegram_auth.py"
echo ""
