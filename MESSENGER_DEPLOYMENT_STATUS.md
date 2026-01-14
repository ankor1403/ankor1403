# Avito Messenger - Статус Развертывания

## 📊 Текущее Состояние

### ✅ Что Работает:
- OAuth авторизация профилей Avito
- Web интерфейс (http://сервер:8003)
- База данных SQLite с профилями
- Background worker запускается
- Токены access_token и refresh_token сохраняются

### ⚠️ Что НЕ Работает:
- **Worker не опрашивает сообщения** - причина: у всех профилей отсутствует `avito_user_id`
- Чтение сообщений из Avito
- Отправка сообщений
- Автоответчик
- N8N webhook интеграция

## 🔍 Проблема

### Суть Проблемы:
После OAuth авторизации профили получают `access_token` и `refresh_token`, но **не получают `avito_user_id`**.

Worker требует `avito_user_id` для работы с Messenger API:
```sql
-- Worker ищет профили с обоими полями
WHERE p.access_token IS NOT NULL
  AND p.avito_user_id IS NOT NULL  -- ❌ Все профили имеют NULL
```

### Почему так произошло:
Старый код OAuth callback не вызывал API endpoint `/core/v1/accounts/self` для получения user ID после авторизации.

### Текущее состояние БД:
```
id  | name                          | avito_user_id
----|-------------------------------|---------------
22  | Avito Profile 2026-01-14 03:52| ❌ ПУСТО
25  | Avito Profile 2026-01-14 04:24| ❌ ПУСТО
26  | Avito Profile 2026-01-14 04:34| ❌ ПУСТО
27  | Avito Profile 2026-01-14 04:38| ❌ ПУСТО
```

## 🔧 Решение

### Шаг 1: Проверить Текущее Состояние

На сервере VPS запустите:
```bash
cd /opt/avito-service
./check-messenger-status.sh
```

Этот скрипт покажет:
- Список профилей и их статус
- Наличие avito_user_id
- Статус worker
- Количество сообщений в БД

### Шаг 2: Применить Фикс Callback (если нужно)

Если скрипт выше показал, что callback НЕ содержит код получения user_id:
```bash
cd /opt/avito-service
./fix-callback-user-id.sh
```

Этот скрипт:
1. Модифицирует `main.py` для получения avito_user_id
2. Обновляет SQL запрос для сохранения user_id
3. Перезапускает контейнер

### Шаг 3: Переавторизовать Профиль

⚠️ **КРИТИЧЕСКИ ВАЖНО**: Необходимо ПЕРЕАВТОРИЗОВАТЬ хотя бы один профиль!

1. Откройте в браузере: `http://ваш-сервер:8003`
2. Войдите в систему
3. Выберите **существующий** профиль (например, профиль #22)
4. Нажмите кнопку **"Авторизовать в Avito"**
5. Подтвердите авторизацию на сайте Avito

### Шаг 4: Проверить Результат

После авторизации запустите проверку:
```bash
./check-messenger-status.sh
```

Вы должны увидеть:
```
id  | name                          | avito_user_id
----|-------------------------------|---------------
22  | Avito Profile 2026-01-14 03:52| ✅ 12345678
```

### Шаг 5: Мониторинг Worker

Запустите мониторинг работы worker:
```bash
./monitor-worker.sh
```

Вы должны увидеть логи типа:
```
INFO:messenger_worker:Polling messages for profile 22...
INFO:messenger_worker:Found 3 unread chats for profile 22
INFO:messenger_worker:Processing chat a1b2c3d4...
INFO:messenger_worker:Saved message #12345 to database
```

## 📋 Как Должен Работать Worker

После успешной настройки worker будет:

1. **Каждые 30 секунд** опрашивать Avito API для каждого профиля с `avito_user_id`
2. **Получать непрочитанные чаты**: `GET /messenger/v1/accounts/{user_id}/chats?unread_only=true`
3. **Получать сообщения**: `GET /messenger/v2/accounts/{user_id}/chats/{chat_id}/messages/`
4. **Сохранять в БД** новые сообщения
5. **Отправлять в N8N webhook** (если настроен)
6. **Отправлять автоответы** (если включен autoresponder)
7. **Обновлять токены** за 1 час до истечения

## 🎯 Конфигурация Профилей

После того как worker заработает, можно настроить функции для каждого профиля:

### Формат features в БД:
```json
{
  "messenger_read": true,      // Читать сообщения
  "messenger_write": true,     // Отправлять сообщения
  "autoresponder": false,      // Автоответчик
  "stats": false               // Статистика
}
```

### Настройка Автоответчика:

В поле `autoresponder_text` профиля:
```
привет:Здравствуйте! Чем могу помочь?|цена:Цену уточняйте в объявлении|адрес:Адрес указан в описании
```

Формат: `ключевое_слово:ответ|ключевое_слово2:ответ2|...`

### Настройка N8N Webhook:

В поле `n8n_webhook_url` профиля:
```
https://ваш-n8n.com/webhook/avito-messages
```

## 🐛 Диагностика Проблем

### Проблема: Worker не опрашивает сообщения

**Проверка 1**: Есть ли avito_user_id?
```bash
docker exec avito-service sqlite3 /app/avito.db \
  "SELECT id, name, avito_user_id FROM profiles WHERE avito_user_id IS NOT NULL;"
```

Если пусто - нужно переавторизовать профиль!

**Проверка 2**: Включен ли messenger_read?
```bash
docker exec avito-service sqlite3 /app/avito.db \
  "SELECT id, name, features FROM profiles;"
```

Должно быть: `"messenger_read": true`

**Проверка 3**: Запущен ли worker?
```bash
docker logs avito-service 2>&1 | grep "Messenger worker"
```

Должно быть: `INFO:messenger_worker:Messenger worker started`

### Проблема: Ошибки при опросе API

**Проверка токена**:
```bash
docker exec avito-service sqlite3 /app/avito.db \
  "SELECT id, token_expires_at FROM profiles WHERE id = 22;"
```

Если токен истек - worker автоматически обновит его.

**Проверка логов API**:
```bash
docker logs -f avito-service | grep -i "api\|авито\|error"
```

### Проблема: Сообщения не сохраняются

**Проверка структуры БД**:
```bash
docker exec avito-service sqlite3 /app/avito.db ".schema messages"
```

**Проверка сообщений**:
```bash
docker exec avito-service sqlite3 /app/avito.db \
  "SELECT COUNT(*), profile_id FROM messages GROUP BY profile_id;"
```

## 📁 Важные Файлы

### На Сервере:
- `/opt/avito-service/app/main.py` - основное приложение FastAPI
- `/opt/avito-service/app/messenger_worker.py` - worker для опроса сообщений
- `/opt/avito-service/app/avito_api_client.py` - клиент Avito API
- `/opt/avito-service/data/avito.db` - база данных SQLite
- `/opt/avito-service/docker-compose.yml` - конфигурация Docker

### В Репозитории:
- `check-messenger-status.sh` - проверка статуса
- `fix-callback-user-id.sh` - фикс callback для получения user_id
- `monitor-worker.sh` - мониторинг worker
- `MESSENGER_DEPLOYMENT_STATUS.md` - этот документ

## 🚀 Быстрый Старт

Если вы начинаете с нуля:

```bash
# 1. Проверить состояние
cd /opt/avito-service
./check-messenger-status.sh

# 2. Если нужно - применить фикс
./fix-callback-user-id.sh

# 3. Переавторизовать профиль в браузере
# http://ваш-сервер:8003 → Выбрать профиль → Авторизовать в Avito

# 4. Проверить снова
./check-messenger-status.sh

# 5. Запустить мониторинг
./monitor-worker.sh
```

## ❓ FAQ

**Q: Почему нужно переавторизовывать профили?**
A: Старый callback не получал avito_user_id. Новый callback получает его, но только при новой авторизации.

**Q: Потеряются ли токены при переавторизации?**
A: Нет, токены будут обновлены новыми, но профиль останется тот же.

**Q: Можно ли просто добавить avito_user_id в БД вручную?**
A: Теоретически да, но вы не знаете свой Avito user_id. Проще переавторизоваться.

**Q: Как часто worker опрашивает сообщения?**
A: Каждые 30 секунд для каждого профиля с messenger_read=true.

**Q: Worker создает слишком много запросов к API?**
A: Worker опрашивает только непрочитанные чаты (unread_only=true), что минимизирует запросы.

**Q: Можно ли изменить частоту опроса?**
A: Да, в messenger_worker.py измените `self.poll_interval = 30` на нужное значение (в секундах).

## 📞 Поддержка

Если возникли проблемы:
1. Запустите `./check-messenger-status.sh` и предоставьте вывод
2. Соберите логи: `docker logs avito-service > avito-logs.txt`
3. Проверьте БД: `docker exec avito-service sqlite3 /app/avito.db ".dump profiles"`

---

**Последнее обновление**: 2026-01-14
**Версия документа**: 1.0
