# 🚀 УСТАНОВКА LISA С ЕДИНЫМ CADDY ДЛЯ ВСЕХ СЕРВИСОВ

## 📋 ПЛАН ДЕЙСТВИЙ

Мы установим Lisa и настроим один общий Caddy для:
- ✅ Telegram Multi-Service (telegram.afonin-lisa.ru)
- ✅ Старый Telegram Service (tg.api.afonin-lisa.ru)
- ✅ Lisa N8N (n8n.ваш-домен.ru)
- ✅ Lisa Supabase (supabase.ваш-домен.ru)
- ✅ Все будущие сервисы

---

## ⏱️ ВРЕМЯ: ~30 минут

---

## 🎯 ЭТАПЫ:

1. ✅ Создать бэкапы (5 мин)
2. 🛑 Остановить сервисы (2 мин)
3. 🗑️ Удалить старый Caddy (1 мин)
4. 📥 Установить Lisa (10 мин)
5. 🔧 Настроить единый Caddy (10 мин)
6. ✅ Проверить всё (2 мин)

---

# 📂 ЭТАП 1: СОЗДАНИЕ БЭКАПОВ (5 минут)

⚠️ **ВАЖНО!** Сначала сохраним всё, на случай если что-то пойдёт не так.

## Шаг 1.1: Создать директорию для бэкапов

```bash
mkdir -p ~/backups/$(date +%Y%m%d_%H%M%S)
cd ~/backups/$(date +%Y%m%d_%H%M%S)
```

---

## Шаг 1.2: Сохранить конфигурацию старого Caddy

```bash
# Скопировать Caddyfile из контейнера:
docker exec wappi-caddy cat /etc/caddy/Caddyfile > caddy_old_config.txt

# Проверить что сохранилось:
cat caddy_old_config.txt

echo "✓ Конфигурация Caddy сохранена в: $(pwd)/caddy_old_config.txt"
```

---

## Шаг 1.3: Сохранить конфигурации Telegram сервисов

```bash
# Multi-Service:
cp -r /opt/telegram_multi_service /opt/telegram_multi_service.backup

# Старый сервис:
cp -r /opt/messengers /opt/messengers.backup

# Wappi:
cp -r /opt/wappi /opt/wappi.backup

echo "✓ Бэкапы созданы в /opt/*.backup"
```

---

## Шаг 1.4: Сохранить базу данных Telegram

```bash
# Экспорт базы данных:
docker exec telegram-multi-service cat /app/data/multi.db > telegram_multi_db_backup.db 2>/dev/null || echo "База уже сохранена в volume"

echo "✓ Бэкап базы данных создан (если была доступна)"
```

---

## Шаг 1.5: Записать текущие контейнеры

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' > docker_containers_before.txt

cat docker_containers_before.txt

echo "✓ Список контейнеров сохранён"
```

---

# 🛑 ЭТАП 2: ОСТАНОВКА СЕРВИСОВ (2 минуты)

## Шаг 2.1: Остановить Telegram сервисы (НЕ УДАЛЯЕМ!)

```bash
# Остановить Multi-Service:
cd /opt/telegram_multi_service
docker-compose stop
echo "✓ telegram-multi-service остановлен"

# Остановить старый сервис:
cd /opt/messengers
docker-compose stop telegram-service
echo "✓ telegram-service остановлен"
```

⚠️ **Мы НЕ удаляем контейнеры, только останавливаем!**

---

## Шаг 2.2: Остановить и удалить старый Caddy

```bash
cd /opt/wappi
docker-compose down
echo "✓ wappi-caddy удалён"
```

✅ **Старый Caddy удалён, порты 80 и 443 свободны!**

---

## Шаг 2.3: Проверить свободные порты

```bash
# Порты 80 и 443 должны быть свободны:
netstat -tlnp | grep -E ":(80|443)" || echo "✓ Порты 80 и 443 свободны!"
```

Если видите пустой вывод или "свободны" - отлично! Можно продолжать.

---

# 📥 ЭТАП 3: УСТАНОВКА LISA (10 минут)

## Шаг 3.1: Обновить систему

```bash
apt update && apt upgrade -y
```

---

## Шаг 3.2: Проверить наличие необходимых пакетов

```bash
# Проверить:
git --version || apt install -y git
python3 --version || apt install -y python3 python3-pip
docker --version || curl -fsSL https://get.docker.com | sh

echo "✓ Все необходимые пакеты установлены"
```

---

## Шаг 3.3: Скачать Lisa

```bash
cd ~
git clone https://github.com/shorin-nikita/lisa.git
cd lisa
```

---

## Шаг 3.4: Запустить установку Lisa

```bash
python3 CTAPT.py
```

---

## ❓ ОТВЕТЫ НА ВОПРОСЫ СКРИПТА:

Скрипт установки Lisa задаст вам вопросы. Вот что нужно отвечать:

### Вопрос 1: **"Введите домен для N8N (или оставьте пустым)"**

```
n8n.afonin-lisa.ru
```
*(Или ваш домен, если есть другой)*

---

### Вопрос 2: **"Введите домен для Supabase (или оставьте пустым)"**

```
db.afonin-lisa.ru
```
*(Или ваш домен)*

---

### Вопрос 3: **"Введите домен для Ollama (или оставьте пустым)"**

```
ai.afonin-lisa.ru
```
*(Или ваш домен, или оставьте пустым если не нужен)*

---

### Вопрос 4: **"Введите email для Let's Encrypt SSL сертификатов"**

```
admin@afonin-lisa.ru
```
*(Ваш реальный email)*

---

### Вопрос 5: **"Настроить прокси-сервер?"**

```
(Просто нажмите Enter - пропустить)
```

---

⏳ **Ждите 5-10 минут...** Скрипт установит Lisa, настроит firewall, сгенерирует пароли.

---

## Шаг 3.5: Проверить что Lisa установлена

```bash
cd ~/lisa
docker ps | grep -E "(n8n|supabase|ollama|caddy)"
```

Вы должны увидеть контейнеры Lisa (n8n, supabase-kong, postgres, caddy и другие).

---

# 🔧 ЭТАП 4: НАСТРОЙКА ЕДИНОГО CADDY (10 минут)

Сейчас у нас есть Caddy от Lisa. Нужно добавить в него маршруты для Telegram сервисов.

## Шаг 4.1: Запустить Telegram сервисы обратно

```bash
# Запустить Multi-Service:
cd /opt/telegram_multi_service
docker-compose start
echo "✓ telegram-multi-service запущен"

# Запустить старый сервис:
cd /opt/messengers
docker-compose start telegram-service
echo "✓ telegram-service запущен"

# Проверить:
docker ps | grep telegram
```

---

## Шаг 4.2: Найти имя сети Lisa

```bash
docker network ls | grep lisa
```

Вы увидите что-то вроде `lisa_default` или `lisa_edge`. Запомните это имя!

---

## Шаг 4.3: Подключить Telegram контейнеры к сети Lisa

**Замените `lisa_default` на имя сети из предыдущего шага!**

```bash
# Подключить telegram-multi-service:
docker network connect lisa_default telegram-multi-service
echo "✓ telegram-multi-service подключён к сети Lisa"

# Подключить telegram-service:
docker network connect lisa_default telegram-service
echo "✓ telegram-service подключён к сети Lisa"

# Проверить подключение:
docker network inspect lisa_default | grep -E "(telegram-multi-service|telegram-service)"
```

Вы должны увидеть оба контейнера в списке.

---

## Шаг 4.4: Найти имя контейнера Caddy Lisa

```bash
docker ps | grep caddy
```

Вы увидите что-то вроде `lisa_caddy_1` или `lisa-caddy-1`. Запомните!

---

## Шаг 4.5: Получить текущий Caddyfile Lisa

```bash
cd ~/lisa

# Сохранить текущий Caddyfile:
docker exec lisa_caddy_1 cat /etc/caddy/Caddyfile > Caddyfile.original

# Проверить что сохранилось:
cat Caddyfile.original
```

---

## Шаг 4.6: Создать новый Caddyfile с маршрутами для всех сервисов

Скопируйте и выполните этот блок **ЦЕЛИКОМ**:

```bash
cat > ~/lisa/Caddyfile.new << 'CADDYFILE_END'
{
  email admin@afonin-lisa.ru
  # Автоматический HTTPS для всех доменов
}

# ============================================
# TELEGRAM MULTI-SERVICE
# ============================================
telegram.afonin-lisa.ru {
  log {
    output file /var/log/caddy/telegram.log
    format json
  }

  # Основной сервис на корне
  handle /* {
    reverse_proxy telegram-multi-service:8200
  }

  # Старый API на /api/*
  handle /api/* {
    reverse_proxy telegram-service:8100
  }

  # Multi-service на /multi*
  handle_path /multi* {
    reverse_proxy telegram-multi-service:8200
  }

  header {
    Strict-Transport-Security max-age=31536000; includeSubDomains; preload
    X-Content-Type-Options nosniff
    Referrer-Policy strict-origin-when-cross-origin
    -Server
  }
}

# ============================================
# СТАРЫЙ TELEGRAM API
# ============================================
tg.api.afonin-lisa.ru {
  log {
    output file /var/log/caddy/tg-api.log
    format json
  }

  reverse_proxy telegram-service:8100

  header {
    Strict-Transport-Security max-age=31536000; includeSubDomains; preload
    X-Content-Type-Options nosniff
    Referrer-Policy strict-origin-when-cross-origin
    -Server
  }
}

# ============================================
# LISA N8N (АВТОМАТИЗАЦИЯ)
# ============================================
n8n.afonin-lisa.ru {
  log {
    output file /var/log/caddy/n8n.log
    format json
  }

  reverse_proxy n8n:5678

  header {
    Strict-Transport-Security max-age=31536000; includeSubDomains; preload
    X-Content-Type-Options nosniff
    Referrer-Policy strict-origin-when-cross-origin
    -Server
  }
}

# ============================================
# LISA SUPABASE (БАЗА ДАННЫХ)
# ============================================
db.afonin-lisa.ru {
  log {
    output file /var/log/caddy/supabase.log
    format json
  }

  reverse_proxy supabase-kong:8000

  header {
    Strict-Transport-Security max-age=31536000; includeSubDomains; preload
    X-Content-Type-Options nosniff
    Referrer-Policy strict-origin-when-cross-origin
    -Server
  }
}

# ============================================
# LISA OLLAMA (AI МОДЕЛИ) - опционально
# ============================================
ai.afonin-lisa.ru {
  log {
    output file /var/log/caddy/ollama.log
    format json
  }

  reverse_proxy ollama:11434

  header {
    Strict-Transport-Security max-age=31536000; includeSubDomains; preload
    X-Content-Type-Options nosniff
    Referrer-Policy strict-origin-when-cross-origin
    -Server
  }
}

CADDYFILE_END

echo "✓ Новый Caddyfile создан в ~/lisa/Caddyfile.new"
```

---

## Шаг 4.7: Проверить новый Caddyfile

```bash
cat ~/lisa/Caddyfile.new
```

Убедитесь что:
- ✅ Есть блоки для telegram.afonin-lisa.ru
- ✅ Есть блоки для tg.api.afonin-lisa.ru
- ✅ Есть блоки для n8n.afonin-lisa.ru
- ✅ Есть блоки для db.afonin-lisa.ru

---

## Шаг 4.8: Скопировать новый Caddyfile в контейнер

```bash
# Скопировать в контейнер Caddy:
docker cp ~/lisa/Caddyfile.new lisa_caddy_1:/etc/caddy/Caddyfile

echo "✓ Caddyfile скопирован в контейнер"
```

---

## Шаг 4.9: Проверить синтаксис Caddyfile

```bash
docker exec lisa_caddy_1 caddy validate --config /etc/caddy/Caddyfile
```

Если увидели `Valid configuration` - отлично! Если ошибка - покажите мне вывод.

---

## Шаг 4.10: Перезагрузить Caddy

```bash
docker exec lisa_caddy_1 caddy reload --config /etc/caddy/Caddyfile

echo "✓ Caddy перезагружен с новой конфигурацией"
```

---

## Шаг 4.11: Проверить логи Caddy

```bash
docker logs --tail=30 lisa_caddy_1
```

Ищите строки типа:
```
[INFO] certificate obtained successfully
```

Это значит SSL сертификаты получаются.

---

# ✅ ЭТАП 5: ПРОВЕРКА РАБОТОСПОСОБНОСТИ (2 минуты)

## Шаг 5.1: Проверить все контейнеры

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

Должны работать:
- ✅ telegram-multi-service
- ✅ telegram-service
- ✅ lisa_caddy_1 (или похожее имя)
- ✅ n8n
- ✅ supabase контейнеры
- ✅ postgres
- ✅ ollama (если установлен)

---

## Шаг 5.2: Проверить домены изнутри сервера

```bash
echo "=== Проверка доменов ==="

# Telegram Multi-Service:
echo "1. Telegram Multi-Service:"
curl -I https://telegram.afonin-lisa.ru/ 2>&1 | head -5

# Старый Telegram API:
echo "2. Telegram API:"
curl -I https://tg.api.afonin-lisa.ru/ 2>&1 | head -5

# N8N:
echo "3. N8N:"
curl -I https://n8n.afonin-lisa.ru/ 2>&1 | head -5

# Supabase:
echo "4. Supabase:"
curl -I https://db.afonin-lisa.ru/ 2>&1 | head -5

echo "=== Проверка завершена ==="
```

Вы должны увидеть `HTTP/2 200` или `HTTP/2 303` для каждого домена.

---

## Шаг 5.3: Проверить DNS записи

```bash
echo "=== Проверка DNS ==="
nslookup telegram.afonin-lisa.ru
nslookup tg.api.afonin-lisa.ru
nslookup n8n.afonin-lisa.ru
nslookup db.afonin-lisa.ru
echo "=== DNS проверка завершена ==="
```

Все домены должны указывать на **83.222.25.94**.

⚠️ **Если DNS не настроены:** вам нужно создать A-записи в панели управления доменом:
```
n8n.afonin-lisa.ru    → A → 83.222.25.94
db.afonin-lisa.ru     → A → 83.222.25.94
ai.afonin-lisa.ru     → A → 83.222.25.94
```

---

## Шаг 5.4: Открыть в браузере

Откройте в браузере (на вашем компьютере):

- ✅ **Telegram Multi-Service:** https://telegram.afonin-lisa.ru/
- ✅ **Telegram API:** https://tg.api.afonin-lisa.ru/
- ✅ **N8N (автоматизация):** https://n8n.afonin-lisa.ru/
- ✅ **Supabase (БД):** https://db.afonin-lisa.ru/

Всё должно открываться с **зелёным замочком** (HTTPS)!

---

# 🎉 ГОТОВО!

## ✅ ЧТО СДЕЛАНО:

- ✅ Создали бэкапы всех конфигураций
- ✅ Остановили Telegram сервисы (временно)
- ✅ Удалили старый Caddy
- ✅ Установили Lisa
- ✅ Настроили единый Caddy для всех сервисов
- ✅ Подключили Telegram к сети Lisa
- ✅ Проверили работу всех сервисов

---

## 🌐 ДОСТУП К СЕРВИСАМ:

### Telegram:
- **Multi-Service:** https://telegram.afonin-lisa.ru/
- **Old API:** https://tg.api.afonin-lisa.ru/

### Lisa:
- **N8N (автоматизация):** https://n8n.afonin-lisa.ru/
- **Supabase (БД):** https://db.afonin-lisa.ru/
- **Ollama (AI):** https://ai.afonin-lisa.ru/

---

## 🔐 ПАРОЛИ LISA:

```bash
cd ~/lisa
cat .env | grep -E "(PASSWORD|SECRET|JWT)"
```

Сохраните эти пароли! Они понадобятся для входа в N8N и Supabase.

---

## 📊 УПРАВЛЕНИЕ СЕРВИСАМИ:

### Посмотреть все контейнеры:
```bash
docker ps
```

### Перезапустить все:
```bash
cd ~/lisa && docker-compose restart
cd /opt/telegram_multi_service && docker-compose restart
cd /opt/messengers && docker-compose restart telegram-service
```

### Логи:
```bash
# Caddy:
docker logs -f lisa_caddy_1

# Telegram:
docker logs -f telegram-multi-service

# N8N:
docker logs -f n8n

# Все сразу:
docker logs -f $(docker ps -q)
```

---

## 🆘 ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ:

### Проблема 1: Домены не открываются

**Проверьте DNS:**
```bash
nslookup n8n.afonin-lisa.ru
```

Если IP неправильный - настройте A-записи в панели домена.

---

### Проблема 2: "Connection refused"

**Проверьте что контейнеры запущены:**
```bash
docker ps | grep -E "(telegram|caddy|n8n)"
```

**Перезапустите:**
```bash
docker restart telegram-multi-service telegram-service lisa_caddy_1
```

---

### Проблема 3: SSL не работает (нет зелёного замочка)

**Проверьте логи Caddy:**
```bash
docker logs --tail=50 lisa_caddy_1 | grep -i error
```

**Перезагрузите Caddy:**
```bash
docker exec lisa_caddy_1 caddy reload --config /etc/caddy/Caddyfile
```

---

### Проблема 4: Telegram сервис не отвечает

**Проверьте подключение к сети:**
```bash
docker network inspect lisa_default | grep telegram
```

**Если нет в списке - подключите заново:**
```bash
docker network connect lisa_default telegram-multi-service
docker network connect lisa_default telegram-service
```

---

## 🔄 КАК ДОБАВИТЬ НОВЫЙ СЕРВИС В БУДУЩЕМ:

1. **Запустите новый сервис** в Docker
2. **Подключите к сети Lisa:**
   ```bash
   docker network connect lisa_default ИМЯ_КОНТЕЙНЕРА
   ```
3. **Добавьте блок в Caddyfile:**
   ```bash
   docker exec lisa_caddy_1 nano /etc/caddy/Caddyfile
   ```
   Добавьте:
   ```caddyfile
   новый-домен.afonin-lisa.ru {
     reverse_proxy ИМЯ_КОНТЕЙНЕРА:ПОРТ
   }
   ```
4. **Перезагрузите Caddy:**
   ```bash
   docker exec lisa_caddy_1 caddy reload --config /etc/caddy/Caddyfile
   ```

---

## 💾 ВОССТАНОВЛЕНИЕ ИЗ БЭКАПА (если что-то пошло не так):

```bash
# Остановить всё:
cd ~/lisa && docker-compose down
cd /opt/telegram_multi_service && docker-compose down
cd /opt/messengers && docker-compose down

# Восстановить конфигурации:
rm -rf /opt/telegram_multi_service
rm -rf /opt/messengers
rm -rf /opt/wappi

cp -r /opt/telegram_multi_service.backup /opt/telegram_multi_service
cp -r /opt/messengers.backup /opt/messengers
cp -r /opt/wappi.backup /opt/wappi

# Запустить старые сервисы:
cd /opt/wappi && docker-compose up -d
cd /opt/telegram_multi_service && docker-compose up -d
cd /opt/messengers && docker-compose up -d
```

---

## 🎓 ДАЛЬНЕЙШИЕ ШАГИ:

### 1. Настройте N8N:
- Откройте https://n8n.afonin-lisa.ru/
- Создайте администратора
- Импортируйте готовые workflows из `~/lisa/n8n/backup/workflows/`

### 2. Скачайте AI модели в Ollama:
```bash
docker exec -it ollama bash
ollama pull llama3.1
ollama pull mistral
ollama list
exit
```

### 3. Настройте Supabase:
- Откройте https://db.afonin-lisa.ru/
- Войдите с паролем из `.env`
- Создайте базы данных и таблицы

---

## 📚 ПОЛЕЗНЫЕ ССЫЛКИ:

- 📺 **Видео Lisa:** https://youtu.be/vEwYIoZAFOY
- 📖 **GitHub Lisa:** https://github.com/shorin-nikita/lisa
- 📘 **Caddy документация:** https://caddyserver.com/docs/
- 🤖 **N8N документация:** https://docs.n8n.io/

---

## 💡 СОВЕТЫ:

1. **Делайте бэкапы регулярно:**
   ```bash
   docker exec telegram-multi-service cat /app/data/multi.db > ~/backup_$(date +%Y%m%d).db
   docker exec lisa_caddy_1 cat /etc/caddy/Caddyfile > ~/Caddyfile_backup_$(date +%Y%m%d)
   ```

2. **Мониторьте логи:**
   ```bash
   docker logs -f --tail=100 lisa_caddy_1
   ```

3. **Обновляйте регулярно:**
   ```bash
   cd ~/lisa
   python3 O6HOBA.py
   ```

---

**🎉 ПОЗДРАВЛЯЮ! У ВАС ТЕПЕРЬ ЕДИНАЯ ИНФРАСТРУКТУРА С LISA И TELEGRAM!** 🚀

Если возникнут вопросы - спрашивайте! 😊
