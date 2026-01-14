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
from typing import Dict, List, Optional
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
        self.poll_interval = 30  # seconds between polls

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
            # Get all profiles with valid tokens and messenger_read enabled
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

        # Check if messenger_read is enabled
        features = json.loads(profile.get('features', '{}'))
        if not features.get('messenger_read', False):
            return

        # Check if token needs refresh
        if profile['token_expires_at']:
            expires_at = datetime.fromisoformat(profile['token_expires_at'])
            if expires_at < datetime.now() + timedelta(hours=1):
                # Token expires soon, refresh it
                await self.refresh_profile_token(profile)
                return  # Refresh updates profile, will poll next time

        client = AvitoAPIClient(profile['access_token'])
        user_id = profile['avito_user_id']

        # Get all chats
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

        # Get messages (v2 to avoid auto-marking as read)
        messages_response = client.get_messages_v2(user_id, chat_id, limit=10)
        if not messages_response or 'messages' not in messages_response:
            return

        messages = messages_response['messages']

        # Process new messages
        for message in messages:
            if message.get('direction') == 'in':  # Incoming message
                await self.process_incoming_message(profile, client, chat_id, message)

    async def process_incoming_message(self, profile: Dict, client, chat_id: str, message: Dict):
        """Process a single incoming message"""
        message_id = message['id']
        message_text = message.get('content', {}).get('text', '')
        author_id = message.get('author_id', '')

        # Check if message already processed
        with get_db() as conn:
            existing = conn.execute(
                "SELECT id FROM messages WHERE avito_message_id = ? AND profile_id = ?",
                (message_id, profile['id'])
            ).fetchone()

            if existing:
                return  # Already processed

            # Save message to database
            conn.execute("""
                INSERT INTO messages (profile_id, avito_message_id, chat_id, direction, content, author_id, created_at)
                VALUES (?, ?, ?, 'in', ?, ?, ?)
            """, (profile['id'], message_id, chat_id, message_text, author_id, datetime.now()))
            conn.commit()

        logger.info(f"New message in profile {profile['id']}, chat {chat_id}: {message_text[:50]}")

        # Send to N8N webhook if configured
        if profile.get('n8n_webhook'):
            await self.send_to_n8n(profile, chat_id, message)

        # Check autoresponder
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
                logger.info(f"Sent message to N8N webhook for profile {profile['id']}")
            else:
                logger.error(f"N8N webhook returned {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending to N8N: {e}")

    async def send_auto_response(self, profile: Dict, client, chat_id: str, incoming_text: str):
        """Send automatic response based on keywords"""
        autoresponder_config = profile.get('autoresponder_text', '')

        # Simple keyword-based autoresponder
        # Format: keyword1:response1|keyword2:response2
        # Or just a default response if no keywords
        if '|' in autoresponder_config or ':' in autoresponder_config:
            # Keyword-based
            rules = autoresponder_config.split('|')
            for rule in rules:
                if ':' in rule:
                    keyword, response = rule.split(':', 1)
                    if keyword.lower() in incoming_text.lower():
                        await self.send_response(profile, client, chat_id, response)
                        return
        else:
            # Default response for all messages
            if autoresponder_config.strip():
                await self.send_response(profile, client, chat_id, autoresponder_config)

    async def send_response(self, profile: Dict, client, chat_id: str, response_text: str):
        """Send a response message"""
        try:
            user_id = profile['avito_user_id']
            result = client.send_message(user_id, chat_id, response_text)

            if result:
                # Save sent message to database
                with get_db() as conn:
                    conn.execute("""
                        INSERT INTO messages (profile_id, avito_message_id, chat_id, direction, content, created_at)
                        VALUES (?, ?, ?, 'out', ?, ?)
                    """, (profile['id'], result.get('id', ''), chat_id, response_text, datetime.now()))
                    conn.commit()

                logger.info(f"Auto-response sent in profile {profile['id']}, chat {chat_id}")
            else:
                logger.error(f"Failed to send auto-response")
        except Exception as e:
            logger.error(f"Error sending response: {e}")

    async def refresh_profile_token(self, profile: Dict):
        """Refresh access token for a profile"""
        from avito_api_client import AvitoAPIClient
        import os

        client_id = os.getenv("AVITO_CLIENT_ID")
        client_secret = os.getenv("AVITO_CLIENT_SECRET")

        if not profile.get('refresh_token'):
            logger.error(f"No refresh token for profile {profile['id']}")
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
        else:
            logger.error(f"Failed to refresh token for profile {profile['id']}")


# Global worker instance
worker = MessengerWorker()
