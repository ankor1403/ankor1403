# 🚀 Avito Multi-Service - Полная Установка

**Дата:** 2026-01-13
**Статус:** Готово к развертыванию
**Сложность:** Средняя

## 📋 Что это?

**Avito Multi-Service** - это веб-платформа для управления несколькими аккаунтами Avito через единый интерфейс. Позволяет:

- ✅ Регистрация и вход по логину/паролю
- ✅ Управление несколькими профилями Avito (OAuth авторизация)
- ✅ Включение/выключение функций для каждого профиля:
  - 📨 Мессенджер (чтение/отправка сообщений)
  - 📦 Автозагрузка (создание/редактирование объявлений)
  - 📊 Статистика (просмотры, звонки, конверсия)
  - 🤖 Авторесподер (автоматические ответы)
- ✅ Интеграция с N8N через вебхуки
- ✅ HTTPS с автоматическими SSL сертификатами через Caddy

---

## 🔧 Требования

### Сервер
- Ubuntu 20.04+ / Debian 11+
- Docker 20.10+ и Docker Compose 2.0+
- 2GB RAM минимум
- 10GB свободного места

### Домены (у вас должны быть настроены DNS)
- `avito.afonin-lisa.ru` → IP вашего сервера
- `api.avito.afonin-lisa.ru` → IP вашего сервера

### Учетные данные Avito
- Client ID (из Avito Developer Portal)
- Client Secret (из Avito Developer Portal)
- Redirect URI (настроенный в Avito Developer Portal)

---

## 📦 Установка за 5 шагов

### Шаг 1: Клонирование репозитория

```bash
cd /opt
git clone https://github.com/ankor1403/ankor1403.git
cd ankor1403
```

### Шаг 2: Копирование файлов Avito Service

Файлы находятся в `/opt/avito-service/`:

```bash
# Структура:
/opt/avito-service/
├── app/
│   └── main.py           # Основное приложение FastAPI
├── templates/            # HTML шаблоны
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   └── profile_detail.html
├── data/                 # База данных SQLite (создается автоматически)
├── Dockerfile            # Образ Docker
├── docker-compose.yml    # Конфигурация запуска
├── requirements.txt      # Python зависимости (УСТАРЕЛО - см. ниже)
├── .env                  # Переменные окружения (API ключи)
├── deploy.sh            # Скрипт развертывания
├── fix_and_deploy.sh    # Полное исправление и развертывание
└── diagnose.sh          # Диагностика проблем
```

### Шаг 3: Настройка переменных окружения

Отредактируйте `/opt/avito-service/.env`:

```bash
nano /opt/avito-service/.env
```

Содержимое:

```env
AVITO_CLIENT_ID=your_client_id_here
AVITO_CLIENT_SECRET=your_client_secret_here
AVITO_REDIRECT_URI=https://avito.afonin-lisa.ru/api/v1/avito/callback
AVITO_WEBHOOK_URL=https://api.avito.afonin-lisa.ru/api/webhook
```

**Важно:** Замените `your_client_id_here` и `your_client_secret_here` на ваши реальные данные из Avito Developer Portal.

### Шаг 4: ⚠️ Обновление зависимостей (КРИТИЧНО!)

**ВАЖНО:** Текущий `requirements.txt` содержит **10 критических уязвимостей**! Используйте безопасную версию:

```bash
cd /opt/avito-service

# Создайте резервную копию старого файла
cp requirements.txt requirements-old.txt

# Скопируйте безопасную версию из репозитория
cp /opt/ankor1403/requirements-secure.txt requirements.txt

# Или создайте вручную:
cat > requirements.txt << 'EOF'
# Avito Multi-Service - Secure Dependencies
# All CVEs patched - See AVITO_DEPENDENCY_AUDIT.md

# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.32.0

# Templating
jinja2==3.1.5

# HTTP Client
requests==2.32.4

# Form Parsing
python-multipart==0.0.18
EOF
```

**Подробности:** См. [AVITO_DEPENDENCY_AUDIT.md](/home/user/ankor1403/AVITO_DEPENDENCY_AUDIT.md) для полного отчета по безопасности.

### Шаг 5: Обновление Caddyfile

Добавьте конфигурацию Avito в ваш Caddyfile (обычно `/root/lisa/Caddyfile` или используйте Caddyfile.unified из репозитория):

```bash
# Если используете unified Caddyfile из репозитория:
cp /opt/ankor1403/Caddyfile.unified /root/lisa/Caddyfile

# ИЛИ добавьте вручную в существующий Caddyfile:
cat >> /root/lisa/Caddyfile << 'EOF'

# ============================================
# AVITO MULTI-SERVICE
# ============================================
avito.afonin-lisa.ru {
  log {
    output file /var/log/caddy/avito.log
    format json
  }

  reverse_proxy avito-service:8300

  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Content-Type-Options nosniff
    Referrer-Policy strict-origin-when-cross-origin
    -Server
  }
}

api.avito.afonin-lisa.ru {
  log {
    output file /var/log/caddy/avito-api.log
    format json
  }

  reverse_proxy avito-service:8300

  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Content-Type-Options nosniff
    Referrer-Policy strict-origin-when-cross-origin
    -Server
  }
}
EOF
```

Перезапустите Caddy:

```bash
cd /root/lisa
docker compose restart caddy
```

---

## 🚀 Запуск

### Вариант А: Автоматический запуск (Рекомендуется)

```bash
cd /opt/avito-service
./fix_and_deploy.sh
```

Этот скрипт автоматически:
1. Остановит и удалит старые контейнеры
2. Удалит старые Docker образы
3. Соберет новый образ (без кэша)
4. Запустит контейнер
5. Проверит работоспособность
6. Найдет и обновит Caddyfile (если нужно)
7. Перезапустит Caddy

### Вариант Б: Ручной запуск

```bash
cd /opt/avito-service

# Остановка старых контейнеров
docker compose down

# Сборка образа
docker compose build --no-cache

# Запуск
docker compose up -d

# Проверка логов
docker compose logs -f
```

---

## ✅ Проверка работоспособности

### 1. Проверка контейнера

```bash
cd /opt/avito-service
docker compose ps
```

Должно показывать:
```
NAME            STATUS          PORTS
avito-service   Up X minutes    0.0.0.0:8300->8300/tcp
```

### 2. Проверка API

```bash
# Health check
curl http://localhost:8300/health

# Должно вернуть:
{"status":"healthy"}
```

### 3. Проверка веб-интерфейса

Откройте в браузере:
- http://localhost:8300 (локально)
- https://avito.afonin-lisa.ru (через интернет)

Должна появиться страница с кнопками "Войти" и "Зарегистрироваться".

### 4. Диагностика (если что-то не работает)

```bash
cd /opt/avito-service
./diagnose.sh
```

---

## 👤 Первое использование

### 1. Регистрация

1. Откройте https://avito.afonin-lisa.ru
2. Нажмите "Зарегистрироваться"
3. Введите username и password
4. Нажмите "Зарегистрироваться"

### 2. Вход

1. Введите ваш username и password
2. Нажмите "Войти"
3. Вы попадете в Dashboard (список ваших профилей Avito)

### 3. Добавление профиля Avito

1. На странице Dashboard нажмите "Добавить новый профиль"
2. Введите название профиля (например, "Мой магазин")
3. Нажмите "Подключить к Avito"
4. Вы будете перенаправлены на страницу авторизации Avito
5. Разрешите доступ к вашему аккаунту Avito
6. После успешной авторизации вы вернетесь в Dashboard
7. Профиль будет отображаться со статусом "✅ Подключен"

### 4. Управление профилем

Нажмите "Управление" на карточке профиля:

**Доступные функции:**
- 📨 **Мессенджер:** Включить для получения/отправки сообщений через API
- 📦 **Автозагрузка:** Включить для создания/редактирования объявлений
- 📊 **Статистика:** Включить для получения аналитики (просмотры, звонки)
- 🤖 **Авторесподер:** Включить для автоматических ответов

**Действия:**
- **Обновить токен:** Обновить OAuth токен (если истек)
- **Удалить профиль:** Удалить профиль из системы

---

## 🔐 Безопасность

### Критические уязвимости исправлены

✅ **10 CVE исправлено** в requirements-secure.txt:
- CVE-2024-24762 (FastAPI ReDoS) - HIGH
- CVE-2024-47874 (Starlette DoS) - HIGH
- CVE-2025-43859 (h11 Request Smuggling) - CRITICAL
- CVE-2024-53981 (python-multipart DoS) - HIGH
- CVE-2024-56201 (Jinja2 RCE) - HIGH
- CVE-2024-35195 (requests Cert Bypass) - MEDIUM
- CVE-2024-47081 (requests Credential Leak) - MEDIUM
- И другие...

**См. подробности:** [AVITO_DEPENDENCY_AUDIT.md](/home/user/ankor1403/AVITO_DEPENDENCY_AUDIT.md)

### Рекомендации

1. ✅ Никогда не коммитьте `.env` файл в git
2. ✅ Используйте сложные пароли (минимум 12 символов)
3. ⚠️ В production установите `secure=True` для cookies (требует HTTPS)
4. ⚠️ Добавьте CSRF защиту для форм
5. ⚠️ Настройте rate limiting для API endpoints
6. ⚠️ Используйте Redis для хранения сессий (вместо in-memory)

---

## 📝 Полезные команды

### Управление контейнером

```bash
cd /opt/avito-service

# Просмотр логов в реальном времени
docker compose logs -f

# Просмотр последних 100 строк
docker compose logs --tail=100

# Перезапуск
docker compose restart

# Остановка
docker compose down

# Полный пересборка и запуск
./fix_and_deploy.sh
```

### Работа с базой данных

```bash
# Подключение к SQLite базе
sqlite3 /opt/avito-service/data/avito.db

# Полезные SQL команды:
SELECT * FROM users;
SELECT * FROM profiles;
SELECT * FROM messages LIMIT 10;

# Выход: .quit
```

### Проверка структуры внутри контейнера

```bash
# Список файлов в контейнере
docker exec avito-service ls -la /app/

# Проверка Python импортов
docker exec avito-service python -c "import main; print('OK')"
```

---

## 🐛 Решение проблем

### Ошибка: "Internal Server Error"

**Причина:** Неправильные пути в Dockerfile или отсутствие шаблонов

**Решение:**
```bash
cd /opt/avito-service
./diagnose.sh

# Проверьте вывод секции "4️⃣ Файлы внутри контейнера"
# Должны быть:
# /app/main.py
# /app/templates/
# /app/data/

# Если файлов нет, пересоберите:
./fix_and_deploy.sh
```

### Ошибка: "Environment variables NOT SET"

**Причина:** `.env` файл не загружается в Docker

**Решение:**
Убедитесь, что в `docker-compose.yml` есть строка:
```yaml
env_file:
  - .env
```

Затем перезапустите:
```bash
docker compose down
docker compose up -d
```

### Ошибка OAuth: "Что-то пошло не так"

**Причины:**
1. Неправильный Client ID или Client Secret
2. Redirect URI не совпадает с настройками в Avito Developer Portal
3. Токен истек

**Решение:**
1. Проверьте `.env` файл
2. Убедитесь, что Redirect URI = `https://avito.afonin-lisa.ru/api/v1/avito/callback`
3. Убедитесь, что этот URI настроен в Avito Developer Portal
4. Проверьте логи: `docker compose logs -f`

### Ошибка: "Connection refused" к базе данных

**Причина:** Отсутствует директория `/app/data/`

**Решение:**
```bash
# Создайте директорию внутри контейнера
docker exec avito-service mkdir -p /app/data
docker compose restart
```

---

## 📚 Архитектура

### Стек технологий

- **Backend:** FastAPI 0.115.0 (Python 3.11)
- **Web Server:** Uvicorn 0.32.0
- **Database:** SQLite3
- **Templates:** Jinja2 3.1.5
- **HTTP Client:** Requests 2.32.4
- **Reverse Proxy:** Caddy 2.x (с автоматическим HTTPS)
- **Контейнеризация:** Docker + Docker Compose

### Структура базы данных

**Таблица: users**
- `id` - INTEGER PRIMARY KEY AUTOINCREMENT
- `username` - TEXT UNIQUE NOT NULL
- `password_hash` - TEXT NOT NULL
- `created_at` - TIMESTAMP DEFAULT CURRENT_TIMESTAMP

**Таблица: profiles**
- `id` - INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id` - INTEGER FOREIGN KEY → users.id
- `profile_name` - TEXT NOT NULL
- `avito_user_id` - TEXT (ID пользователя Avito)
- `access_token` - TEXT (OAuth токен)
- `refresh_token` - TEXT (Токен обновления)
- `token_expires_at` - TIMESTAMP
- `messenger_enabled` - BOOLEAN DEFAULT 0
- `autoload_enabled` - BOOLEAN DEFAULT 0
- `stats_enabled` - BOOLEAN DEFAULT 0
- `autoresponder_enabled` - BOOLEAN DEFAULT 0
- `created_at` - TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `updated_at` - TIMESTAMP DEFAULT CURRENT_TIMESTAMP

**Таблица: messages**
- `id` - INTEGER PRIMARY KEY AUTOINCREMENT
- `profile_id` - INTEGER FOREIGN KEY → profiles.id
- `message_id` - TEXT (ID сообщения в Avito)
- `chat_id` - TEXT
- `direction` - TEXT ('incoming' | 'outgoing')
- `text` - TEXT
- `created_at` - TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### API Endpoints

**Публичные (без авторизации):**
- `GET /` - Главная страница (перенаправление на login)
- `GET /login` - Страница входа
- `POST /login` - Вход пользователя
- `GET /register` - Страница регистрации
- `POST /register` - Регистрация пользователя
- `GET /api/v1/avito/callback` - OAuth callback от Avito

**Защищенные (требуют авторизации):**
- `GET /dashboard` - Список профилей пользователя
- `POST /profiles/new` - Создание нового профиля
- `GET /profiles/{profile_id}` - Детали профиля
- `POST /profiles/{profile_id}/toggle/{feature}` - Включение/выключение функции
- `POST /profiles/{profile_id}/delete` - Удаление профиля
- `POST /profiles/{profile_id}/refresh-token` - Обновление OAuth токена
- `GET /logout` - Выход

**Webhooks:**
- `POST /api/webhook` - Прием вебхуков от N8N/Avito

**Health Check:**
- `GET /health` - Проверка работоспособности

---

## 🔗 Интеграция с N8N

### Настройка в N8N

1. Создайте новый workflow в N8N
2. Добавьте HTTP Request node
3. Настройте:
   - Method: POST
   - URL: `https://api.avito.afonin-lisa.ru/api/webhook`
   - Authentication: None
   - Body: JSON

**Пример payload:**

```json
{
  "event": "new_message",
  "profile_id": 1,
  "chat_id": "12345",
  "message": "Привет! Когда можно посмотреть товар?"
}
```

### Отправка сообщений из N8N

```json
{
  "action": "send_message",
  "profile_id": 1,
  "chat_id": "12345",
  "text": "Здравствуйте! Товар доступен для просмотра завтра в 14:00"
}
```

---

## 📖 Полезные ссылки

### Документация Avito API
- [Avito Developer Portal](https://developers.avito.ru/)
- [OAuth 2.0 Authorization](https://developers.avito.ru/api-catalog/auth)
- [Messenger API](https://developers.avito.ru/api-catalog/messenger)
- [AutoLoad API](https://developers.avito.ru/api-catalog/autoload)

### Документация технологий
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Caddy Documentation](https://caddyserver.com/docs/)

---

## 🆘 Поддержка

Если у вас возникли проблемы:

1. Запустите диагностику:
   ```bash
   cd /opt/avito-service
   ./diagnose.sh > /tmp/avito-debug.log 2>&1
   cat /tmp/avito-debug.log
   ```

2. Проверьте отчет по безопасности:
   ```bash
   cat /opt/ankor1403/AVITO_DEPENDENCY_AUDIT.md
   ```

3. Создайте issue в репозитории: https://github.com/ankor1403/ankor1403/issues

---

**Последнее обновление:** 2026-01-13
**Версия:** 1.0.0
**Автор:** @ankor1403
**Лицензия:** MIT
