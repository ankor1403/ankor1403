#!/bin/bash
# Emergency fix для Avito Messenger - восстановление работоспособности

echo "🚨 АВАРИЙНОЕ ВОССТАНОВЛЕНИЕ AVITO SERVICE"
echo "=========================================="
echo ""

# Функция для создания простого шаблона index.html
create_simple_templates() {
    echo "📝 Создание простых рабочих шаблонов..."
    
    # index.html - простая страница входа
    cat > /opt/avito-service/app/templates/index.html << 'EOHTML'
<!DOCTYPE html>
<html>
<head>
    <title>Avito Multi-Service</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>Добро пожаловать в Avito Multi-Service Platform</h1>
    <form method="post" action="/login">
        <input type="text" name="username" placeholder="Логин" required>
        <input type="password" name="password" placeholder="Пароль" required>
        <button type="submit">Войти</button>
    </form>
</body>
</html>
EOHTML

    # dashboard.html
    cat > /opt/avito-service/app/templates/dashboard.html << 'EOHTML'
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>Мои профили Avito</h1>
    <p>Пользователь: {{ user.username }}</p>
    
    <h2>Список профилей:</h2>
    <ul>
    {% for profile in profiles %}
        <li>
            <a href="/profile/{{ profile.id }}">{{ profile.name }}</a>
            {% if profile.access_token %}✅{% else %}⚠️{% endif %}
        </li>
    {% endfor %}
    </ul>
    
    <form method="post" action="/profile/create">
        <button type="submit">Создать новый профиль</button>
    </form>
    
    <p><a href="/logout">Выйти</a></p>
</body>
</html>
EOHTML

    # profile.html
    cat > /opt/avito-service/app/templates/profile.html << 'EOHTML'
<!DOCTYPE html>
<html>
<head>
    <title>Профиль {{ profile.name }}</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>{{ profile.name }}</h1>
    
    {% if profile.access_token %}
        <p style="color: green;">✅ Авторизован в Avito</p>
        {% if profile.avito_user_id %}
        <p>User ID: {{ profile.avito_user_id }}</p>
        {% endif %}
    {% else %}
        <p style="color: orange;">⚠️ Не авторизован</p>
    {% endif %}
    
    <h2>Действия:</h2>
    <a href="/avito/authorize/{{ profile.id }}">
        <button>Авторизовать в Avito</button>
    </a>
    
    {% if messages %}
    <h2>Сообщения ({{ messages|length }}):</h2>
    <ul>
    {% for msg in messages %}
        <li>{{ msg.direction }} | {{ msg.created_at }}: {{ msg.content }}</li>
    {% endfor %}
    </ul>
    {% endif %}
    
    <p><a href="/dashboard">← Назад</a></p>
</body>
</html>
EOHTML

    echo "✅ Шаблоны созданы"
}

# Функция для патча main.py - добавить сохранение avito_user_id
patch_main_py() {
    echo "🔧 Патчинг main.py для сохранения avito_user_id..."
    
    # Создать Python скрипт для патча
    cat > /tmp/patch_main.py << 'EOPYTHON'
import re

# Читаем файл
with open('/opt/avito-service/app/main.py', 'r') as f:
    content = f.read()

# Проверяем что уже не пропатчено
if 'avito_user_id = ' in content and 'UPDATE profiles SET access_token = ?, refresh_token = ?, avito_user_id = ?' in content:
    print("✅ Файл уже содержит код сохранения avito_user_id")
    exit(0)

# Шаг 1: Убедиться что есть получение avito_user_id после получения токена
if 'avito_user_id = ' not in content:
    # Найти место после token_data = token_response.json()
    insert_after = 'token_data = token_response.json()'
    
    user_id_code = '''
        
        # Получить avito_user_id
        avito_user_id = None
        try:
            user_info_response = requests.get(
                f"{AVITO_API_URL}/core/v1/accounts/self",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            if user_info_response.status_code == 200:
                user_info = user_info_response.json()
                avito_user_id = str(user_info.get('id'))
                logger.info(f"Got avito_user_id: {avito_user_id} for profile {profile_id}")
        except Exception as e:
            logger.error(f"Error getting avito_user_id: {e}")
'''
    
    if insert_after in content:
        content = content.replace(insert_after, insert_after + user_id_code, 1)
        print("✅ Добавлен код получения avito_user_id")

# Шаг 2: Обновить SQL UPDATE
# Ищем старый UPDATE (может быть в разных форматах)
old_patterns = [
    (r'cursor\.execute\(\s*"UPDATE profiles SET access_token = \?, refresh_token = \? WHERE id = \?"\s*,\s*\([^)]+\)\s*\)',
     'cursor.execute("UPDATE profiles SET access_token = ?, refresh_token = ?, avito_user_id = ? WHERE id = ? AND user_id = ?", (token_data["access_token"], token_data.get("refresh_token"), avito_user_id, profile_id, user_id))'),
    
    (r'conn\.execute\(\s*"""UPDATE profiles\s+SET access_token = \?,\s+refresh_token = \?\s+WHERE id = \?"""\s*,\s*\([^)]+\)\s*\)',
     'conn.execute("""UPDATE profiles SET access_token = ?, refresh_token = ?, avito_user_id = ? WHERE id = ? AND user_id = ?""", (token_data["access_token"], token_data.get("refresh_token"), avito_user_id, profile_id, user_id))')
]

for pattern, replacement in old_patterns:
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        print(f"✅ SQL UPDATE обновлён для сохранения avito_user_id")
        break
else:
    print("⚠️ Паттерн UPDATE не найден, возможно уже обновлён")

# Сохранить
with open('/opt/avito-service/app/main.py', 'w') as f:
    f.write(content)

print("✅ main.py успешно пропатчен!")
EOPYTHON

    python3 /tmp/patch_main.py
}

# Основной процесс восстановления
echo "1️⃣ Восстановление старого рабочего main.py..."
cp /opt/avito-service/app/main.py.old.backup /opt/avito-service/app/main.py
echo "✅ main.py восстановлен"

echo ""
echo "2️⃣ Создание совместимых шаблонов..."
create_simple_templates

echo ""
echo "3️⃣ Применение патча для сохранения avito_user_id..."
patch_main_py

echo ""
echo "4️⃣ Перезапуск контейнера..."
cd /opt/avito-service
docker compose restart

echo ""
echo "5️⃣ Ожидание запуска сервиса..."
sleep 5

echo ""
echo "6️⃣ Проверка работоспособности..."
if curl -s http://localhost:8300 | grep -q "Avito"; then
    echo "✅ Сервис работает!"
else
    echo "❌ Ошибка! Смотрим логи:"
    docker logs avito-service 2>&1 | tail -20
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ ВОССТАНОВЛЕНИЕ ЗАВЕРШЕНО!"
echo "=========================================="
echo ""
echo "Откройте: http://avito.afonin-lisa.ru"
echo "Авторизуйте профиль для получения avito_user_id"
echo ""
echo "Проверка статуса:"
echo "  cd /opt/avito-service && ./check-messenger-status.sh"
