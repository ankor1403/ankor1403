#!/bin/bash
# Telegram Multi-Service Diagnostic Script
# Использование: bash telegram_diagnostic.sh

echo "=== Telegram Multi-Service Диагностика ==="
echo ""

SERVER="root@83.222.25.94"

echo "1. Проверка статуса контейнеров..."
ssh $SERVER "docker ps --filter name=telegram --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
echo ""

echo "2. Проверка переменных окружения Telegram API..."
ssh $SERVER "docker exec telegram-multi-service env | grep -E 'TELEGRAM_API'"
echo ""

echo "3. Проверка логов Multi-Service (последние 50 строк)..."
ssh $SERVER "docker logs --tail=50 telegram-multi-service 2>&1"
echo ""

echo "4. Проверка здоровья сервиса..."
ssh $SERVER "curl -s http://127.0.0.1:8200/health 2>/dev/null || echo 'Health check failed'"
echo ""

echo "5. Проверка базы данных (пользователи и профили)..."
ssh $SERVER "docker exec telegram-multi-service python3 -c \"
import sqlite3
try:
    conn = sqlite3.connect('/app/data/multi.db')
    cur = conn.cursor()
    users = cur.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    profiles = cur.execute('SELECT COUNT(*) FROM profiles').fetchone()[0]
    print(f'Пользователей: {users}')
    print(f'Профилей: {profiles}')
    conn.close()
except Exception as e:
    print(f'Ошибка БД: {e}')
\""
echo ""

echo "6. Проверка доступности через веб..."
curl -sk https://telegram.afonin-lisa.ru/ | head -5
echo ""

echo "=== Диагностика завершена ==="
