#!/bin/bash

# Скрипт для исправления OAuth scopes в Avito Service
# Запускать на сервере root@ixhyswhgny

set -e

echo "🔧 Исправление OAuth scopes в /opt/avito-service/app/main.py"
echo ""

cd /opt/avito-service

# Создаем бэкап
echo "1️⃣ Создание бэкапа..."
cp app/main.py app/main.py.backup.$(date +%Y%m%d_%H%M%S)

# Показываем текущие scopes
echo ""
echo "2️⃣ Текущие scopes в файле:"
grep -n "scope" app/main.py || echo "Не найдено!"

echo ""
echo "3️⃣ Применение исправлений..."

# Правильные scopes согласно документации Avito API
CORRECT_SCOPES="messenger:read,messenger:write,items:info,items:apply_vas,stats:read,autoload:reports,user:read,user_balance:read,user_operations:read"

# Исправляем ВСЕ варианты старых scopes
sed -i 's|"scope": "messenger:read messenger:write autoload:read autoload:write items:info"|"scope": "'"${CORRECT_SCOPES}"'"|g' app/main.py

sed -i 's|scopes = "messenger:read,messenger:write,items:info,items:apply_vas,stats:read,autoload:reports,user:read"|scopes = "'"${CORRECT_SCOPES}"'"|g' app/main.py

# Также проверяем вариант с одинарными кавычками
sed -i "s|'scope': 'messenger:read messenger:write autoload:read autoload:write items:info'|'scope': '${CORRECT_SCOPES}'|g" app/main.py

sed -i "s|scopes = 'messenger:read,messenger:write,items:info,items:apply_vas,stats:read,autoload:reports,user:read'|scopes = '${CORRECT_SCOPES}'|g" app/main.py

echo ""
echo "4️⃣ Проверка результата:"
grep -n "scope" app/main.py

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
echo "📋 Правильные scopes установлены:"
echo "   ${CORRECT_SCOPES}"
echo ""
echo "⚠️  ВАЖНО: Откройте браузер в РЕЖИМЕ ИНКОГНИТО"
echo "   или нажмите Ctrl+Shift+R для полной перезагрузки!"
echo ""
