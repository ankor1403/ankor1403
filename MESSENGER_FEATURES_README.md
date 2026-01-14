# Avito Messenger Features - Руководство

## 🎉 Добавленные функции

### 1. **Чтение сообщений из Avito**
- Фоновая задача автоматически проверяет новые сообщения каждые 30 секунд
- Все сообщения сохраняются в базу данных
- Поддержка нескольких профилей одновременно
- Работает только для профилей с включенной функцией "Чтение сообщений"

### 2. **Отправка сообщений**
- API endpoints для отправки сообщений в чаты
- Ручная отправка через веб-интерфейс
- Все отправленные сообщения сохраняются в БД
- Поддержка длинных сообщений

### 3. **Автоответчик**
- Автоматические ответы на входящие сообщения
- Два режима:
  - **Ключевые слова**: `ключ1:ответ1|ключ2:ответ2`
  - **Дефолтный ответ**: просто текст (отвечает на все сообщения)
- Пример: `цена:Цена в объявлении актуальна|наличие:Товар в наличии`

### 4. **Интеграция с N8N**
- Автоматическая отправка новых сообщений на webhook
- Формат данных:
```json
{
  "profile_id": 22,
  "profile_name": "Мой профиль",
  "chat_id": "chat_12345",
  "message": {
    "id": "msg_67890",
    "text": "Текст сообщения",
    "author_id": "user_123",
    ...
  },
  "timestamp": "2026-01-14T10:30:00"
}
```

### 5. **Автоматическое обновление токенов**
- Токены автоматически обновляются за 1 час до истечения
- Не нужно вручную переавторизовываться
- Токены живут 24 часа, обновляются автоматически

### 6. **API Endpoints**

#### GET `/api/profile/{profile_id}/chats`
Получить список всех чатов профиля
```bash
curl -H "Cookie: session=YOUR_SESSION" \
  https://avito.afonin-lisa.ru/api/profile/22/chats
```

#### GET `/api/profile/{profile_id}/chat/{chat_id}/messages`
Получить сообщения из конкретного чата
```bash
curl -H "Cookie: session=YOUR_SESSION" \
  https://avito.afonin-lisa.ru/api/profile/22/chat/CHAT_ID/messages
```

#### POST `/api/profile/{profile_id}/chat/{chat_id}/send`
Отправить сообщение в чат
```bash
curl -X POST \
  -H "Cookie: session=YOUR_SESSION" \
  -F "text=Привет! Спасибо за вопрос." \
  https://avito.afonin-lisa.ru/api/profile/22/chat/CHAT_ID/send
```

## 📦 Установка

### На сервере root@ixhyswhgny:

```bash
# 1. Скопируйте файлы с локальной машины
scp /home/user/ankor1403/avito_api_client.py root@ixhyswhgny:/tmp/
scp /home/user/ankor1403/messenger_worker.py root@ixhyswhgny:/tmp/
scp /home/user/ankor1403/main_updated.py root@ixhyswhgny:/tmp/
scp /home/user/ankor1403/deploy-messenger-features.sh root@ixhyswhgny:/tmp/

# 2. Запустите скрипт развертывания
ssh root@ixhyswhgny
cd /tmp
chmod +x deploy-messenger-features.sh
./deploy-messenger-features.sh
```

## ⚙️ Настройка профиля

1. **Авторизуйте профиль в Avito**
   - Перейдите на страницу профиля
   - Нажмите "Авторизовать в Avito"
   - Подтвердите доступ

2. **Включите нужные функции** (чекбоксы)
   - ✅ Чтение сообщений - фоновая проверка новых сообщений
   - ✅ Отправка сообщений - возможность отвечать
   - ✅ Автоответчик - автоматические ответы
   - ✅ Статистика - сбор статистики (будет реализовано позже)

3. **Настройте автоответчик**

   **Вариант 1 - Ключевые слова:**
   ```
   цена:Цена указана в объявлении|наличие:Товар в наличии|доставка:Доставка обсуждается индивидуально
   ```

   **Вариант 2 - Дефолтный ответ:**
   ```
   Спасибо за вопрос! Отвечу в ближайшее время.
   ```

4. **Добавьте N8N Webhook** (опционально)
   - Создайте Webhook в N8N
   - Вставьте URL в поле "N8N Webhook URL"
   - Формат: `https://your-n8n.com/webhook/avito-messages`

## 🔍 Мониторинг

### Проверка логов
```bash
docker compose logs --tail=100 -f
```

### Проверка базы данных
```bash
# Количество сообщений
sqlite3 data/avito.db "SELECT COUNT(*) FROM messages;"

# Последние сообщения
sqlite3 data/avito.db "SELECT * FROM messages ORDER BY created_at DESC LIMIT 10;"

# Статус профилей
sqlite3 data/avito.db "SELECT id, name, avito_user_id FROM profiles;"
```

### Health Check
```bash
curl https://avito.afonin-lisa.ru/health
```

## 🐛 Устранение проблем

### Сообщения не приходят
1. Проверьте, что профиль авторизован (есть `access_token` и `avito_user_id`)
2. Проверьте, что включена функция "Чтение сообщений"
3. Проверьте логи на ошибки: `docker compose logs --tail=50`

### Автоответчик не работает
1. Убедитесь, что включена функция "Автоответчик"
2. Проверьте формат правил автоответчика
3. Проверьте, что есть текст автоответчика

### Токен истек
- Токены обновляются автоматически
- Если обновление не сработало, переавторизуйте профиль вручную

### N8N не получает данные
1. Проверьте URL webhook (должен быть доступен извне)
2. Проверьте логи на ошибки отправки
3. Проверьте N8N на входящие запросы

## 📊 Структура базы данных

### Таблица `profiles`
- `id` - ID профиля
- `user_id` - ID пользователя
- `name` - Название профиля
- `access_token` - OAuth токен
- `refresh_token` - Refresh токен
- `token_expires_at` - Время истечения токена
- `avito_user_id` - **НОВОЕ** ID пользователя в Avito
- `features` - JSON с включенными функциями
- `autoresponder_text` - Текст автоответчика
- `n8n_webhook` - URL N8N webhook

### Таблица `messages`
- `id` - ID сообщения
- `profile_id` - ID профиля
- `avito_message_id` - ID сообщения в Avito
- `chat_id` - **НОВОЕ** ID чата
- `direction` - Направление (`in` или `out`)
- `content` - Текст сообщения
- `author_id` - **НОВОЕ** ID автора
- `created_at` - Дата создания

### Таблица `chats` (**НОВАЯ**)
- `id` - ID записи
- `profile_id` - ID профиля
- `avito_chat_id` - ID чата в Avito
- `item_id` - ID объявления
- `last_message_at` - Время последнего сообщения
- `last_checked_at` - Время последней проверки
- `unread_count` - Количество непрочитанных

## 🔐 Безопасность

- Токены хранятся в зашифрованной базе данных
- Webhook URL должен быть защищен в N8N
- Логи не содержат токенов доступа
- Session cookies используют httpOnly

## 📝 TODO (будущие улучшения)

- [ ] Веб-интерфейс для просмотра чатов и отправки сообщений
- [ ] Статистика сообщений (графики, аналитика)
- [ ] Шаблоны ответов
- [ ] Расписание автоответчика (работать только в определенное время)
- [ ] Telegram уведомления о новых сообщениях
- [ ] Мультиязычность автоответчика
- [ ] AI-powered автоответчик с GPT

## 📚 Полезные ссылки

- [Avito API Documentation](https://developers.avito.ru/api-catalog)
- [Avito Messenger API GitHub](https://github.com/HamasakiBrain/avito-messenger)
- [N8N Documentation](https://docs.n8n.io/)

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker compose logs -f`
2. Проверьте статус: `curl https://avito.afonin-lisa.ru/health`
3. Проверьте БД: `sqlite3 data/avito.db`
4. Создайте issue в репозитории

---

**Версия:** 1.0.0
**Дата:** 2026-01-14
**Автор:** Claude AI Assistant
