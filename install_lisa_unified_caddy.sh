#!/bin/bash
###############################################################################
# АВТОМАТИЧЕСКАЯ УСТАНОВКА LISA С ЕДИНЫМ CADDY
###############################################################################
# Этот скрипт:
# 1. Создаёт бэкапы
# 2. Останавливает сервисы
# 3. Удаляет старый Caddy
# 4. Устанавливает Lisa
# 5. Настраивает единый Caddy для всех сервисов
###############################################################################

set -e  # Остановка при ошибке

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  УСТАНОВКА LISA С ЕДИНЫМ CADDY ДЛЯ ВСЕХ СЕРВИСОВ            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Проверка что запущено от root
if [ "$EUID" -ne 0 ]; then
    print_error "Запустите скрипт от root: sudo bash $0"
    exit 1
fi

print_warning "ВНИМАНИЕ! Этот скрипт:"
print_warning "  • Остановит Telegram сервисы"
print_warning "  • Удалит старый Caddy"
print_warning "  • Установит Lisa"
print_warning "  • Настроит единый Caddy"
echo ""
read -p "Продолжить? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[YyДд]$ ]]; then
    print_info "Установка отменена"
    exit 0
fi

# ============================================================================
# ЭТАП 1: СОЗДАНИЕ БЭКАПОВ
# ============================================================================

print_info "═══════════════════════════════════════════════════════"
print_info "  ЭТАП 1: СОЗДАНИЕ БЭКАПОВ"
print_info "═══════════════════════════════════════════════════════"
echo ""

BACKUP_DIR=~/backups/$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
cd "$BACKUP_DIR"
print_status "Создана директория бэкапов: $BACKUP_DIR"

# Бэкап Caddy конфигурации
if docker ps | grep -q wappi-caddy; then
    docker exec wappi-caddy cat /etc/caddy/Caddyfile > caddy_old_config.txt 2>/dev/null && \
    print_status "Конфигурация Caddy сохранена" || \
    print_warning "Не удалось сохранить конфигурацию Caddy"
fi

# Бэкап директорий
for dir in /opt/telegram_multi_service /opt/messengers /opt/wappi; do
    if [ -d "$dir" ]; then
        cp -r "$dir" "${dir}.backup" 2>/dev/null && \
        print_status "Бэкап $dir создан" || \
        print_warning "Не удалось создать бэкап $dir"
    fi
done

# Список контейнеров
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' > docker_containers_before.txt
print_status "Список контейнеров сохранён"
echo ""

# ============================================================================
# ЭТАП 2: ОСТАНОВКА СЕРВИСОВ
# ============================================================================

print_info "═══════════════════════════════════════════════════════"
print_info "  ЭТАП 2: ОСТАНОВКА СЕРВИСОВ"
print_info "═══════════════════════════════════════════════════════"
echo ""

# Остановить Telegram сервисы (не удалять!)
if [ -d "/opt/telegram_multi_service" ]; then
    cd /opt/telegram_multi_service
    docker-compose stop && print_status "telegram-multi-service остановлен"
fi

if [ -d "/opt/messengers" ]; then
    cd /opt/messengers
    docker-compose stop telegram-service 2>/dev/null && print_status "telegram-service остановлен"
fi

# Удалить старый Caddy
if [ -d "/opt/wappi" ]; then
    cd /opt/wappi
    docker-compose down && print_status "wappi-caddy удалён"
fi

# Проверка портов
print_info "Проверка свободных портов..."
if netstat -tlnp | grep -E ":(80|443)" > /dev/null 2>&1; then
    print_warning "Порты 80 и 443 всё ещё заняты!"
    netstat -tlnp | grep -E ":(80|443)"
else
    print_status "Порты 80 и 443 свободны!"
fi
echo ""

# ============================================================================
# ЭТАП 3: УСТАНОВКА LISA
# ============================================================================

print_info "═══════════════════════════════════════════════════════"
print_info "  ЭТАП 3: УСТАНОВКА LISA"
print_info "═══════════════════════════════════════════════════════"
echo ""

# Проверка зависимостей
print_info "Проверка зависимостей..."
apt update > /dev/null 2>&1

for cmd in git python3 docker; do
    if ! command -v $cmd &> /dev/null; then
        print_warning "$cmd не установлен, устанавливаю..."
        case $cmd in
            git) apt install -y git ;;
            python3) apt install -y python3 python3-pip ;;
            docker) curl -fsSL https://get.docker.com | sh ;;
        esac
    else
        print_status "$cmd установлен"
    fi
done
echo ""

# Скачать Lisa
print_info "Скачивание Lisa..."
cd ~
if [ -d "lisa" ]; then
    print_warning "Директория ~/lisa уже существует"
    read -p "Удалить и скачать заново? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[YyДд]$ ]]; then
        rm -rf lisa
        git clone https://github.com/shorin-nikita/lisa.git
        print_status "Lisa скачана заново"
    else
        print_info "Используется существующая директория"
    fi
else
    git clone https://github.com/shorin-nikita/lisa.git
    print_status "Lisa скачана"
fi

cd ~/lisa
echo ""

# Запуск установки Lisa
print_warning "═══════════════════════════════════════════════════════"
print_warning "  СЕЙЧАС ЗАПУСТИТСЯ УСТАНОВЩИК LISA"
print_warning "═══════════════════════════════════════════════════════"
echo ""
print_info "Вам нужно будет ответить на вопросы:"
echo "  1. Домен для N8N: n8n.afonin-lisa.ru (или ваш)"
echo "  2. Домен для Supabase: db.afonin-lisa.ru (или ваш)"
echo "  3. Домен для Ollama: ai.afonin-lisa.ru (или пустое)"
echo "  4. Email для SSL: admin@afonin-lisa.ru"
echo "  5. Прокси: просто Enter (пропустить)"
echo ""
read -p "Нажмите Enter чтобы продолжить..." dummy

python3 CTAPT.py

# Проверка установки
print_info "Проверка установки Lisa..."
if docker ps | grep -q "n8n"; then
    print_status "Lisa установлена успешно!"
else
    print_error "Lisa не установлена! Проверьте ошибки выше."
    exit 1
fi
echo ""

# ============================================================================
# ЭТАП 4: НАСТРОЙКА ЕДИНОГО CADDY
# ============================================================================

print_info "═══════════════════════════════════════════════════════"
print_info "  ЭТАП 4: НАСТРОЙКА ЕДИНОГО CADDY"
print_info "═══════════════════════════════════════════════════════"
echo ""

# Запустить Telegram сервисы
print_info "Запуск Telegram сервисов..."
cd /opt/telegram_multi_service && docker-compose start && print_status "telegram-multi-service запущен"
cd /opt/messengers && docker-compose start telegram-service && print_status "telegram-service запущен"
echo ""

# Найти имя сети Lisa
print_info "Поиск сети Lisa..."
LISA_NETWORK=$(docker network ls | grep lisa | head -1 | awk '{print $2}')
if [ -z "$LISA_NETWORK" ]; then
    print_error "Сеть Lisa не найдена!"
    exit 1
fi
print_status "Сеть Lisa: $LISA_NETWORK"

# Подключить Telegram к сети Lisa
print_info "Подключение Telegram к сети Lisa..."
docker network connect "$LISA_NETWORK" telegram-multi-service 2>/dev/null && \
    print_status "telegram-multi-service подключён" || \
    print_warning "telegram-multi-service уже подключён"

docker network connect "$LISA_NETWORK" telegram-service 2>/dev/null && \
    print_status "telegram-service подключён" || \
    print_warning "telegram-service уже подключён"
echo ""

# Найти контейнер Caddy
print_info "Поиск контейнера Caddy..."
CADDY_CONTAINER=$(docker ps | grep caddy | grep lisa | head -1 | awk '{print $NF}')
if [ -z "$CADDY_CONTAINER" ]; then
    print_error "Контейнер Caddy не найден!"
    exit 1
fi
print_status "Контейнер Caddy: $CADDY_CONTAINER"
echo ""

# Создать новый Caddyfile
print_info "Создание нового Caddyfile..."
cat > ~/lisa/Caddyfile.new << 'CADDYFILE_END'
{
  email admin@afonin-lisa.ru
}

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
    Strict-Transport-Security max-age=31536000
    X-Content-Type-Options nosniff
    Referrer-Policy strict-origin-when-cross-origin
    -Server
  }
}

# Старый Telegram API
tg.api.afonin-lisa.ru {
  log {
    output file /var/log/caddy/tg-api.log
    format json
  }
  reverse_proxy telegram-service:8100
  header {
    Strict-Transport-Security max-age=31536000
    X-Content-Type-Options nosniff
    -Server
  }
}

# Lisa N8N
n8n.afonin-lisa.ru {
  log {
    output file /var/log/caddy/n8n.log
    format json
  }
  reverse_proxy n8n:5678
}

# Lisa Supabase
db.afonin-lisa.ru {
  log {
    output file /var/log/caddy/supabase.log
    format json
  }
  reverse_proxy supabase-kong:8000
}

# Lisa Ollama (опционально)
ai.afonin-lisa.ru {
  log {
    output file /var/log/caddy/ollama.log
    format json
  }
  reverse_proxy ollama:11434
}
CADDYFILE_END

print_status "Caddyfile создан"

# Скопировать в контейнер
docker cp ~/lisa/Caddyfile.new "$CADDY_CONTAINER":/etc/caddy/Caddyfile
print_status "Caddyfile скопирован в контейнер"

# Проверить синтаксис
print_info "Проверка синтаксиса Caddyfile..."
if docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile; then
    print_status "Синтаксис Caddyfile корректен"
else
    print_error "Ошибка в Caddyfile! Проверьте конфигурацию."
    exit 1
fi

# Перезагрузить Caddy
print_info "Перезагрузка Caddy..."
docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile
print_status "Caddy перезагружен"
echo ""

# ============================================================================
# ЭТАП 5: ПРОВЕРКА
# ============================================================================

print_info "═══════════════════════════════════════════════════════"
print_info "  ЭТАП 5: ПРОВЕРКА РАБОТОСПОСОБНОСТИ"
print_info "═══════════════════════════════════════════════════════"
echo ""

# Список контейнеров
print_info "Активные контейнеры:"
docker ps --format 'table {{.Names}}\t{{.Status}}'
echo ""

# Проверка доменов
print_info "Проверка доменов (подождите 10 секунд для инициализации SSL)..."
sleep 10

for domain in telegram.afonin-lisa.ru tg.api.afonin-lisa.ru n8n.afonin-lisa.ru db.afonin-lisa.ru; do
    echo -n "  $domain: "
    if curl -s -I --max-time 5 "https://$domain/" 2>&1 | grep -q "HTTP"; then
        print_status "OK"
    else
        print_warning "Не отвечает (возможно, DNS не настроен)"
    fi
done
echo ""

# ============================================================================
# ЗАВЕРШЕНИЕ
# ============================================================================

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                  УСТАНОВКА ЗАВЕРШЕНА!                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

print_status "Все сервисы настроены и запущены!"
echo ""

print_info "ДОСТУП К СЕРВИСАМ:"
echo "  • Telegram Multi: https://telegram.afonin-lisa.ru/"
echo "  • Telegram API:   https://tg.api.afonin-lisa.ru/"
echo "  • N8N:            https://n8n.afonin-lisa.ru/"
echo "  • Supabase:       https://db.afonin-lisa.ru/"
echo "  • Ollama AI:      https://ai.afonin-lisa.ru/"
echo ""

print_info "ПАРОЛИ LISA:"
echo "  cd ~/lisa && cat .env | grep -E '(PASSWORD|SECRET)'"
echo ""

print_info "БЭКАПЫ СОХРАНЕНЫ В:"
echo "  $BACKUP_DIR"
echo ""

print_warning "НЕ ЗАБУДЬТЕ НАСТРОИТЬ DNS A-ЗАПИСИ:"
echo "  n8n.afonin-lisa.ru  → 83.222.25.94"
echo "  db.afonin-lisa.ru   → 83.222.25.94"
echo "  ai.afonin-lisa.ru   → 83.222.25.94"
echo ""

print_info "Подробная инструкция: LISA_УСТАНОВКА_ОДИН_CADDY.md"
echo ""
print_status "Готово! 🎉"
