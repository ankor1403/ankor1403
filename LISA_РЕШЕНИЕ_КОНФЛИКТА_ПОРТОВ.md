# 🔧 РЕШЕНИЕ КОНФЛИКТА ПОРТОВ: LISA + TELEGRAM SERVICE

## 🔥 ПРОБЛЕМА

На сервере **83.222.25.94** запущены:
- **wappi-caddy** → порты 80, 443 (для telegram.afonin-lisa.ru)
- **telegram-multi-service** → порт 8200
- **telegram-service** → порт 8100

**Lisa** тоже хочет использовать **порты 80 и 443** для своего Caddy!

---

## 💡 ВАРИАНТЫ РЕШЕНИЯ

### Вариант 1: ⭐ НОВЫЙ СЕРВЕР (РЕКОМЕНДУЕТСЯ)

**Самое простое и правильное решение.**

✅ **Преимущества:**
- Нет конфликтов
- Независимая работа
- Проще управлять
- Лучше производительность

📦 **Стоимость:** от 200₽/месяц (Timeweb, Beget, REG.RU)

---

### Вариант 2: 🔄 ОДИН CADDY ДЛЯ ВСЕХ СЕРВИСОВ

Использовать **один Caddy** (от Lisa) для проксирования всех сервисов.

**Схема:**
```
Интернет → Caddy (Lisa)
              ├─→ telegram.afonin-lisa.ru → telegram-multi-service:8200
              ├─→ tg.api.afonin-lisa.ru → telegram-service:8100
              ├─→ n8n.ваш-домен.ru → n8n:5678
              └─→ supabase.ваш-домен.ru → supabase-kong:8000
```

#### Пошаговая инструкция:

---

#### ШАГ 1: Остановить старый Caddy

```bash
cd /opt/wappi
docker-compose down
```

⚠️ **ВНИМАНИЕ:** telegram.afonin-lisa.ru временно перестанет работать!

---

#### ШАГ 2: Установить Lisa

```bash
cd ~
git clone https://github.com/shorin-nikita/lisa.git
cd lisa
python3 CTAPT.py
```

Во время установки укажите домены для Lisa.

---

#### ШАГ 3: Получить старый Caddyfile

```bash
# Создать бэкап старой конфигурации Caddy:
docker run --rm -v wappi_caddy_data:/data alpine cat /data/caddy/autosave.json > ~/old_caddy_config.json

# Или посмотреть конфигурацию из старого docker-compose:
cat /opt/wappi/Caddyfile
```

---

#### ШАГ 4: Добавить старые домены в Caddy Lisa

**Найти Caddyfile Lisa:**
```bash
cd ~/lisa
docker exec lisa_caddy_1 cat /etc/caddy/Caddyfile > ~/lisa_caddyfile_backup
```

**Отредактировать:**
```bash
nano ~/lisa_caddyfile_backup
```

**Добавить блоки для Telegram сервисов:**
```caddyfile
# Telegram Multi-Service
telegram.afonin-lisa.ru {
  log {
    output file /var/log/caddy/telegram.log
    format json
  }

  handle /* {
    reverse_proxy telegram-multi-service:8200
  }

  handle /api/* {
    reverse_proxy telegram-service:8100
  }

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

# Старый API
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
```

---

#### ШАГ 5: Подключить Telegram контейнеры к сети Lisa

Узнать имя сети Lisa:
```bash
docker network ls | grep lisa
```

Обычно это `lisa_default`.

Подключить контейнеры:
```bash
docker network connect lisa_default telegram-multi-service
docker network connect lisa_default telegram-service
```

---

#### ШАГ 6: Применить новый Caddyfile

```bash
# Скопировать в контейнер:
docker cp ~/lisa_caddyfile_backup lisa_caddy_1:/etc/caddy/Caddyfile

# Перезагрузить Caddy:
docker exec lisa_caddy_1 caddy reload --config /etc/caddy/Caddyfile
```

---

#### ШАГ 7: Проверить

```bash
# Проверить telegram.afonin-lisa.ru:
curl -I https://telegram.afonin-lisa.ru/

# Проверить tg.api.afonin-lisa.ru:
curl -I https://tg.api.afonin-lisa.ru/

# Проверить Lisa (N8N):
curl -I https://n8n.ваш-домен.ru/
```

---

### Вариант 3: 🔧 ИЗМЕНИТЬ ПОРТЫ LISA

Настроить Lisa на использование других портов (например, 8080, 8443).

**СЛОЖНОСТЬ:** Высокая (нужно править docker-compose.yml Lisa)

#### Пошаговая инструкция:

---

#### ШАГ 1: Установить Lisa БЕЗ доменов

```bash
cd ~
git clone https://github.com/shorin-nikita/lisa.git
cd lisa
python3 CTAPT.py
```

Когда спросит про домены - **оставьте пустым** (доступ по портам).

---

#### ШАГ 2: Изменить порты в docker-compose.yml

```bash
cd ~/lisa
nano docker-compose.yml
```

**Найти секцию Caddy и изменить порты:**
```yaml
caddy:
  ports:
    - "8080:80"    # было "80:80"
    - "8443:443"   # было "443:443"
```

---

#### ШАГ 3: Перезапустить Lisa

```bash
cd ~/lisa
docker-compose down
docker-compose up -d
```

---

#### ШАГ 4: Доступ к сервисам

Теперь Lisa доступна на других портах:
- **N8N:** http://IP:8001
- **Supabase:** http://IP:8005

А Telegram сервисы остаются на портах 80/443.

---

### Вариант 4: 🚫 ОСТАНОВИТЬ TELEGRAM СЕРВИСЫ

**НЕ РЕКОМЕНДУЕТСЯ**, если вам нужен Telegram сервис!

```bash
# Остановить Telegram сервисы:
cd /opt/wappi && docker-compose down
cd /opt/telegram_multi_service && docker-compose down
cd /opt/messengers && docker-compose down

# Установить Lisa:
cd ~
git clone https://github.com/shorin-nikita/lisa.git
cd lisa
python3 CTAPT.py
```

Telegram сервисы будут недоступны.

---

## 📊 СРАВНЕНИЕ ВАРИАНТОВ

| Вариант | Сложность | Время | Стоимость | Рекомендация |
|---------|-----------|-------|-----------|--------------|
| 1. Новый сервер | ⭐ Легко | 10 мин | 200₽/мес | ⭐⭐⭐⭐⭐ |
| 2. Один Caddy | ⚠️ Средне | 30 мин | Бесплатно | ⭐⭐⭐ |
| 3. Другие порты | 🔧 Сложно | 20 мин | Бесплатно | ⭐⭐ |
| 4. Остановить Telegram | ⭐ Легко | 5 мин | Бесплатно | ❌ |

---

## 🎯 МОЯ РЕКОМЕНДАЦИЯ

### Если бюджет позволяет → **Вариант 1** (новый сервер)

✅ **Плюсы:**
- Просто и быстро
- Нет рисков
- Лучшая производительность
- Независимое масштабирование

**Где арендовать:**
- **Timeweb:** от 200₽/мес (промокод CLOUDLITE)
- **Beget:** от 300₽/мес (рекомендует автор Lisa)
- **REG.RU:** от 250₽/мес

---

### Если хотите на одном сервере → **Вариант 2** (один Caddy)

⚠️ **Учтите:**
- Нужно настроить сетевое взаимодействие контейнеров
- Один Caddy управляет всеми доменами
- При падении Caddy все сервисы недоступны

✅ **Плюсы:**
- Бесплатно
- Один SSL/HTTPS для всех
- Единая точка входа

---

### Если хотите минимум изменений → **Вариант 3** (другие порты)

⚠️ **Учтите:**
- Lisa будет доступна БЕЗ HTTPS (только HTTP на 8080)
- Нужно открывать дополнительные порты
- Нет автоматических SSL сертификатов

✅ **Плюсы:**
- Telegram сервисы не трогаются
- Минимум изменений

---

## 🆘 ПОМОЩЬ

Если выбрали **Вариант 2** (один Caddy) и что-то не работает:

### Проблема 1: Telegram контейнеры не видны из Caddy

```bash
# Посмотреть сети контейнера:
docker inspect telegram-multi-service | grep NetworkMode

# Подключить к нужной сети:
docker network connect lisa_default telegram-multi-service
docker network connect lisa_default telegram-service
```

### Проблема 2: Caddy не перезагружает конфигурацию

```bash
# Проверить синтаксис:
docker exec lisa_caddy_1 caddy validate --config /etc/caddy/Caddyfile

# Перезапустить контейнер:
docker restart lisa_caddy_1
```

### Проблема 3: SSL не работает для старых доменов

```bash
# Проверить логи Caddy:
docker logs lisa_caddy_1

# Убедитесь что DNS записи правильные:
nslookup telegram.afonin-lisa.ru
nslookup tg.api.afonin-lisa.ru
```

---

## 📝 ИТОГОВАЯ СХЕМА (Вариант 2 - один Caddy)

```
┌─────────────────────────────────────────────────┐
│              ИНТЕРНЕТ (80, 443)                 │
└─────────────────┬───────────────────────────────┘
                  │
          ┌───────▼────────┐
          │  Caddy (Lisa)  │
          │  порты 80,443  │
          └───────┬────────┘
                  │
       ┌──────────┼──────────┬─────────────┐
       │          │          │             │
       ▼          ▼          ▼             ▼
  telegram    tg.api    n8n.domain   supabase
  .afonin     .afonin   :5678         .domain
  -lisa.ru    -lisa.ru                :8000
       │          │
       ▼          ▼
  telegram-   telegram-
  multi-      service
  service     :8100
  :8200
```

---

## 🎉 ГОТОВО!

Выберите подходящий вариант и действуйте! Если нужна помощь - спрашивайте!

**Лучший выбор:** Новый сервер для Lisa (Вариант 1) 🚀
