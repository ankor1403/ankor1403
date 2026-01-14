#!/bin/bash
# Мониторинг работы messenger worker

echo "📊 Мониторинг Avito Messenger Worker"
echo "====================================="
echo ""
echo "Нажмите Ctrl+C для выхода"
echo ""

# Показываем текущие профили с user_id
echo "Профили с avito_user_id:"
docker exec avito-service sqlite3 /app/avito.db "SELECT id, name, avito_user_id FROM profiles WHERE avito_user_id IS NOT NULL AND avito_user_id != '';" 2>/dev/null || docker exec avito-service sqlite3 /data/avito.db "SELECT id, name, avito_user_id FROM profiles WHERE avito_user_id IS NOT NULL AND avito_user_id != '';" 2>/dev/null || sqlite3 /opt/avito-service/data/avito.db "SELECT id, name, avito_user_id FROM profiles WHERE avito_user_id IS NOT NULL AND avito_user_id != '';"

echo ""
echo "====================================="
echo "Логи worker (в реальном времени):"
echo "====================================="
echo ""

# Следим за логами
docker logs -f avito-service 2>&1 | grep --line-buffered -iE "worker|polling|chat|message|profile|авито|avito"
