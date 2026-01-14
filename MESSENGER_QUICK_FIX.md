# 🚀 Avito Messenger - Быстрое Исправление

## ⚡ Текущая Ситуация

Ваш Avito сервис работает, OAuth авторизация проходит успешно, но **messenger worker не опрашивает сообщения**.

### Причина:
У всех профилей отсутствует поле `avito_user_id`, которое необходимо worker для обращения к Messenger API.

```
Профиль 22: access_token ✅ | avito_user_id ❌
Профиль 25: access_token ✅ | avito_user_id ❌
Профиль 26: access_token ✅ | avito_user_id ❌
Профиль 27: access_token ✅ | avito_user_id ❌
```

## 🎯 Решение (3 простых шага)

### Вариант A: Если у вас есть SSH доступ к серверу

#### 1️⃣ Скопируйте скрипты на сервер:

```bash
cd /home/user/ankor1403
./deploy-diagnostic-scripts.sh root@ixhyswhgny
```

Или вручную:
```bash
scp check-messenger-status.sh root@ixhyswhgny:/opt/avito-service/
scp fix-callback-user-id.sh root@ixhyswhgny:/opt/avito-service/
scp monitor-worker.sh root@ixhyswhgny:/opt/avito-service/
```

#### 2️⃣ На сервере запустите диагностику:

```bash
ssh root@ixhyswhgny
cd /opt/avito-service
./check-messenger-status.sh
```

#### 3️⃣ Если скрипт показал, что callback нужно исправить:

```bash
./fix-callback-user-id.sh
```

#### 4️⃣ Переавторизуйте любой профиль:

1. Откройте браузер: `http://ваш-сервер:8003`
2. Войдите в систему
3. Выберите профиль (например, #22)
4. Нажмите **"Авторизовать в Avito"**
5. Подтвердите на сайте Avito

#### 5️⃣ Проверьте результат:

```bash
./check-messenger-status.sh
./monitor-worker.sh
```

---

### Вариант B: Если вы УЖЕ на сервере

Если вы уже подключены к серверу через SSH:

```bash
# 1. Перейдите в директорию
cd /opt/avito-service

# 2. Скачайте скрипты из репозитория
wget https://raw.githubusercontent.com/ваш-юзер/ankor1403/claude/audit-dependencies-mkbp0op9n8ha6qpk-Gt2Dm/check-messenger-status.sh
wget https://raw.githubusercontent.com/ваш-юзер/ankor1403/claude/audit-dependencies-mkbp0op9n8ha6qpk-Gt2Dm/fix-callback-user-id.sh
wget https://raw.githubusercontent.com/ваш-юзер/ankor1403/claude/audit-dependencies-mkbp0op9n8ha6qpk-Gt2Dm/monitor-worker.sh

# Сделайте исполняемыми
chmod +x *.sh

# 3. Запустите диагностику
./check-messenger-status.sh

# 4. Примените фикс (если нужно)
./fix-callback-user-id.sh

# 5. Переавторизуйте профиль в браузере (см. выше)

# 6. Проверьте
./check-messenger-status.sh
```

---

### Вариант C: Ручное исправление (если скрипты не работают)

#### На сервере выполните:

```bash
cd /opt/avito-service

# Создайте Python скрипт для патча
cat > /tmp/fix_callback.py << 'EOFIX'
import sys
import re

with open('/app/main.py', 'r') as f:
    content = f.read()

# Проверка
if 'Get Avito user_id' in content:
    print("✅ Уже исправлено")
    sys.exit(0)

# Добавляем AVITO_API_URL
if 'AVITO_API_URL' not in content:
    content = content.replace(
        'AVITO_TOKEN_URL = "https://api.avito.ru/token"',
        'AVITO_TOKEN_URL = "https://api.avito.ru/token"\nAVITO_API_URL = "https://api.avito.ru"'
    )

# Код получения user_id
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
        except Exception as e:
            avito_user_id = None
'''

# Вставляем после token_data = token_response.json()
pattern = r'(token_data = token_response\.json\(\)\s*\n)'
content = re.sub(pattern, r'\1' + insert_code + '\n', content, count=1)

# Обновляем SQL UPDATE
new_update = '''conn.execute(
            """UPDATE profiles
               SET access_token = ?,
                   refresh_token = ?,
                   token_expires_at = ?,
                   avito_user_id = ?
               WHERE id = ? AND user_id = ?""",
            (access_token, refresh_token, expires_at.isoformat(), avito_user_id, profile_id, user_id)'''

old_pattern = r'conn\.execute\(\s*"""UPDATE profiles\s+SET access_token = \?,\s+refresh_token = \?,\s+token_expires_at = \?\s+WHERE id = \? AND user_id = \?""",\s*\(access_token, refresh_token, expires_at\.isoformat\(\), profile_id, user_id\)'
content = re.sub(old_pattern, new_update, content, flags=re.DOTALL)

with open('/app/main.py', 'w') as f:
    f.write(content)

print("✅ Исправлено!")
EOFIX

# Примените патч
docker cp /tmp/fix_callback.py avito-service:/tmp/
docker exec avito-service python3 /tmp/fix_callback.py

# Перезапустите
docker compose restart
```

Затем переавторизуйте профиль в браузере.

---

## 🔍 Как Проверить Что Всё Работает

### 1. Проверьте что профиль получил avito_user_id:

```bash
docker exec avito-service sqlite3 /app/avito.db \
  "SELECT id, name, avito_user_id FROM profiles WHERE id = 22;"
```

Должно быть:
```
22|Avito Profile 2026-01-14 03:52|12345678
```

### 2. Проверьте логи worker:

```bash
docker logs -f avito-service | grep -i "polling\|chat\|message"
```

Должно появиться:
```
INFO:messenger_worker:Polling messages for profile 22...
INFO:messenger_worker:Found 2 unread chats
INFO:messenger_worker:Processing chat abc123...
```

### 3. Проверьте сообщения в БД:

```bash
docker exec avito-service sqlite3 /app/avito.db \
  "SELECT COUNT(*) FROM messages;"
```

Должно быть > 0 если есть непрочитанные сообщения.

---

## ❓ FAQ

**Q: Я переавторизовался, но avito_user_id всё равно пустой**

A: Проверьте логи при авторизации:
```bash
docker logs avito-service | grep -i "user_id\|callback"
```

Если видите ошибку - callback не был исправлен. Запустите `fix-callback-user-id.sh` снова.

**Q: Worker запущен, но не опрашивает сообщения**

A: Проверьте features профиля:
```bash
docker exec avito-service sqlite3 /app/avito.db \
  "SELECT id, features FROM profiles WHERE id = 22;"
```

Должно быть: `{"messenger_read": true, ...}`

Если нет:
```bash
docker exec avito-service sqlite3 /app/avito.db \
  "UPDATE profiles SET features = '{\"messenger_read\": true, \"messenger_write\": true}' WHERE id = 22;"
```

**Q: Ошибки в логах про API**

A: Проверьте что токен не истек:
```bash
docker exec avito-service sqlite3 /app/avito.db \
  "SELECT id, token_expires_at FROM profiles WHERE id = 22;"
```

Worker автоматически обновит токен за 1 час до истечения.

**Q: Можно ли добавить avito_user_id вручную?**

A: Технически да, но вы не знаете свой Avito user_id. Получить его можно только через API с access_token, что делает callback автоматически.

---

## 📞 Что Делать Если Ничего Не Помогло

1. Соберите диагностическую информацию:

```bash
cd /opt/avito-service

# Статус профилей
docker exec avito-service sqlite3 /app/avito.db \
  "SELECT id, name, avito_user_id, features FROM profiles;" > diagnosis.txt

# Логи
docker logs avito-service > avito-logs.txt 2>&1

# Проверка callback
docker exec avito-service grep -A 40 "def oauth_callback" /app/main.py > callback-code.txt
```

2. Проверьте файлы:
   - `diagnosis.txt` - состояние профилей
   - `avito-logs.txt` - логи приложения
   - `callback-code.txt` - код callback функции

3. Убедитесь что:
   - В callback-code.txt есть строка `# Get Avito user_id`
   - В diagnosis.txt хотя бы один профиль имеет непустой avito_user_id
   - В avito-logs.txt нет ошибок типа "Failed to get user_id"

---

## 📚 Полная Документация

Детальная документация: **MESSENGER_DEPLOYMENT_STATUS.md**

Файлы в репозитории:
- `check-messenger-status.sh` - Диагностика состояния
- `fix-callback-user-id.sh` - Исправление callback
- `monitor-worker.sh` - Мониторинг worker
- `MESSENGER_DEPLOYMENT_STATUS.md` - Полная документация
- `MESSENGER_QUICK_FIX.md` - Этот файл

---

**Последнее обновление**: 2026-01-14
**Версия**: 1.0
