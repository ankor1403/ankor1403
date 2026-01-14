# Ручное Развертывание Avito Service на Сервере

**Для сервера:** root@ixhyswhgny
**Дата:** 2026-01-13

---

## Вариант 1: Автоматический (Рекомендуется)

### Шаг 1: Скопируйте скрипт на сервер

На вашем локальном компьютере выполните:

```bash
# Скопируйте скрипт на сервер
scp /home/user/ankor1403/deploy-avito-server.sh root@ixhyswhgny:/root/

# Подключитесь к серверу
ssh root@ixhyswhgny
```

### Шаг 2: Запустите скрипт

На сервере выполните:

```bash
cd /root
chmod +x deploy-avito-server.sh
./deploy-avito-server.sh
```

Скрипт автоматически:
- Обновит requirements.txt
- Исправит Avito API URLs
- Пересоберет Docker контейнер
- Запустит сервис
- Проверит работоспособность

---

## Вариант 2: Ручное развертывание (Шаг за шагом)

Используйте этот вариант если автоматический скрипт не работает.

### Шаг 1: Подключитесь к серверу

```bash
ssh root@ixhyswhgny
cd /opt/avito-service
```

### Шаг 2: Обновите requirements.txt

```bash
cat > /opt/avito-service/requirements.txt << 'EOF'
# Avito Multi-Service - Secure Dependencies
# Last Updated: 2026-01-13
# All CVEs patched

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

Проверьте:
```bash
cat requirements.txt
```

### Шаг 3: Исправьте Avito API URLs в main.py

```bash
# Исправьте Token URL
sed -i 's|https://api.avito.ru/oauth/token|https://api.avito.ru/token|g' /opt/avito-service/app/main.py

# Исправьте Auth URL
sed -i 's|https://api.avito.ru/oauth"|https://avito.ru/oauth"|g' /opt/avito-service/app/main.py
```

Проверьте изменения:
```bash
grep "AVITO_.*_URL" /opt/avito-service/app/main.py
```

Должно показать:
```python
AVITO_AUTH_URL = "https://avito.ru/oauth"
AVITO_TOKEN_URL = "https://api.avito.ru/token"
```

### Шаг 4: Проверьте .env файл

```bash
cat /opt/avito-service/.env
```

Убедитесь, что есть правильные значения:
```env
AVITO_CLIENT_ID=oRhUFoLmgR1oCXKKQhzg
AVITO_CLIENT_SECRET=2uxbvzFn7TPX3J1sfW0AqbHGIcEGesC06em_fNjg
AVITO_REDIRECT_URI=https://avito.afonin-lisa.ru/api/v1/avito/callback
AVITO_WEBHOOK_URL=https://api.avito.afonin-lisa.ru/api/webhook
```

**ВАЖНО:** Redirect URI должен быть `/api/v1/avito/callback`, а НЕ `/oauth/callback`!

Если неправильно, исправьте:
```bash
nano /opt/avito-service/.env
# Или используйте sed:
sed -i 's|/oauth/callback|/api/v1/avito/callback|g' /opt/avito-service/.env
```

### Шаг 5: Проверьте docker-compose.yml

```bash
cat /opt/avito-service/docker-compose.yml
```

Убедитесь, что есть строка `env_file: - .env`:

```yaml
version: '3.8'
services:
  avito-service:
    build: .
    container_name: avito-service
    restart: unless-stopped
    ports:
      - "8300:8300"
    volumes:
      - ./data:/app/data
    env_file:
      - .env      # <-- ЭТА СТРОКА ДОЛЖНА БЫТЬ!
    environment:
      - TZ=Europe/Moscow
    networks:
      - localai_default

networks:
  localai_default:
    external: true
```

Если строки `env_file` нет, добавьте её:
```bash
nano /opt/avito-service/docker-compose.yml
```

### Шаг 6: Остановите старый контейнер

```bash
cd /opt/avito-service
docker compose down
docker rm -f avito-service 2>/dev/null || true
```

### Шаг 7: Удалите старые образы

```bash
docker rmi -f avito-service:latest 2>/dev/null || true
docker image prune -f
```

### Шаг 8: Соберите новый образ

```bash
cd /opt/avito-service
docker compose build --no-cache
```

Это займет несколько минут. Вы должны увидеть процесс установки новых версий пакетов.

### Шаг 9: Запустите контейнер

```bash
docker compose up -d
```

### Шаг 10: Проверьте статус

```bash
# Проверьте что контейнер запущен
docker ps | grep avito-service

# Посмотрите логи
docker compose logs -f
```

Нажмите `Ctrl+C` чтобы выйти из просмотра логов.

### Шаг 11: Проверьте переменные окружения

```bash
docker exec avito-service python -c "
import os
print('Client ID:', os.getenv('AVITO_CLIENT_ID', 'NOT SET'))
print('Client Secret:', os.getenv('AVITO_CLIENT_SECRET', 'NOT SET')[:20] + '...')
print('Redirect URI:', os.getenv('AVITO_REDIRECT_URI', 'NOT SET'))
"
```

Должно показать ваши реальные значения, а НЕ "NOT SET"!

**Если показывает "NOT SET":**
1. Убедитесь что в docker-compose.yml есть `env_file: - .env`
2. Проверьте что .env файл существует
3. Перезапустите: `docker compose down && docker compose up -d`

### Шаг 12: Проверьте HTTP endpoint

```bash
curl http://localhost:8300/
```

Должна вернуться HTML страница (не ошибка).

### Шаг 13: Проверьте зависимости

```bash
docker exec avito-service pip list | grep -E "fastapi|uvicorn|jinja2|requests|python-multipart"
```

Должно показать:
```
fastapi              0.115.0
jinja2               3.1.5
python-multipart     0.0.18
requests             2.32.4
uvicorn              0.32.0
```

---

## Проверка работоспособности

### 1. Откройте браузер

Перейдите на: https://avito.afonin-lisa.ru

Должна открыться страница с кнопками "Войти" и "Зарегистрироваться".

### 2. Зарегистрируйтесь

Создайте новый аккаунт:
- Username: test_user
- Password: test_password123

### 3. Добавьте профиль Avito

1. Нажмите "Добавить новый профиль"
2. Введите название: "Тестовый профиль"
3. Нажмите "Подключить к Avito"
4. Вы будете перенаправлены на Avito OAuth

### 4. Разрешите доступ

На странице Avito:
1. Войдите в свой аккаунт Avito (если не вошли)
2. Нажмите "Разрешить доступ"

### 5. Проверьте результат

Вы должны вернуться на dashboard с подключенным профилем (статус "✅ Подключен").

**Если вместо этого видите ошибку:**
```bash
# Посмотрите логи контейнера
docker compose logs --tail=50

# Проверьте что показывает Avito при OAuth
# (смотрите в браузере URL с параметрами error=...)
```

---

## Решение проблем

### Ошибка: "Environment variables NOT SET"

**Причина:** docker-compose.yml не загружает .env файл

**Решение:**
```bash
# Откройте docker-compose.yml
nano /opt/avito-service/docker-compose.yml

# Добавьте после строки "build: .":
    env_file:
      - .env

# Сохраните (Ctrl+O, Enter, Ctrl+X)

# Перезапустите
docker compose down
docker compose up -d
```

### Ошибка: "Что-то пошло не так" от Avito OAuth

**Возможные причины:**

1. **Неправильный Redirect URI**
   ```bash
   # Проверьте .env
   grep REDIRECT_URI /opt/avito-service/.env
   # Должно быть: /api/v1/avito/callback
   ```

2. **Неправильный Client ID/Secret**
   ```bash
   # Проверьте что они совпадают с Avito Developer Panel
   cat /opt/avito-service/.env
   ```

3. **Scopes не разрешены в приложении**
   - Зайдите в Avito Developer Panel
   - Проверьте разрешенные scopes для вашего приложения

### Ошибка: "HTTP 400/401" от Avito API

**Решение:**
```bash
# Проверьте что URLs правильные
grep "AVITO_.*_URL" /opt/avito-service/app/main.py

# Должно быть:
# AVITO_AUTH_URL = "https://avito.ru/oauth"
# AVITO_TOKEN_URL = "https://api.avito.ru/token"
```

### Контейнер не запускается

```bash
# Посмотрите детальные логи
docker compose logs

# Проверьте что все файлы на месте
ls -la /opt/avito-service/app/
ls -la /opt/avito-service/templates/

# Пересоберите с нуля
docker compose down
docker rmi -f avito-service:latest
docker compose build --no-cache
docker compose up -d
```

---

## Полезные команды

### Просмотр логов
```bash
cd /opt/avito-service

# Последние 50 строк
docker compose logs --tail=50

# В реальном времени
docker compose logs -f

# Только ошибки
docker compose logs | grep -i error
```

### Перезапуск сервиса
```bash
cd /opt/avito-service
docker compose restart
```

### Полная пересборка
```bash
cd /opt/avito-service
docker compose down
docker rmi -f avito-service:latest
docker compose build --no-cache
docker compose up -d
```

### Проверка базы данных
```bash
# Подключитесь к SQLite
sqlite3 /opt/avito-service/data/avito.db

# SQL команды:
SELECT * FROM users;
SELECT * FROM profiles;
.quit
```

### Проверка файлов внутри контейнера
```bash
docker exec avito-service ls -la /app/
docker exec avito-service ls -la /app/templates/
docker exec avito-service cat /app/main.py | grep AVITO_TOKEN_URL
```

---

## Обновление Caddy (Если нужно)

Если вы еще не добавили Avito в Caddyfile:

```bash
# Найдите Caddyfile (обычно в /root/lisa/)
find /root -name "Caddyfile" 2>/dev/null

# Откройте его
nano /root/lisa/Caddyfile

# Добавьте в конец:
```

```caddyfile
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
```

Перезапустите Caddy:
```bash
cd /root/lisa
docker compose restart caddy
```

---

## Что было исправлено

### Безопасность (10 CVE)
- ✅ CVE-2024-24762 (FastAPI ReDoS) - HIGH
- ✅ CVE-2024-47874 (Starlette DoS) - HIGH
- ✅ CVE-2025-43859 (h11 Request Smuggling) - CRITICAL
- ✅ CVE-2024-53981 (python-multipart DoS) - HIGH
- ✅ CVE-2024-56201 (Jinja2 RCE) - HIGH
- ✅ CVE-2024-34064 (Jinja2) - MEDIUM
- ✅ CVE-2024-56326 (Jinja2 Sandbox) - HIGH
- ✅ CVE-2024-35195 (requests Cert Bypass) - MEDIUM
- ✅ CVE-2024-47081 (requests Credential Leak) - MEDIUM

### Функциональность
- ✅ Исправлен Token URL: `https://api.avito.ru/token` (было: `/oauth/token`)
- ✅ Исправлен Auth URL: `https://avito.ru/oauth` (было: `https://api.avito.ru/oauth`)
- ✅ Исправлен формат scopes: запятые вместо пробелов
- ✅ Добавлены все необходимые scopes (messenger, items, stats, autoload, user)
- ✅ Улучшена обработка ошибок OAuth

---

## Контакты поддержки

**Avito API Support:**
- Телефон: +7 495 777-10-66
- Email: supportautoload@avito.ru

**Номер профиля:** 3 578 796

---

**Последнее обновление:** 2026-01-13
**Автор:** @ankor1403
