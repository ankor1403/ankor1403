#!/bin/bash
# Скрипт для исправления callback - добавление получения avito_user_id

echo "🔧 Исправление OAuth callback для получения avito_user_id"
echo ""

# Создаём Python скрипт для патча
cat > /tmp/fix_callback.py << 'EOFIX'
import sys
import re

with open('/app/main.py', 'r') as f:
    content = f.read()

# Проверяем, уже ли есть код получения user_id
if 'Get Avito user_id' in content or 'avito_user_id' in content.split('def oauth_callback')[1].split('def ')[0]:
    print("✅ Callback уже содержит код получения avito_user_id")
    sys.exit(0)

# Добавляем AVITO_API_URL если нет
if 'AVITO_API_URL' not in content:
    content = content.replace(
        'AVITO_TOKEN_URL = "https://api.avito.ru/token"',
        'AVITO_TOKEN_URL = "https://api.avito.ru/token"\nAVITO_API_URL = "https://api.avito.ru"'
    )
    print("✅ Добавлена константа AVITO_API_URL")

# Находим место после получения token_data и добавляем код получения user_id
# Ищем паттерн: token_data = token_response.json()
# После него добавляем код

insert_code = '''
        # Get Avito user_id
        try:
            user_info_response = requests.get(
                f"{AVITO_API_URL}/core/v1/accounts/self",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            avito_user_id = None
            if user_info_response.status_code == 200:
                user_info = user_info_response.json()
                avito_user_id = str(user_info.get('id'))
                print(f"✅ Got avito_user_id: {avito_user_id}")
            else:
                print(f"⚠️ Failed to get user_id: {user_info_response.status_code}")
        except Exception as e:
            print(f"⚠️ Error getting user_id: {e}")
            avito_user_id = None
'''

# Находим место после token_data = token_response.json()
pattern = r'(token_data = token_response\.json\(\)\s*\n)'
if re.search(pattern, content):
    content = re.sub(pattern, r'\1' + insert_code + '\n', content, count=1)
    print("✅ Добавлен код получения avito_user_id после token_data")
else:
    print("❌ Не найден паттерн 'token_data = token_response.json()'")
    sys.exit(1)

# Теперь нужно изменить SQL UPDATE чтобы включить avito_user_id
# Ищем UPDATE profiles SET ... WHERE id = ? AND user_id = ?
old_update_pattern = r'conn\.execute\(\s*"""UPDATE profiles\s+SET access_token = \?,\s+refresh_token = \?,\s+token_expires_at = \?\s+WHERE id = \? AND user_id = \?""",\s*\(access_token, refresh_token, expires_at\.isoformat\(\), profile_id, user_id\)'

new_update = '''conn.execute(
            """UPDATE profiles
               SET access_token = ?,
                   refresh_token = ?,
                   token_expires_at = ?,
                   avito_user_id = ?
               WHERE id = ? AND user_id = ?""",
            (access_token, refresh_token, expires_at.isoformat(), avito_user_id, profile_id, user_id)'''

if re.search(old_update_pattern, content, re.DOTALL):
    content = re.sub(old_update_pattern, new_update, content, count=1, flags=re.DOTALL)
    print("✅ Обновлен SQL UPDATE для сохранения avito_user_id")
else:
    # Попробуем более гибкий паттерн
    alt_pattern = r'(conn\.execute\(\s*"""UPDATE profiles.*?WHERE id = \? AND user_id = \?""".*?\(access_token, refresh_token, expires_at\.isoformat\(\), profile_id, user_id\))'
    if re.search(alt_pattern, content, re.DOTALL):
        content = re.sub(alt_pattern, new_update, content, count=1, flags=re.DOTALL)
        print("✅ Обновлен SQL UPDATE для сохранения avito_user_id (альтернативный паттерн)")
    else:
        print("⚠️ Не найден SQL UPDATE для обновления - возможно уже обновлен")

# Сохраняем
with open('/app/main.py', 'w') as f:
    f.write(content)

print("✅ Файл main.py успешно обновлен!")
EOFIX

# Копируем скрипт в контейнер
echo "📦 Копирование скрипта в контейнер..."
docker cp /tmp/fix_callback.py avito-service:/tmp/

# Запускаем скрипт
echo "⚙️  Применение патча..."
docker exec avito-service python3 /tmp/fix_callback.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Callback успешно обновлен!"
    echo ""
    echo "🔄 Перезапуск контейнера..."
    cd /opt/avito-service && docker compose restart

    echo ""
    echo "=========================================="
    echo "✅ ВСЁ ГОТОВО!"
    echo "=========================================="
    echo ""
    echo "📝 ТЕПЕРЬ ПЕРЕАВТОРИЗУЙТЕ ЛЮБОЙ ПРОФИЛЬ:"
    echo ""
    echo "   1. Откройте браузер: http://ваш-сервер:8003"
    echo "   2. Войдите в систему"
    echo "   3. Выберите профиль"
    echo "   4. Нажмите 'Авторизовать в Avito'"
    echo "   5. Подтвердите авторизацию"
    echo ""
    echo "После авторизации запустите проверку:"
    echo "   ./check-messenger-status.sh"
    echo ""
else
    echo ""
    echo "❌ Ошибка при применении патча"
    echo ""
fi
