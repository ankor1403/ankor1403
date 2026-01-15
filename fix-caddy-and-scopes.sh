#!/bin/bash

# Полный скрипт исправления Caddy и OAuth scopes
# Запускать на сервере root@ixhyswhgny

set -e

echo "🔧 ПОЛНОЕ ИСПРАВЛЕНИЕ CADDY И AVITO SERVICE"
echo "============================================="
echo ""

# 1. ИСПРАВЛЕНИЕ CADDYFILE
echo "1️⃣ Исправление Caddyfile..."

CADDYFILE="/root/lisa/Caddyfile"

# Создаем бэкап
cp "$CADDYFILE" "$CADDYFILE.backup.$(date +%Y%m%d_%H%M%S)"

# Проверяем есть ли уже avito.afonin-lisa.ru
if grep -q "avito.afonin-lisa.ru" "$CADDYFILE"; then
    echo "   avito.afonin-lisa.ru уже есть в конфиге"
else
    echo "   Добавляем avito.afonin-lisa.ru..."
    # Добавляем конфиг для avito перед последним блоком
    cat >> "$CADDYFILE" << 'AVITO_BLOCK'

# ============================================
# AVITO SERVICE
# ============================================
avito.afonin-lisa.ru {
    reverse_proxy localhost:8300

    log {
        output file /var/log/caddy/avito.log
        format json
    }
}
AVITO_BLOCK
fi

# Исправляем проблему с log на строке ~101
# Проблема: директива log вне блока сайта
# Ищем и исправляем структуру

echo "   Проверяем синтаксис Caddyfile..."

# Временный фикс - закомментируем проблемный блок log если он вне сайта
# Сначала проверим структуру
python3 << 'PYTHON_FIX'
import re

with open('/root/lisa/Caddyfile', 'r') as f:
    content = f.read()

lines = content.split('\n')
fixed_lines = []
in_site_block = 0
i = 0

while i < len(lines):
    line = lines[i]
    stripped = line.strip()

    # Подсчет открытых/закрытых скобок
    in_site_block += line.count('{') - line.count('}')

    # Если log { вне блока сайта (in_site_block == 0) и это начало блока
    if stripped.startswith('log {') and in_site_block == 1:
        # Это log внутри блока - OK
        fixed_lines.append(line)
    elif stripped == 'log {' and in_site_block == 0:
        # log вне блока - комментируем весь блок
        fixed_lines.append('# COMMENTED OUT - was outside site block')
        fixed_lines.append('# ' + line)
        i += 1
        brace_count = 1
        while i < len(lines) and brace_count > 0:
            brace_count += lines[i].count('{') - lines[i].count('}')
            fixed_lines.append('# ' + lines[i])
            i += 1
        i -= 1  # Компенсация за цикл while
    else:
        fixed_lines.append(line)

    i += 1

with open('/root/lisa/Caddyfile', 'w') as f:
    f.write('\n'.join(fixed_lines))

print("   Caddyfile исправлен")
PYTHON_FIX

echo ""

# 2. ИСПРАВЛЕНИЕ OAUTH SCOPES
echo "2️⃣ Исправление OAuth scopes в Avito Service..."

MAIN_PY="/opt/avito-service/app/main.py"

# Создаем бэкап
cp "$MAIN_PY" "$MAIN_PY.backup.$(date +%Y%m%d_%H%M%S)"

# Правильные scopes
CORRECT_SCOPES="messenger:read,messenger:write,items:info,items:apply_vas,stats:read,autoload:reports,user:read,user_balance:read,user_operations:read"

# Исправляем ALL_SCOPES
sed -i "s/^ALL_SCOPES = .*/ALL_SCOPES = \"$CORRECT_SCOPES\"/" "$MAIN_PY"

echo "   Проверка scopes:"
grep "ALL_SCOPES" "$MAIN_PY"

echo ""

# 3. ПЕРЕЗАПУСК СЕРВИСОВ
echo "3️⃣ Перезапуск сервисов..."

# Перезапуск Avito Service
echo "   Перезапуск avito-service..."
cd /opt/avito-service
docker compose down 2>/dev/null || true
docker compose up -d --build

# Перезапуск Caddy
echo "   Перезапуск Caddy..."
cd /root/lisa
docker compose restart caddy 2>/dev/null || docker restart caddy

echo ""

# 4. ПРОВЕРКА
echo "4️⃣ Проверка статуса..."
sleep 3

echo "   Docker containers:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "avito|caddy"

echo ""
echo "   Логи Caddy:"
docker logs caddy 2>&1 | tail -10

echo ""
echo "   Логи avito-service:"
docker logs avito-service 2>&1 | tail -5

echo ""
echo "============================================="
echo "✅ ГОТОВО!"
echo ""
echo "Проверьте сайт: https://avito.afonin-lisa.ru"
echo "⚠️  ВАЖНО: Откройте в РЕЖИМЕ ИНКОГНИТО (Ctrl+Shift+N)"
echo "============================================="
