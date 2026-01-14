#!/bin/bash
# Проверка статуса Avito Messenger

echo "=========================================="
echo "📊 СТАТУС AVITO MESSENGER"
echo "=========================================="
echo ""

echo "1️⃣ Проверка профилей в базе данных:"
echo "-----------------------------------"
docker exec avito-service sqlite3 /app/avito.db "SELECT id, name, CASE WHEN access_token IS NOT NULL THEN 'ДА' ELSE 'НЕТ' END as 'Токен', CASE WHEN avito_user_id IS NOT NULL AND avito_user_id != '' THEN avito_user_id ELSE '❌ ПУСТО' END as 'User ID' FROM profiles ORDER BY id;" -header -column 2>/dev/null

if [ $? -ne 0 ]; then
    # Попробуем альтернативный путь
    docker exec avito-service sqlite3 /data/avito.db "SELECT id, name, CASE WHEN access_token IS NOT NULL THEN 'ДА' ELSE 'НЕТ' END as 'Токен', CASE WHEN avito_user_id IS NOT NULL AND avito_user_id != '' THEN avito_user_id ELSE '❌ ПУСТО' END as 'User ID' FROM profiles ORDER BY id;" -header -column 2>/dev/null

    if [ $? -ne 0 ]; then
        sqlite3 /opt/avito-service/data/avito.db "SELECT id, name, CASE WHEN access_token IS NOT NULL THEN 'ДА' ELSE 'НЕТ' END as 'Токен', CASE WHEN avito_user_id IS NOT NULL AND avito_user_id != '' THEN avito_user_id ELSE '❌ ПУСТО' END as 'User ID' FROM profiles ORDER BY id;" -header -column
    fi
fi

echo ""
echo "2️⃣ Проверка worker в логах:"
echo "-----------------------------------"
docker logs avito-service 2>&1 | grep -i "messenger worker" | tail -5

echo ""
echo "3️⃣ Проверка callback кода (должен быть user_id fetch):"
echo "-----------------------------------"
if docker exec avito-service grep -q "Get Avito user_id" /app/main.py 2>/dev/null; then
    echo "✅ Callback код для получения user_id НАЙДЕН"
else
    echo "❌ Callback код для получения user_id НЕ НАЙДЕН"
    echo "   Нужно применить фикс!"
fi

echo ""
echo "4️⃣ Количество сообщений в БД:"
echo "-----------------------------------"
MESSAGES=$(docker exec avito-service sqlite3 /app/avito.db "SELECT COUNT(*) FROM messages;" 2>/dev/null || docker exec avito-service sqlite3 /data/avito.db "SELECT COUNT(*) FROM messages;" 2>/dev/null || sqlite3 /opt/avito-service/data/avito.db "SELECT COUNT(*) FROM messages;" 2>/dev/null || echo "0")
echo "Всего сообщений: $MESSAGES"

echo ""
echo "=========================================="
echo "📋 ЧТО ДЕЛАТЬ ДАЛЬШЕ:"
echo "=========================================="

# Проверяем есть ли профили с user_id
HAS_USER_ID=$(docker exec avito-service sqlite3 /app/avito.db "SELECT COUNT(*) FROM profiles WHERE avito_user_id IS NOT NULL AND avito_user_id != '';" 2>/dev/null || docker exec avito-service sqlite3 /data/avito.db "SELECT COUNT(*) FROM profiles WHERE avito_user_id IS NOT NULL AND avito_user_id != '';" 2>/dev/null || sqlite3 /opt/avito-service/data/avito.db "SELECT COUNT(*) FROM profiles WHERE avito_user_id IS NOT NULL AND avito_user_id != '';" 2>/dev/null || echo "0")

if [ "$HAS_USER_ID" == "0" ]; then
    echo ""
    echo "⚠️  НИ У ОДНОГО ПРОФИЛЯ НЕТ avito_user_id!"
    echo ""
    echo "🔧 Вам нужно ПЕРЕАВТОРИЗОВАТЬ любой профиль:"
    echo ""
    echo "   1. Откройте в браузере: http://ваш-сервер:8003"
    echo "   2. Войдите в систему"
    echo "   3. Выберите любой профиль (например, профиль #22)"
    echo "   4. Нажмите кнопку 'Авторизовать в Avito'"
    echo "   5. Подтвердите авторизацию в Avito"
    echo ""
    echo "   После этого запустите этот скрипт снова!"
    echo ""
else
    echo ""
    echo "✅ Есть профили с user_id! Worker должен работать."
    echo ""
    echo "Проверьте логи worker:"
    echo "   docker logs -f avito-service | grep -i 'polling\\|chat\\|message'"
    echo ""
fi
