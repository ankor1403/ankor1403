#!/bin/bash

# All-in-one installer for Avito Messenger
# Copy this entire script to server and run it

set -e

echo "🚀 Avito Messenger - Установка всех функций"
echo "============================================"
echo ""

cd /opt/avito-service

# Backup
echo "1️⃣ Резервное копирование..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r app "$BACKUP_DIR/"
cp -r data "$BACKUP_DIR/" 2>/dev/null || true
echo "✅ Backup: $BACKUP_DIR"

echo ""
echo "2️⃣ Создание avito_api_client.py..."
cat > app/avito_api_client.py << 'EOFCLIENT'
"""
Avito API Client
Handles all interactions with Avito Messenger API
"""

import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AvitoAPIClient:
    """Client for Avito Messenger API"""

    BASE_URL = "https://api.avito.ru"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    def get_user_info(self) -> Optional[Dict]:
        """Get current user information"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/core/v1/accounts/self",
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get user info: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

    def get_chats(self, user_id: str, unread_only: bool = False, limit: int = 100, offset: int = 0) -> Optional[Dict]:
        """Get list of chats"""
        try:
            params = {"limit": limit, "offset": offset}
            if unread_only:
                params["unread_only"] = "true"

            response = requests.get(
                f"{self.BASE_URL}/messenger/v1/accounts/{user_id}/chats",
                headers=self.headers,
                params=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get chats: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting chats: {e}")
            return None

    def get_messages(self, user_id: str, chat_id: str, limit: int = 100, offset: int = 0) -> Optional[Dict]:
        """Get messages from chat (v2 - does not mark as read)"""
        try:
            params = {"limit": limit, "offset": offset}

            response = requests.get(
                f"{self.BASE_URL}/messenger/v2/accounts/{user_id}/chats/{chat_id}/messages/",
                headers=self.headers,
                params=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get messages: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return None

    def send_message(self, user_id: str, chat_id: str, message_text: str) -> Optional[Dict]:
        """Send message to chat"""
        try:
            payload = {
                "message": {"text": message_text},
                "type": "text"
            }

            response = requests.post(
                f"{self.BASE_URL}/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages",
                headers=self.headers,
                json=payload
            )

            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Failed to send message: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None

    @staticmethod
    def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> Optional[Dict]:
        """Refresh access token using refresh token"""
        try:
            payload = {
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            }

            response = requests.post(
                "https://api.avito.ru/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=payload
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to refresh token: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None
EOFCLIENT

echo "✅ avito_api_client.py создан"

echo ""
echo "3️⃣ Создание messenger_worker.py..."
cat > app/messenger_worker.py << 'EOFWORKER'
"""
Messenger Worker
Background tasks for polling messages, auto-responder, and N8N integration
"""

import asyncio
import logging
import sqlite3
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = "/app/data/avito.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class MessengerWorker:
    """Handles background messaging tasks"""

    def __init__(self):
        self.running = False
        self.poll_interval = 30

    async def start(self):
        """Start background worker"""
        self.running = True
        logger.info("Messenger worker started")

        while self.running:
            try:
                await self.poll_messages()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(self.poll_interval)

    async def stop(self):
        """Stop background worker"""
        self.running = False
        logger.info("Messenger worker stopped")

    async def poll_messages(self):
        """Poll messages for all active profiles"""
        with get_db() as conn:
            profiles = conn.execute("""
                SELECT p.*, u.username
                FROM profiles p
                JOIN users u ON p.user_id = u.id
                WHERE p.access_token IS NOT NULL
                AND p.avito_user_id IS NOT NULL
            """).fetchall()

            for profile in profiles:
                try:
                    await self.poll_profile_messages(dict(profile))
                except Exception as e:
                    logger.error(f"Error polling profile {profile['id']}: {e}")

    async def poll_profile_messages(self, profile: Dict):
        """Poll messages for a single profile"""
        from avito_api_client import AvitoAPIClient

        features = json.loads(profile.get('features', '{}'))
        if not features.get('messenger_read', False):
            return

        # Check token expiration
        if profile['token_expires_at']:
            expires_at = datetime.fromisoformat(profile['token_expires_at'])
            if expires_at < datetime.now() + timedelta(hours=1):
                await self.refresh_profile_token(profile)
                return

        client = AvitoAPIClient(profile['access_token'])
        user_id = profile['avito_user_id']

        chats_response = client.get_chats(user_id, unread_only=True)
        if not chats_response or 'chats' not in chats_response:
            return

        for chat in chats_response.get('chats', []):
            try:
                await self.process_chat(profile, client, chat)
            except Exception as e:
                logger.error(f"Error processing chat {chat.get('id')}: {e}")

    async def process_chat(self, profile: Dict, client, chat: Dict):
        """Process a single chat"""
        user_id = profile['avito_user_id']
        chat_id = chat['id']

        messages_response = client.get_messages(user_id, chat_id, limit=10)
        if not messages_response or 'messages' not in messages_response:
            return

        messages = messages_response['messages']

        for message in messages:
            if message.get('direction') == 'in':
                await self.process_incoming_message(profile, client, chat_id, message)

    async def process_incoming_message(self, profile: Dict, client, chat_id: str, message: Dict):
        """Process a single incoming message"""
        message_id = message['id']
        message_text = message.get('content', {}).get('text', '')
        author_id = message.get('author_id', '')

        with get_db() as conn:
            existing = conn.execute(
                "SELECT id FROM messages WHERE avito_message_id = ? AND profile_id = ?",
                (message_id, profile['id'])
            ).fetchone()

            if existing:
                return

            conn.execute("""
                INSERT INTO messages (profile_id, avito_message_id, chat_id, direction, content, author_id, created_at)
                VALUES (?, ?, ?, 'in', ?, ?, ?)
            """, (profile['id'], message_id, chat_id, message_text, author_id, datetime.now()))
            conn.commit()

        logger.info(f"New message in profile {profile['id']}, chat {chat_id}")

        if profile.get('n8n_webhook'):
            await self.send_to_n8n(profile, chat_id, message)

        features = json.loads(profile.get('features', '{}'))
        if features.get('autoresponder', False) and profile.get('autoresponder_text'):
            await self.send_auto_response(profile, client, chat_id, message_text)

    async def send_to_n8n(self, profile: Dict, chat_id: str, message: Dict):
        """Send message data to N8N webhook"""
        try:
            webhook_url = profile['n8n_webhook']
            payload = {
                "profile_id": profile['id'],
                "profile_name": profile['name'],
                "chat_id": chat_id,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }

            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"Sent to N8N for profile {profile['id']}")
        except Exception as e:
            logger.error(f"Error sending to N8N: {e}")

    async def send_auto_response(self, profile: Dict, client, chat_id: str, incoming_text: str):
        """Send automatic response"""
        autoresponder_config = profile.get('autoresponder_text', '')

        if '|' in autoresponder_config or ':' in autoresponder_config:
            rules = autoresponder_config.split('|')
            for rule in rules:
                if ':' in rule:
                    keyword, response = rule.split(':', 1)
                    if keyword.lower() in incoming_text.lower():
                        await self.send_response(profile, client, chat_id, response)
                        return
        else:
            if autoresponder_config.strip():
                await self.send_response(profile, client, chat_id, autoresponder_config)

    async def send_response(self, profile: Dict, client, chat_id: str, response_text: str):
        """Send a response message"""
        try:
            user_id = profile['avito_user_id']
            result = client.send_message(user_id, chat_id, response_text)

            if result:
                with get_db() as conn:
                    conn.execute("""
                        INSERT INTO messages (profile_id, avito_message_id, chat_id, direction, content, created_at)
                        VALUES (?, ?, ?, 'out', ?, ?)
                    """, (profile['id'], result.get('id', ''), chat_id, response_text, datetime.now()))
                    conn.commit()

                logger.info(f"Auto-response sent in profile {profile['id']}")
        except Exception as e:
            logger.error(f"Error sending response: {e}")

    async def refresh_profile_token(self, profile: Dict):
        """Refresh access token for a profile"""
        from avito_api_client import AvitoAPIClient
        import os

        client_id = os.getenv("AVITO_CLIENT_ID")
        client_secret = os.getenv("AVITO_CLIENT_SECRET")

        if not profile.get('refresh_token'):
            return

        token_data = AvitoAPIClient.refresh_access_token(
            client_id,
            client_secret,
            profile['refresh_token']
        )

        if token_data and 'access_token' in token_data:
            expires_at = datetime.now() + timedelta(seconds=token_data.get('expires_in', 86400))

            with get_db() as conn:
                conn.execute("""
                    UPDATE profiles
                    SET access_token = ?,
                        refresh_token = ?,
                        token_expires_at = ?
                    WHERE id = ?
                """, (
                    token_data['access_token'],
                    token_data.get('refresh_token', profile['refresh_token']),
                    expires_at.isoformat(),
                    profile['id']
                ))
                conn.commit()

            logger.info(f"Token refreshed for profile {profile['id']}")


worker = MessengerWorker()
EOFWORKER

echo "✅ messenger_worker.py создан"

echo ""
echo "4️⃣ Обновление main.py..."
# Just add the imports and startup/shutdown events to existing main.py
# This is safer than replacing the whole file

# Add to the imports section
sed -i '/^from contextlib import contextmanager/a import asyncio\nimport logging' app/main.py

# Add startup event if not exists
if ! grep -q "@app.on_event" app/main.py; then
    cat >> app/main.py << 'EOFSTARTUP'

# Background worker startup/shutdown
@app.on_event("startup")
async def startup_event():
    """Start background worker on app startup"""
    from messenger_worker import worker
    asyncio.create_task(worker.start())
    logger.info("Background worker started")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop background worker on app shutdown"""
    from messenger_worker import worker
    await worker.stop()
    logger.info("Background worker stopped")
EOFSTARTUP
fi

echo "✅ main.py обновлён"

echo ""
echo "5️⃣ Обновление базы данных..."
sqlite3 data/avito.db "ALTER TABLE profiles ADD COLUMN avito_user_id TEXT;" 2>/dev/null || echo "  avito_user_id exists"
sqlite3 data/avito.db "ALTER TABLE messages ADD COLUMN chat_id TEXT;" 2>/dev/null || echo "  chat_id exists"
sqlite3 data/avito.db "ALTER TABLE messages ADD COLUMN author_id TEXT;" 2>/dev/null || echo "  author_id exists"

sqlite3 data/avito.db <<'EOSQL'
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

CREATE INDEX IF NOT EXISTS idx_messages_profile_chat ON messages(profile_id, chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_avito_id ON messages(avito_message_id);
CREATE INDEX IF NOT EXISTS idx_chats_profile ON chats(profile_id);
EOSQL

echo "✅ База данных обновлена"

echo ""
echo "6️⃣ Перезапуск контейнера..."
docker compose down
docker compose build --no-cache
docker compose up -d

echo ""
echo "7️⃣ Ожидание запуска..."
sleep 10

echo ""
echo "8️⃣ Логи:"
docker compose logs --tail=50

echo ""
echo "=========================================="
echo "✅ УСТАНОВКА ЗАВЕРШЕНА!"
echo "=========================================="
echo ""
echo "📋 Что делать дальше:"
echo ""
echo "1. Откройте https://avito.afonin-lisa.ru"
echo "2. Войдите в систему"
echo "3. Откройте профиль (ID 22)"
echo "4. ПЕРЕАВТОРИЗУЙТЕ профиль:"
echo "   - Нажмите 'Авторизовать в Avito'"
echo "   - Подтвердите доступ"
echo "   (это нужно чтобы получить avito_user_id)"
echo ""
echo "5. Включите функции (чекбоксы):"
echo "   ✅ Чтение сообщений"
echo "   ✅ Отправка сообщений"
echo "   ✅ Автоответчик"
echo ""
echo "6. Настройте автоответчик (пример):"
echo "   цена:Цена в объявлении|наличие:Товар в наличии"
echo ""
echo "7. Добавьте N8N webhook (опционально)"
echo ""
echo "Фоновый worker проверяет сообщения каждые 30 сек!"
echo ""
