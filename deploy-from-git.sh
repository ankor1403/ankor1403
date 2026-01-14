#!/bin/bash

# Deployment script - run this on root@ixhyswhgny server
# Pulls files from git repository and deploys them

set -e

echo "🚀 Развертывание Avito Messenger из Git"
echo "========================================"
echo ""

# Create temp directory
TEMP_DIR="/tmp/avito-deploy-$(date +%s)"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

echo "1️⃣ Клонирование репозитория..."
git clone http://127.0.0.1:51302/git/ankor1403/ankor1403 .
git checkout claude/audit-dependencies-mkbp0op9n8ha6qpk-Gt2Dm

echo ""
echo "2️⃣ Создание резервной копии..."
cd /opt/avito-service
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r app "$BACKUP_DIR/"
cp -r data "$BACKUP_DIR/" 2>/dev/null || true
echo "✅ Backup создан: $BACKUP_DIR"

echo ""
echo "3️⃣ Копирование новых файлов..."
cp "$TEMP_DIR/avito_api_client.py" app/
cp "$TEMP_DIR/messenger_worker.py" app/
cp "$TEMP_DIR/main_updated.py" app/main.py

echo "✅ Файлы скопированы"

echo ""
echo "4️⃣ Обновление базы данных..."

# Add avito_user_id column
sqlite3 data/avito.db "ALTER TABLE profiles ADD COLUMN avito_user_id TEXT;" 2>/dev/null || echo "  Column avito_user_id already exists"

# Update messages table structure
sqlite3 data/avito.db <<'EOSQL'
-- Add chat_id and author_id if not exists
ALTER TABLE messages ADD COLUMN chat_id TEXT;
ALTER TABLE messages ADD COLUMN author_id TEXT;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_messages_profile_chat ON messages(profile_id, chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_avito_id ON messages(avito_message_id);

-- Create chats table
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    avito_chat_id TEXT NOT NULL,
    item_id TEXT,
    last_message_at TIMESTAMP,
    last_checked_at TIMESTAMP,
    unread_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
    UNIQUE(profile_id, avito_chat_id)
);

CREATE INDEX IF NOT EXISTS idx_chats_profile ON chats(profile_id);
EOSQL

echo "✅ База данных обновлена"

echo ""
echo "5️⃣ Проверка файлов..."
ls -lh app/*.py

echo ""
echo "6️⃣ Перезапуск контейнера..."
docker compose down
docker compose build --no-cache
docker compose up -d

echo ""
echo "7️⃣ Ожидание запуска..."
sleep 10

echo ""
echo "8️⃣ Проверка логов:"
docker compose logs --tail=50

echo ""
echo "✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!"
echo ""
echo "📋 Что делать дальше:"
echo "   1. Перейдите на https://avito.afonin-lisa.ru"
echo "   2. Откройте профиль ID 22"
echo "   3. ПЕРЕАВТОРИЗУЙТЕ профиль (нажмите 'Авторизовать в Avito')"
echo "   4. Включите нужные функции (чекбоксы)"
echo "   5. Настройте автоответчик и N8N webhook"
echo ""
echo "Фоновый воркер автоматически начнёт проверять сообщения!"
echo ""

# Cleanup
rm -rf "$TEMP_DIR"
