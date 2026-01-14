#!/bin/bash

# Deployment script for Avito Messenger features
# Run this script on root@ixhyswhgny server

set -e

echo "🚀 Развертывание функций мессенджера Avito"
echo "=========================================="
echo ""

cd /opt/avito-service

# Step 1: Backup current version
echo "1️⃣ Создание резервной копии..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r app "$BACKUP_DIR/"
cp -r data "$BACKUP_DIR/" 2>/dev/null || true
echo "✅ Backup создан в $BACKUP_DIR"
echo ""

# Step 2: Copy new files (assuming they're uploaded to /tmp/)
echo "2️⃣ Копирование новых файлов..."

# Check if files exist in /tmp/
if [ ! -f "/tmp/avito_api_client.py" ]; then
    echo "❌ Файлы не найдены в /tmp/"
    echo "Пожалуйста, скопируйте файлы на сервер:"
    echo ""
    echo "  scp /home/user/ankor1403/avito_api_client.py root@ixhyswhgny:/tmp/"
    echo "  scp /home/user/ankor1403/messenger_worker.py root@ixhyswhgny:/tmp/"
    echo "  scp /home/user/ankor1403/main_updated.py root@ixhyswhgny:/tmp/"
    echo ""
    exit 1
fi

# Copy files
cp /tmp/avito_api_client.py app/
cp /tmp/messenger_worker.py app/
cp /tmp/main_updated.py app/main.py

echo "✅ Файлы скопированы"
echo ""

# Step 3: Update database schema
echo "3️⃣ Обновление схемы базы данных..."
sqlite3 data/avito.db <<EOF
-- Add avito_user_id column if not exists
PRAGMA table_info(profiles);
.exit
EOF

# Add column manually if needed
sqlite3 data/avito.db "ALTER TABLE profiles ADD COLUMN avito_user_id TEXT;" 2>/dev/null || echo "Column avito_user_id already exists"

# Update messages table
sqlite3 data/avito.db <<EOF
-- Check if chat_id column exists
PRAGMA table_info(messages);

-- Create new messages table structure
CREATE TABLE IF NOT EXISTS messages_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    avito_message_id TEXT,
    chat_id TEXT,
    direction TEXT NOT NULL CHECK(direction IN ('in', 'out')),
    content TEXT,
    author_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

-- Copy existing data
INSERT OR IGNORE INTO messages_new (id, profile_id, avito_message_id, direction, content, created_at)
SELECT id, profile_id, avito_message_id, direction, content, created_at
FROM messages;

-- Drop old table and rename
DROP TABLE IF EXISTS messages_old;
ALTER TABLE messages RENAME TO messages_old;
ALTER TABLE messages_new RENAME TO messages;

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

.exit
EOF

echo "✅ База данных обновлена"
echo ""

# Step 4: Verify files
echo "4️⃣ Проверка файлов..."
ls -lh app/*.py
echo ""

# Step 5: Rebuild and restart container
echo "5️⃣ Перезапуск контейнера..."
docker compose down
docker compose build --no-cache
docker compose up -d

echo ""
echo "6️⃣ Ожидание запуска (10 секунд)..."
sleep 10

# Step 6: Check logs
echo ""
echo "7️⃣ Проверка логов:"
docker compose logs --tail=40

echo ""
echo "✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!"
echo ""
echo "📋 Добавленные функции:"
echo "   ✅ Чтение сообщений из Avito (фоновая задача каждые 30 сек)"
echo "   ✅ Отправка сообщений через API"
echo "   ✅ Автоответчик на ключевые слова"
echo "   ✅ Интеграция с N8N webhooks"
echo "   ✅ Автоматическое обновление токенов"
echo "   ✅ API endpoints для управления чатами"
echo ""
echo "🔗 Новые API endpoints:"
echo "   GET  /api/profile/{id}/chats - получить список чатов"
echo "   GET  /api/profile/{id}/chat/{chat_id}/messages - получить сообщения"
echo "   POST /api/profile/{id}/chat/{chat_id}/send - отправить сообщение"
echo ""
echo "⚙️  Настройте в профиле:"
echo "   1. Включите нужные функции (чекбоксы)"
echo "   2. Настройте автоответчик (формат: ключ1:ответ1|ключ2:ответ2)"
echo "   3. Добавьте N8N webhook URL для получения уведомлений"
echo ""
