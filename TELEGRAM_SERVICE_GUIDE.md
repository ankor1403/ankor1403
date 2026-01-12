# 📱 Руководство по устранению проблем Telegram Multi-Service

## 🔍 Проблема

Не работает авторизация Telegram через QR код и отправка кода подтверждения в telegram-multi-service.

## 🛠️ Созданные инструменты

### 1. **telegram_diagnostic.sh** - Диагностика сервиса

Проверяет состояние всех компонентов системы.

**Использование:**
```bash
bash telegram_diagnostic.sh
```

**Что проверяет:**
- ✅ Статус Docker контейнеров
- ✅ Переменные окружения Telegram API
- ✅ Логи сервиса
- ✅ Состояние базы данных
- ✅ Доступность веб-интерфейса

---

### 2. **test_telegram_auth.py** - Тестирование авторизации

Интерактивный скрипт для тестирования методов авторизации Telegram.

**Использование на сервере:**
```bash
# Скопировать скрипт на сервер
scp test_telegram_auth.py root@83.222.25.94:/tmp/

# Запустить в контейнере
ssh root@83.222.25.94 "docker cp /tmp/test_telegram_auth.py telegram-multi-service:/tmp/"
ssh root@83.222.25.94 "docker exec -it telegram-multi-service python3 /tmp/test_telegram_auth.py"
```

**Возможности:**
- 📨 Тест отправки SMS кода
- 📲 Тест QR авторизации
- 🔐 Проверка существующей авторизации

---

### 3. **fix_telegram_service.sh** - Автоматическое исправление

Полностью перезапускает и настраивает сервис.

**Использование:**
```bash
bash fix_telegram_service.sh
```

**Что делает:**
- 🛑 Останавливает сервис
- 💾 Создает бэкап данных
- ⚙️ Проверяет конфигурацию
- 🔧 Настраивает переменные окружения
- 🔨 Пересобирает контейнер
- ▶️ Запускает сервис
- ✅ Проверяет работоспособность

---

### 4. **test_api_endpoints.sh** - Тестирование API

Проверяет все публичные endpoint'ы сервиса.

**Использование:**
```bash
bash test_api_endpoints.sh
```

**Что тестирует:**
- 🌐 Главная страница
- 💚 Health endpoints
- 📝 Регистрация/Вход
- 📊 API документация
- 🔌 Старый API сервис

---

## 🚀 Пошаговое решение проблемы

### Шаг 1: Диагностика
```bash
bash telegram_diagnostic.sh > diagnostic_report.txt
cat diagnostic_report.txt
```

### Шаг 2: Проверка API endpoint'ов
```bash
bash test_api_endpoints.sh > api_test_report.txt
cat api_test_report.txt
```

### Шаг 3: Исправление (если нужно)
```bash
bash fix_telegram_service.sh
```

### Шаг 4: Тестирование авторизации
```bash
# На сервере
scp test_telegram_auth.py root@83.222.25.94:/tmp/
ssh root@83.222.25.94 "docker cp /tmp/test_telegram_auth.py telegram-multi-service:/tmp/ && docker exec -it telegram-multi-service python3 /tmp/test_telegram_auth.py"
```

---

## 🔧 Ручное исправление проблем

### Проблема 1: API credentials не работают

```bash
ssh root@83.222.25.94 "docker exec telegram-multi-service env | grep TELEGRAM_API"
```

Если пусто или неверно, создайте/исправьте `.env`:

```bash
ssh root@83.222.25.94 "cat > /opt/telegram_multi_service/.env << 'EOF'
TELEGRAM_API_ID=28561380
TELEGRAM_API_HASH=c07bd084d44bb8f3d377aa6e1ea859ff
DATABASE_PATH=/app/data/multi.db
EOF"

ssh root@83.222.25.94 "cd /opt/telegram_multi_service && docker-compose restart"
```

---

### Проблема 2: Не отправляется код авторизации

**Причины:**
- ❌ Неверный формат номера телефона
- ❌ Flood ограничение (слишком много запросов)
- ❌ Заблокированный API ID

**Решение:**

1. Проверьте формат номера (должен быть +79277416299)
2. Подождите 10-15 минут перед повторной попыткой
3. Проверьте API credentials на https://my.telegram.org/apps

---

### Проблема 3: QR код не генерируется

**Требования для QR авторизации:**
- Telethon >= 1.24
- Модуль qrcode (опционально, для отображения)

**Установка зависимостей:**

```bash
ssh root@83.222.25.94 "docker exec telegram-multi-service pip install telethon>=1.24 qrcode"
ssh root@83.222.25.94 "docker restart telegram-multi-service"
```

---

### Проблема 4: База данных повреждена

**Проверка:**
```bash
ssh root@83.222.25.94 "docker exec telegram-multi-service python3 -c \"
import sqlite3
conn = sqlite3.connect('/app/data/multi.db')
print('OK')
conn.close()
\""
```

**Восстановление из бэкапа:**
```bash
ssh root@83.222.25.94 "docker exec telegram-multi-service cp /app/data.backup.*/multi.db /app/data/multi.db"
ssh root@83.222.25.94 "docker restart telegram-multi-service"
```

---

## 📊 Проверка логов в реальном времени

```bash
# Логи Multi-Service
ssh root@83.222.25.94 "docker logs -f telegram-multi-service"

# Логи Caddy (прокси)
ssh root@83.222.25.94 "docker logs -f wappi-caddy"

# Фильтр по ошибкам
ssh root@83.222.25.94 "docker logs -f telegram-multi-service 2>&1 | grep -i error"
```

---

## 🌐 Доступ к сервису

### Веб-интерфейс:
- **Multi-Service**: https://telegram.afonin-lisa.ru/
- **Старый API**: https://tg.api.afonin-lisa.ru/
- **Документация**: https://telegram.afonin-lisa.ru/docs

### API Endpoints:

#### Регистрация
```bash
curl -X POST https://telegram.afonin-lisa.ru/register \
  -H "Content-Type: application/json" \
  -d '{"username":"myuser","password":"mypass"}'
```

#### Вход
```bash
curl -X POST https://telegram.afonin-lisa.ru/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=myuser&password=mypass"
```

#### Создание Telegram профиля
```bash
curl -X POST https://telegram.afonin-lisa.ru/profile/create \
  -H "Cookie: session_token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"MyProfile","phone":"+79277416299"}'
```

---

## 🆘 Экстренное восстановление

Если ничего не помогает:

```bash
# Полная переустановка
ssh root@83.222.25.94 "cd /opt/telegram_multi_service && \
  docker-compose down -v && \
  docker-compose build --no-cache && \
  docker-compose up -d"
```

---

## 📞 Поддержка

Если проблемы сохраняются, проверьте:

1. **Telegram API статус**: https://core.telegram.org/api/status
2. **Лимиты API**: Возможно, исчерпан лимит запросов
3. **Firewall**: Убедитесь, что порты 443, 80 открыты
4. **DNS**: Проверьте, что домены резолвятся правильно

```bash
nslookup telegram.afonin-lisa.ru
nslookup tg.api.afonin-lisa.ru
```

---

## 📝 Логирование проблем

Соберите полную диагностику:

```bash
bash telegram_diagnostic.sh > full_diagnostic.txt 2>&1
bash test_api_endpoints.sh >> full_diagnostic.txt 2>&1
ssh root@83.222.25.94 "docker logs telegram-multi-service --tail=500" >> full_diagnostic.txt 2>&1
```

Отправьте `full_diagnostic.txt` для анализа.
