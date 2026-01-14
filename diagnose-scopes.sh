#!/bin/bash

# Диагностика OAuth scopes
echo "🔍 Диагностика OAuth scopes в Avito Service"
echo ""
echo "=========================================="
echo "СОДЕРЖИМОЕ ФАЙЛА main.py (строки со scope):"
echo "=========================================="
grep -n -A 2 -B 2 "scope" /opt/avito-service/app/main.py
echo ""
echo "=========================================="
echo "ПРАВИЛЬНЫЕ SCOPES ДОЛЖНЫ БЫТЬ:"
echo "=========================================="
echo "messenger:read,messenger:write,items:info,items:apply_vas,stats:read,autoload:reports,user:read,user_balance:read,user_operations:read"
echo ""
echo "=========================================="
echo "НЕПРАВИЛЬНЫЕ SCOPES (если найдены):"
echo "=========================================="
grep -n "autoload:read\|autoload:write" /opt/avito-service/app/main.py && echo "❌ НАЙДЕНЫ НЕПРАВИЛЬНЫЕ SCOPES!" || echo "✅ Неправильные scopes не найдены"
echo ""
echo "=========================================="
echo "СТАТУС КОНТЕЙНЕРА:"
echo "=========================================="
docker ps | grep avito-service
echo ""
echo "=========================================="
echo "ПОСЛЕДНИЕ 10 СТРОК ЛОГОВ:"
echo "=========================================="
docker compose -f /opt/avito-service/docker-compose.yml logs --tail=10
echo ""
