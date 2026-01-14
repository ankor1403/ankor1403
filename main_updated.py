"""
Avito Multi-Service Platform - Enhanced with Messenger functionality
"""

import requests
import os
import uuid
import sqlite3
import hashlib
import secrets
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlencode
from contextlib import contextmanager

from fastapi import FastAPI, Request, Form, HTTPException, Response, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Avito Multi-Service")
templates = Jinja2Templates(directory="/app/templates")

# Environment variables
AVITO_CLIENT_ID = os.getenv("AVITO_CLIENT_ID", "oRhUFoLmgR1oCXKKQhzg")
AVITO_CLIENT_SECRET = os.getenv("AVITO_CLIENT_SECRET", "2uxbvzFn7TPX3J1sfW0AqbHGIcEGesC06em_fNjg")
AVITO_REDIRECT_URI = os.getenv("AVITO_REDIRECT_URI", "https://avito.afonin-lisa.ru/api/v1/avito/callback")
AVITO_AUTH_URL = "https://avito.ru/oauth"
AVITO_TOKEN_URL = "https://api.avito.ru/token"
AVITO_API_URL = "https://api.avito.ru"

DB_PATH = "/app/data/avito.db"

# Database context manager
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Database initialization
def init_db():
    with get_db() as conn:
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Profiles table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                access_token TEXT,
                refresh_token TEXT,
                token_expires_at TIMESTAMP,
                avito_user_id TEXT,
                features TEXT DEFAULT '{}',
                autoresponder_text TEXT,
                n8n_webhook TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Messages table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                avito_message_id TEXT,
                chat_id TEXT,
                direction TEXT NOT NULL CHECK(direction IN ('in', 'out')),
                content TEXT,
                author_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            )
        """)

        # Chats table
        conn.execute("""
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
            )
        """)

        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_profile_chat ON messages(profile_id, chat_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_avito_id ON messages(avito_message_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chats_profile ON chats(profile_id)")

        conn.commit()

init_db()

# Helper functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_from_session(request: Request) -> Optional[dict]:
    session_token = request.cookies.get("session")
    if not session_token:
        return None

    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (session_token,)
        ).fetchone()
        return dict(user) if user else None

def require_auth(request: Request):
    user = get_user_from_session(request)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/"})
    return user

# Avito API helper class
class AvitoAPI:
    @staticmethod
    def get_user_info(access_token: str) -> Optional[Dict]:
        """Get Avito user info to retrieve user_id"""
        try:
            response = requests.get(
                f"{AVITO_API_URL}/core/v1/accounts/self",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

    @staticmethod
    def get_chats(access_token: str, user_id: str, limit: int = 100) -> Optional[Dict]:
        """Get list of chats"""
        try:
            response = requests.get(
                f"{AVITO_API_URL}/messenger/v1/accounts/{user_id}/chats",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"limit": limit}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error getting chats: {e}")
            return None

    @staticmethod
    def get_messages(access_token: str, user_id: str, chat_id: str, limit: int = 50) -> Optional[Dict]:
        """Get messages from chat"""
        try:
            response = requests.get(
                f"{AVITO_API_URL}/messenger/v2/accounts/{user_id}/chats/{chat_id}/messages/",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"limit": limit}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return None

    @staticmethod
    def send_message(access_token: str, user_id: str, chat_id: str, text: str) -> Optional[Dict]:
        """Send message to chat"""
        try:
            response = requests.post(
                f"{AVITO_API_URL}/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "message": {"text": text},
                    "type": "text"
                }
            )
            if response.status_code in [200, 201]:
                return response.json()
            logger.error(f"Send message failed: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_user_from_session(request)
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()

        if existing:
            return HTMLResponse("<h1>Username already exists</h1><a href='/register'>Try again</a>")

        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password))
        )
        conn.commit()

    return RedirectResponse(url="/?registered=1", status_code=302)

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password_hash = ?",
            (username, hash_password(password))
        ).fetchone()

        if not user:
            return HTMLResponse("<h1>Invalid credentials</h1><a href='/'>Try again</a>")

        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(key="session", value=str(user["id"]))
        return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = require_auth(request)

    with get_db() as conn:
        profiles = conn.execute(
            "SELECT * FROM profiles WHERE user_id = ? ORDER BY created_at DESC",
            (user["id"],)
        ).fetchall()

        profiles_data = []
        for p in profiles:
            profile_dict = dict(p)
            profile_dict['features'] = json.loads(p['features'])

            # Get message count
            msg_count = conn.execute(
                "SELECT COUNT(*) as count FROM messages WHERE profile_id = ?",
                (p['id'],)
            ).fetchone()['count']

            profile_dict['message_count'] = msg_count
            profiles_data.append(profile_dict)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "profiles": profiles_data
    })

@app.post("/profile/create")
async def create_profile(request: Request, name: str = Form(...)):
    user = require_auth(request)

    with get_db() as conn:
        conn.execute(
            """INSERT INTO profiles (user_id, name, features)
               VALUES (?, ?, ?)""",
            (user["id"], name, json.dumps({
                "messenger_read": True,
                "messenger_write": True,
                "autoresponder": False,
                "stats": False,
            }))
        )
        conn.commit()

    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/profile/{profile_id}", response_class=HTMLResponse)
async def view_profile(request: Request, profile_id: int):
    user = require_auth(request)

    with get_db() as conn:
        profile = conn.execute(
            "SELECT * FROM profiles WHERE id = ? AND user_id = ?",
            (profile_id, user["id"])
        ).fetchone()

        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        profile_dict = dict(profile)
        profile_dict['features'] = json.loads(profile['features'])

        # Get recent messages
        messages = conn.execute(
            """SELECT * FROM messages
               WHERE profile_id = ?
               ORDER BY created_at DESC LIMIT 50""",
            (profile_id,)
        ).fetchall()

        messages_data = [dict(m) for m in messages]

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "profile": profile_dict,
        "messages": messages_data
    })

@app.post("/profile/{profile_id}/authorize")
async def authorize_profile(request: Request, profile_id: int):
    user = require_auth(request)

    with get_db() as conn:
        profile = conn.execute(
            "SELECT * FROM profiles WHERE id = ? AND user_id = ?",
            (profile_id, user["id"])
        ).fetchone()

        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

    # Redirect to Avito OAuth
    state = f"{user['id']}:{profile_id}"
    scopes = "messenger:read,messenger:write,items:info,items:apply_vas,stats:read,autoload:reports,user:read,user_balance:read,user_operations:read"

    params = {
        "response_type": "code",
        "client_id": AVITO_CLIENT_ID,
        "redirect_uri": AVITO_REDIRECT_URI,
        "state": state,
        "scope": scopes
    }
    oauth_url = f"{AVITO_AUTH_URL}?{urlencode(params)}"

    return RedirectResponse(url=oauth_url, status_code=302)

@app.get("/api/v1/avito/callback")
async def oauth_callback(code: str, state: str):
    # Parse state
    try:
        user_id_str, profile_id_str = state.split(":")
        user_id = int(user_id_str)
        profile_id = int(profile_id_str)
    except:
        return HTMLResponse("<h1>Invalid state parameter</h1>")

    # Exchange code for token
    try:
        token_response = requests.post(
            AVITO_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": AVITO_CLIENT_ID,
                "client_secret": AVITO_CLIENT_SECRET,
            }
        )

        if token_response.status_code != 200:
            error_msg = f"HTTP {token_response.status_code}: {token_response.text}"
            return HTMLResponse(f"<h1>Ошибка от Avito API: {error_msg}</h1><a href='/dashboard'>Вернуться</a>")

        token_data = token_response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token", "")
        expires_in = token_data.get("expires_in", 86400)

        # Get Avito user_id
        user_info = AvitoAPI.get_user_info(access_token)
        avito_user_id = user_info.get("id") if user_info else None

        if not avito_user_id:
            return HTMLResponse("<h1>Не удалось получить ID пользователя Avito</h1><a href='/dashboard'>Вернуться</a>")

        # Calculate expiration
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        # Save to database
        with get_db() as conn:
            conn.execute(
                """UPDATE profiles
                   SET access_token = ?,
                       refresh_token = ?,
                       token_expires_at = ?,
                       avito_user_id = ?
                   WHERE id = ? AND user_id = ?""",
                (access_token, refresh_token, expires_at.isoformat(), avito_user_id, profile_id, user_id)
            )
            conn.commit()

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return HTMLResponse(f"<h1>Ошибка: {str(e)}</h1><a href='/dashboard'>Вернуться</a>")

    return RedirectResponse(url=f"/profile/{profile_id}", status_code=302)

@app.post("/profile/{profile_id}/update-features")
async def update_features(
    request: Request,
    profile_id: int,
    messenger_read: Optional[str] = Form(None),
    messenger_write: Optional[str] = Form(None),
    autoresponder: Optional[str] = Form(None),
    stats: Optional[str] = Form(None)
):
    user = require_auth(request)

    features = {
        "messenger_read": messenger_read == "on",
        "messenger_write": messenger_write == "on",
        "autoresponder": autoresponder == "on",
        "stats": stats == "on",
    }

    with get_db() as conn:
        conn.execute(
            "UPDATE profiles SET features = ? WHERE id = ? AND user_id = ?",
            (json.dumps(features), profile_id, user["id"])
        )
        conn.commit()

    return RedirectResponse(url=f"/profile/{profile_id}", status_code=302)

@app.post("/profile/{profile_id}/update-autoresponder")
async def update_autoresponder(
    request: Request,
    profile_id: int,
    autoresponder_text: str = Form(...)
):
    user = require_auth(request)

    with get_db() as conn:
        conn.execute(
            "UPDATE profiles SET autoresponder_text = ? WHERE id = ? AND user_id = ?",
            (autoresponder_text, profile_id, user["id"])
        )
        conn.commit()

    return RedirectResponse(url=f"/profile/{profile_id}", status_code=302)

@app.post("/profile/{profile_id}/update-webhook")
async def update_webhook(
    request: Request,
    profile_id: int,
    n8n_webhook: str = Form(...)
):
    user = require_auth(request)

    with get_db() as conn:
        conn.execute(
            "UPDATE profiles SET n8n_webhook = ? WHERE id = ? AND user_id = ?",
            (n8n_webhook, profile_id, user["id"])
        )
        conn.commit()

    return RedirectResponse(url=f"/profile/{profile_id}", status_code=302)

# API endpoints for manual message management
@app.get("/api/profile/{profile_id}/chats")
async def get_profile_chats(request: Request, profile_id: int):
    user = require_auth(request)

    with get_db() as conn:
        profile = conn.execute(
            "SELECT * FROM profiles WHERE id = ? AND user_id = ?",
            (profile_id, user["id"])
        ).fetchone()

        if not profile or not profile['access_token'] or not profile['avito_user_id']:
            raise HTTPException(status_code=404, detail="Profile not authorized")

        chats = AvitoAPI.get_chats(profile['access_token'], profile['avito_user_id'])
        return JSONResponse(chats if chats else {"error": "Failed to fetch chats"})

@app.get("/api/profile/{profile_id}/chat/{chat_id}/messages")
async def get_chat_messages(request: Request, profile_id: int, chat_id: str):
    user = require_auth(request)

    with get_db() as conn:
        profile = conn.execute(
            "SELECT * FROM profiles WHERE id = ? AND user_id = ?",
            (profile_id, user["id"])
        ).fetchone()

        if not profile or not profile['access_token'] or not profile['avito_user_id']:
            raise HTTPException(status_code=404, detail="Profile not authorized")

        messages = AvitoAPI.get_messages(profile['access_token'], profile['avito_user_id'], chat_id)
        return JSONResponse(messages if messages else {"error": "Failed to fetch messages"})

@app.post("/api/profile/{profile_id}/chat/{chat_id}/send")
async def send_chat_message(
    request: Request,
    profile_id: int,
    chat_id: str,
    text: str = Form(...)
):
    user = require_auth(request)

    with get_db() as conn:
        profile = conn.execute(
            "SELECT * FROM profiles WHERE id = ? AND user_id = ?",
            (profile_id, user["id"])
        ).fetchone()

        if not profile or not profile['access_token'] or not profile['avito_user_id']:
            raise HTTPException(status_code=404, detail="Profile not authorized")

        result = AvitoAPI.send_message(profile['access_token'], profile['avito_user_id'], chat_id, text)

        if result:
            # Save to database
            conn.execute("""
                INSERT INTO messages (profile_id, avito_message_id, chat_id, direction, content, created_at)
                VALUES (?, ?, ?, 'out', ?, ?)
            """, (profile_id, result.get('id', ''), chat_id, text, datetime.now()))
            conn.commit()

            return JSONResponse({"success": True, "message": result})
        else:
            return JSONResponse({"success": False, "error": "Failed to send message"}, status_code=500)

# Background worker startup/shutdown
@app.on_event("startup")
async def startup_event():
    """Start background worker on app startup"""
    from messenger_worker import worker
    asyncio.create_task(worker.start())
    logger.info("Application started, background worker launched")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop background worker on app shutdown"""
    from messenger_worker import worker
    await worker.stop()
    logger.info("Application shutdown, background worker stopped")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8300)
