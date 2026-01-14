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
        """
        Get current user information
        Endpoint: GET /core/v1/accounts/self
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/core/v1/accounts/self",
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get user info: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

    def get_chats(self, user_id: str, unread_only: bool = False, limit: int = 100, offset: int = 0) -> Optional[Dict]:
        """
        Get list of chats
        Endpoint: GET /messenger/v1/accounts/{user_id}/chats
        """
        try:
            params = {
                "limit": limit,
                "offset": offset
            }
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
                logger.error(f"Failed to get chats: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting chats: {e}")
            return None

    def get_chat_by_id(self, user_id: str, chat_id: str) -> Optional[Dict]:
        """
        Get specific chat information
        Endpoint: GET /messenger/v1/accounts/{user_id}/chats/{chat_id}
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/messenger/v1/accounts/{user_id}/chats/{chat_id}",
                headers=self.headers
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get chat: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting chat: {e}")
            return None

    def get_messages(self, user_id: str, chat_id: str, limit: int = 100, offset: int = 0) -> Optional[Dict]:
        """
        Get messages from chat (marks as read automatically)
        Endpoint: GET /messenger/v1/accounts/{user_id}/chats/{chat_id}/messages/
        """
        try:
            params = {
                "limit": limit,
                "offset": offset
            }

            response = requests.get(
                f"{self.BASE_URL}/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages/",
                headers=self.headers,
                params=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get messages: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return None

    def get_messages_v2(self, user_id: str, chat_id: str, limit: int = 100, offset: int = 0) -> Optional[Dict]:
        """
        Get messages from chat (does NOT mark as read)
        Endpoint: GET /messenger/v2/accounts/{user_id}/chats/{chat_id}/messages/
        """
        try:
            params = {
                "limit": limit,
                "offset": offset
            }

            response = requests.get(
                f"{self.BASE_URL}/messenger/v2/accounts/{user_id}/chats/{chat_id}/messages/",
                headers=self.headers,
                params=params
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get messages v2: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting messages v2: {e}")
            return None

    def send_message(self, user_id: str, chat_id: str, message_text: str) -> Optional[Dict]:
        """
        Send message to chat
        Endpoint: POST /messenger/v1/accounts/{user_id}/chats/{chat_id}/messages
        """
        try:
            payload = {
                "message": {
                    "text": message_text
                },
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
                logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None

    def mark_chat_as_read(self, user_id: str, chat_id: str) -> bool:
        """
        Mark chat as read
        Endpoint: POST /messenger/v1/accounts/{user_id}/chats/{chat_id}/read
        """
        try:
            response = requests.post(
                f"{self.BASE_URL}/messenger/v1/accounts/{user_id}/chats/{chat_id}/read",
                headers=self.headers
            )

            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Error marking chat as read: {e}")
            return False

    def delete_message(self, user_id: str, chat_id: str, message_id: str) -> bool:
        """
        Delete message (only messages less than 1 hour old)
        Endpoint: POST /messenger/v1/accounts/{user_id}/chats/{chat_id}/messages/{message_id}
        """
        try:
            response = requests.post(
                f"{self.BASE_URL}/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages/{message_id}",
                headers=self.headers
            )

            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return False

    def subscribe_webhook(self, webhook_url: str) -> bool:
        """
        Subscribe to webhook notifications
        Endpoint: POST /messenger/v1/webhook
        """
        try:
            payload = {
                "url": webhook_url
            }

            response = requests.post(
                f"{self.BASE_URL}/messenger/v1/webhook",
                headers=self.headers,
                json=payload
            )

            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Error subscribing webhook: {e}")
            return False

    def unsubscribe_webhook(self, webhook_url: str) -> bool:
        """
        Unsubscribe from webhook notifications
        Endpoint: POST /messenger/v1/webhook/unsubscribe
        """
        try:
            payload = {
                "url": webhook_url
            }

            response = requests.post(
                f"{self.BASE_URL}/messenger/v1/webhook/unsubscribe",
                headers=self.headers,
                json=payload
            )

            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Error unsubscribing webhook: {e}")
            return False

    @staticmethod
    def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> Optional[Dict]:
        """
        Refresh access token using refresh token
        Endpoint: POST /token
        """
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
                logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None
