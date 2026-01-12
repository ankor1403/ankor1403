#!/bin/bash
###############################################################################
# ЛОКАЛЬНАЯ ДИАГНОСТИКА TELEGRAM SERVICE (запускать ПРЯМО НА СЕРВЕРЕ)
###############################################################################

echo "=== Telegram Multi-Service Диагностика (Локальная версия) ==="
echo ""

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${YELLOW}ℹ${NC} $1"; }

echo "1. Проверка статуса контейнеров..."
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E "(telegram|redis|caddy|wappi)"
echo ""

echo "2. Проверка переменных окружения Telegram API..."
docker exec telegram-multi-service env | grep -E 'TELEGRAM_API' || print_error "Переменные не найдены!"
echo ""

echo "3. Проверка логов Multi-Service (последние 30 строк)..."
docker logs --tail=30 telegram-multi-service 2>&1 | tail -20
echo ""

echo "4. Проверка здоровья сервиса (локально)..."
curl -s http://127.0.0.1:8200/health 2>/dev/null || print_error "Сервис не отвечает на порту 8200"
echo ""

echo "5. Проверка доступности через домен..."
curl -s -I https://telegram.afonin-lisa.ru/ | head -5
echo ""

echo "6. Проверка конфигурации Caddy..."
docker exec wappi-caddy cat /etc/caddy/Caddyfile | grep -A10 "telegram.afonin-lisa.ru"
echo ""

echo "7. Проверка сетевого подключения контейнеров..."
docker network inspect edge -f '{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{"\n"}}{{end}}' 2>/dev/null || print_error "Сеть edge не найдена"
echo ""

echo "8. Проверка базы данных..."
if docker exec telegram-multi-service ls /app/data/multi.db 2>/dev/null; then
    print_status "База данных существует"
    echo "Попытка проверки таблиц..."
    docker exec telegram-multi-service python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('/app/data/multi.db')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    users = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM profiles')
    profiles = cur.fetchone()[0]
    print(f'Пользователей: {users}, Профилей: {profiles}')
    conn.close()
except Exception as e:
    print(f'Ошибка БД: {e}')
" 2>/dev/null || print_error "Не удалось подключиться к БД"
else
    print_error "База данных не найдена!"
fi
echo ""

echo "9. Проверка портов..."
netstat -tlnp 2>/dev/null | grep -E ":(80|443|8100|8200|8765)" || ss -tlnp | grep -E ":(80|443|8100|8200|8765)"
echo ""

echo "10. Проверка версий и зависимостей в контейнере..."
docker exec telegram-multi-service python3 -c "
try:
    import telethon
    print(f'Telethon версия: {telethon.__version__}')
except:
    print('Telethon не установлен!')
try:
    import qrcode
    print('QRCode: установлен')
except:
    print('QRCode: НЕ установлен (нужен для QR авторизации)')
"
echo ""

echo "=== Диагностика завершена ==="
echo ""
print_info "РЕКОМЕНДАЦИИ:"
echo ""
echo "Если сервис не работает:"
echo "  1. Запустите исправление: bash fix_telegram_service_local.sh"
echo "  2. Проверьте логи: docker logs -f telegram-multi-service"
echo "  3. Перезапустите сервис: cd /opt/telegram_multi_service && docker-compose restart"
echo ""
