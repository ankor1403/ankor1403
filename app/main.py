"""
Avito Management Platform - Full Featured
Based on official Avito API documentation
"""

import os
import sqlite3
import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import requests
from fastapi import FastAPI, Request, Form, HTTPException, Cookie, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# ============ Configuration ============
app = FastAPI(title="Avito Management Platform")
templates = Jinja2Templates(directory="templates")

# Database
DB_PATH = os.getenv("DB_PATH", "data/app.db")

# Avito API Configuration
AVITO_CLIENT_ID = os.getenv("AVITO_CLIENT_ID", "")
AVITO_CLIENT_SECRET = os.getenv("AVITO_CLIENT_SECRET", "")
AVITO_REDIRECT_URI = os.getenv("AVITO_REDIRECT_URI", "")

# Avito API URLs
AVITO_AUTH_URL = "https://www.avito.ru/oauth"
AVITO_TOKEN_URL = "https://api.avito.ru/token"
AVITO_API_BASE = "https://api.avito.ru"

# ============ Database Setup ============
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Avito profiles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            avito_user_id TEXT,
            avito_profile_name TEXT,
            avito_email TEXT,
            avito_phone TEXT,
            access_token TEXT,
            refresh_token TEXT,
            token_expires_at TIMESTAMP,
            connected_at TIMESTAMP,
            last_sync_at TIMESTAMP,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ============ Helper Functions ============
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=30)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
                   (user_id, token, expires_at))
    conn.commit()
    conn.close()
    return token

def get_user_from_session(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    result = cursor.execute("""
        SELECT u.* FROM users u
        JOIN sessions s ON u.id = s.user_id
        WHERE s.token = ? AND s.expires_at > ?
    """, (token, datetime.now())).fetchone()
    conn.close()
    return dict(result) if result else None

def get_avito_headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

def refresh_avito_token(profile_id: int) -> Optional[str]:
    """Refresh Avito access token using refresh token"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()

    if not profile or not profile["refresh_token"]:
        conn.close()
        return None

    try:
        response = requests.post(AVITO_TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": profile["refresh_token"],
            "client_id": AVITO_CLIENT_ID,
            "client_secret": AVITO_CLIENT_SECRET
        })

        if response.status_code == 200:
            token_data = response.json()
            expires_at = datetime.now() + timedelta(seconds=token_data.get("expires_in", 86400))
            cursor.execute("""
                UPDATE profiles
                SET access_token = ?, refresh_token = ?, token_expires_at = ?
                WHERE id = ?
            """, (token_data["access_token"], token_data.get("refresh_token"), expires_at, profile_id))
            conn.commit()
            conn.close()
            return token_data["access_token"]
    except Exception:
        pass

    conn.close()
    return None

def make_avito_request(profile: dict, method: str, endpoint: str, data: dict = None) -> dict:
    """Make authenticated request to Avito API with auto token refresh"""
    access_token = profile.get("access_token")

    # Check if token needs refresh
    if profile.get("token_expires_at"):
        try:
            expires = datetime.fromisoformat(str(profile["token_expires_at"]))
            if expires < datetime.now():
                new_token = refresh_avito_token(profile["id"])
                if new_token:
                    access_token = new_token
        except:
            pass

    if not access_token:
        return {"error": "No access token"}

    url = f"{AVITO_API_BASE}{endpoint}"
    headers = get_avito_headers(access_token)

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=data, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            return {"error": "Invalid method"}

        if response.status_code == 401:
            # Try to refresh token
            new_token = refresh_avito_token(profile["id"])
            if new_token:
                headers = get_avito_headers(new_token)
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, params=data, timeout=30)
                elif method.upper() == "POST":
                    response = requests.post(url, headers=headers, json=data, timeout=30)
                elif method.upper() == "PUT":
                    response = requests.put(url, headers=headers, json=data, timeout=30)

        return response.json() if response.text else {"status": response.status_code}
    except Exception as e:
        return {"error": str(e)}

# ============ Avito API Functions ============

def get_avito_user_info(profile: dict) -> dict:
    """Get user info from Avito"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    # Try the account info endpoint
    result = make_avito_request(profile, "GET", f"/core/v1/accounts/{user_id}/")
    if result.get("error") or not result.get("id"):
        # Fallback - try alternative endpoint
        result = make_avito_request(profile, "GET", "/core/v1/users/self")
    return result

def get_avito_balance(profile: dict) -> dict:
    """Get wallet balance"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "GET", f"/core/v1/accounts/{user_id}/balance/")

def get_avito_operations(profile: dict, page: int = 1, per_page: int = 25) -> dict:
    """Get wallet operations history"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "GET", f"/core/v1/accounts/{user_id}/operations/",
                              {"page": page, "per_page": per_page})

def get_avito_items(profile: dict, page: int = 1, per_page: int = 25, status: str = None) -> dict:
    """Get user's items (ads)"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    params = {"page": page, "per_page": per_page}
    if status:
        params["status"] = status
    return make_avito_request(profile, "GET", f"/core/v1/accounts/{user_id}/items/", params)

def get_avito_item_info(profile: dict, item_id: int) -> dict:
    """Get detailed info about specific item"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "GET", f"/core/v1/accounts/{user_id}/items/{item_id}/")

def get_avito_items_stats(profile: dict, item_ids: list, date_from: str = None, date_to: str = None) -> dict:
    """Get statistics for items"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    data = {"itemIds": item_ids}
    if date_from:
        data["dateFrom"] = date_from
    if date_to:
        data["dateTo"] = date_to
    return make_avito_request(profile, "POST", f"/stats/v1/accounts/{user_id}/items", data)

def get_avito_calls_stats(profile: dict, item_ids: list, date_from: str = None, date_to: str = None) -> dict:
    """Get calls statistics"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    data = {"itemIds": item_ids}
    if date_from:
        data["dateFrom"] = date_from
    if date_to:
        data["dateTo"] = date_to
    return make_avito_request(profile, "POST", f"/core/v1/accounts/{user_id}/calls/stats/", data)

def get_avito_chats(profile: dict, item_id: int = None, unread_only: bool = False) -> dict:
    """Get messenger chats"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    params = {}
    if item_id:
        params["item_id"] = item_id
    if unread_only:
        params["unread_only"] = "true"
    return make_avito_request(profile, "GET", f"/messenger/v1/accounts/{user_id}/chats/", params)

def get_avito_chat_messages(profile: dict, chat_id: str, limit: int = 50) -> dict:
    """Get messages from specific chat"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "GET", f"/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages/",
                              {"limit": limit})

def send_avito_message(profile: dict, chat_id: str, message: str) -> dict:
    """Send message to chat"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "POST", f"/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages/",
                              {"message": {"text": message}})

def delete_avito_message(profile: dict, chat_id: str, message_id: str) -> dict:
    """Delete message"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "DELETE",
                              f"/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages/{message_id}")

def read_avito_chat(profile: dict, chat_id: str) -> dict:
    """Mark chat as read"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "POST", f"/messenger/v1/accounts/{user_id}/chats/{chat_id}/read")

def get_avito_vas_prices(profile: dict, item_ids: list) -> dict:
    """Get VAS (value-added services) prices"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "POST", f"/core/v1/accounts/{user_id}/price/vas",
                              {"itemIds": item_ids})

def get_avito_vas_package_prices(profile: dict, item_ids: list) -> dict:
    """Get VAS package prices"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "POST", f"/core/v1/accounts/{user_id}/price/vas_packages",
                              {"itemIds": item_ids})

def apply_avito_vas(profile: dict, item_id: int, vas_id: str) -> dict:
    """Apply VAS to item"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "PUT", f"/core/v1/accounts/{user_id}/items/{item_id}/vas",
                              {"vasId": vas_id})

def apply_avito_vas_package(profile: dict, item_id: int, package_id: str) -> dict:
    """Apply VAS package to item"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "PUT", f"/core/v1/accounts/{user_id}/items/{item_id}/vas_packages",
                              {"packageId": package_id})

def get_avito_autoload_reports(profile: dict, page: int = 1, per_page: int = 10) -> dict:
    """Get autoload reports"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "GET", f"/autoload/v1/accounts/{user_id}/reports/",
                              {"page": page, "per_page": per_page})

def get_avito_autoload_last_report(profile: dict) -> dict:
    """Get last autoload report"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "GET", f"/autoload/v1/accounts/{user_id}/reports/last_report/")

def get_avito_autoload_report(profile: dict, report_id: int) -> dict:
    """Get specific autoload report"""
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "GET", f"/autoload/v1/accounts/{user_id}/reports/{report_id}/")

# ============ Routes ============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    user = cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?",
                          (username, hash_password(password))).fetchone()
    conn.close()

    if not user:
        return templates.TemplateResponse("login.html",
                                          {"request": request, "error": "Invalid credentials"})

    token = create_session(user["id"])
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie("session", token, max_age=30*24*60*60, httponly=True)
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                       (username, hash_password(password)))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        token = create_session(user_id)
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie("session", token, max_age=30*24*60*60, httponly=True)
        return response
    except sqlite3.IntegrityError:
        conn.close()
        return templates.TemplateResponse("register.html",
                                          {"request": request, "error": "Username already exists"})

@app.get("/logout")
async def logout(session: Optional[str] = Cookie(None)):
    if session:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (session,))
        conn.commit()
        conn.close()

    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profiles = cursor.execute("SELECT * FROM profiles WHERE user_id = ? ORDER BY id DESC",
                              (user["id"],)).fetchall()
    conn.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "profiles": [dict(p) for p in profiles]
    })

# ============ Profile Management ============

@app.post("/profile/add")
async def add_profile(request: Request, name: str = Form(...), session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO profiles (user_id, name, status) VALUES (?, ?, 'pending')",
                   (user["id"], name))
    profile_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return RedirectResponse(url=f"/profile/{profile_id}/connect", status_code=302)

@app.get("/profile/{profile_id}", response_class=HTMLResponse)
async def profile_detail(request: Request, profile_id: int, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_dict = dict(profile)
    avito_user = None
    balance = None

    # Get Avito user info if connected
    if profile_dict.get("access_token"):
        avito_user = get_avito_user_info(profile_dict)
        if not avito_user.get("error"):
            balance = get_avito_balance(profile_dict)

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "profile": profile_dict,
        "avito_user": avito_user,
        "balance": balance
    })

@app.get("/profile/{profile_id}/connect")
async def connect_avito(profile_id: int, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Build OAuth URL
    # Scopes: user:read, messenger:read, messenger:write, items:info, items:apply_vas, stats:read, user_balance:read, autoload:reports
    params = {
        "response_type": "code",
        "client_id": AVITO_CLIENT_ID,
        "redirect_uri": AVITO_REDIRECT_URI,
        "scope": "user:read messenger:read messenger:write items:info items:apply_vas stats:read user_balance:read autoload:reports",
        "state": str(profile_id)
    }
    auth_url = f"{AVITO_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url, status_code=302)

@app.get("/profile/{profile_id}/reconnect")
async def reconnect_avito(profile_id: int, session: Optional[str] = Cookie(None)):
    """Disconnect and reconnect Avito profile"""
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE profiles
        SET access_token = NULL, refresh_token = NULL, token_expires_at = NULL,
            avito_user_id = NULL, status = 'pending'
        WHERE id = ? AND user_id = ?
    """, (profile_id, user["id"]))
    conn.commit()
    conn.close()

    return RedirectResponse(url=f"/profile/{profile_id}/connect", status_code=302)

@app.get("/profile/{profile_id}/disconnect")
async def disconnect_avito(profile_id: int, session: Optional[str] = Cookie(None)):
    """Disconnect Avito profile (keep profile, remove tokens)"""
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE profiles
        SET access_token = NULL, refresh_token = NULL, token_expires_at = NULL,
            avito_user_id = NULL, avito_profile_name = NULL, status = 'disconnected'
        WHERE id = ? AND user_id = ?
    """, (profile_id, user["id"]))
    conn.commit()
    conn.close()

    return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/profile/{profile_id}/delete")
async def delete_profile(profile_id: int, session: Optional[str] = Cookie(None)):
    """Delete profile completely"""
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM profiles WHERE id = ? AND user_id = ?", (profile_id, user["id"]))
    conn.commit()
    conn.close()

    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/avito/callback")
@app.get("/api/v1/avito/callback")
async def avito_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle OAuth callback from Avito"""
    print(f"=== AVITO CALLBACK ===")
    print(f"URL: {request.url}")
    print(f"Code: {code[:20] if code else None}...")
    print(f"State: {state}")
    print(f"Error: {error}")

    if error:
        return HTMLResponse(f"<h1>Error: {error}</h1><a href='/dashboard'>Back to Dashboard</a>")

    if not code or not state:
        return HTMLResponse("<h1>Missing code or state</h1><a href='/dashboard'>Back</a>")

    try:
        profile_id = int(state)
    except ValueError:
        return HTMLResponse("<h1>Invalid state</h1><a href='/dashboard'>Back</a>")

    # Exchange code for token
    try:
        print(f"Exchanging code for token...")
        print(f"Client ID: {AVITO_CLIENT_ID}")
        print(f"Redirect URI: {AVITO_REDIRECT_URI}")

        token_response = requests.post(
            AVITO_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": AVITO_CLIENT_ID,
                "client_secret": AVITO_CLIENT_SECRET,
                "redirect_uri": AVITO_REDIRECT_URI
            }
        )

        print(f"Token response status: {token_response.status_code}")
        print(f"Token response: {token_response.text[:500]}")

        if token_response.status_code != 200:
            error_msg = f"HTTP {token_response.status_code}: {token_response.text}"
            return HTMLResponse(f"<h1>Avito API Error: {error_msg}</h1><a href='/dashboard'>Back</a>")

        token_data = token_response.json()

        # Check for error in JSON response
        if "error" in token_data:
            error_msg = token_data.get("error_description", token_data.get("error"))
            return HTMLResponse(f"<h1>Token Error: {error_msg}</h1><a href='/dashboard'>Back</a>")

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        user_id = token_data.get("user_id")  # Avito returns user_id in token response!

        print(f"Got access_token: {access_token[:20] if access_token else 'None'}...")
        print(f"Got user_id from token: {user_id}")

        if not access_token:
            return HTMLResponse(f"<h1>No access token in response</h1><pre>{json.dumps(token_data, indent=2)}</pre><a href='/dashboard'>Back</a>")

        expires_at = datetime.now() + timedelta(seconds=token_data.get("expires_in", 86400))

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Save token and user_id from token response
        cursor.execute("""
            UPDATE profiles
            SET access_token = ?, refresh_token = ?, token_expires_at = ?,
                avito_user_id = ?, status = 'connected', connected_at = ?
            WHERE id = ?
        """, (access_token, refresh_token, expires_at, user_id, datetime.now(), profile_id))
        conn.commit()

        print(f"Saved token and user_id to database")

        # Try to get additional user info from Avito API
        if user_id:
            conn.row_factory = sqlite3.Row
            profile = cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()

            if profile:
                profile_dict = dict(profile)
                # Try to get user info (may not work with limited scopes)
                try:
                    user_info = get_avito_user_info(profile_dict)
                    print(f"User info response: {user_info}")

                    if not user_info.get("error") and user_info.get("name"):
                        cursor.execute("""
                            UPDATE profiles
                            SET avito_profile_name = ?, avito_email = ?, avito_phone = ?
                            WHERE id = ?
                        """, (user_info.get("name"), user_info.get("email"),
                              user_info.get("phone"), profile_id))
                        conn.commit()
                except Exception as e:
                    print(f"Error getting user info: {e}")

        conn.close()
        return RedirectResponse(url=f"/profile/{profile_id}", status_code=302)

    except Exception as e:
        print(f"Exception in callback: {e}")
        import traceback
        traceback.print_exc()
        return HTMLResponse(f"<h1>Error: {str(e)}</h1><a href='/dashboard'>Back</a>")

# ============ Items (Ads) Management ============

@app.get("/profile/{profile_id}/items", response_class=HTMLResponse)
async def profile_items(request: Request, profile_id: int,
                        page: int = 1, status: str = None,
                        session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_dict = dict(profile)
    items_data = get_avito_items(profile_dict, page=page, per_page=25, status=status)

    return templates.TemplateResponse("items.html", {
        "request": request,
        "user": user,
        "profile": profile_dict,
        "items_data": items_data,
        "current_page": page,
        "status_filter": status
    })

@app.get("/profile/{profile_id}/items/{item_id}", response_class=HTMLResponse)
async def item_detail(request: Request, profile_id: int, item_id: int,
                      session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_dict = dict(profile)
    item_info = get_avito_item_info(profile_dict, item_id)
    stats = get_avito_items_stats(profile_dict, [item_id])
    vas_prices = get_avito_vas_prices(profile_dict, [item_id])

    return templates.TemplateResponse("item_detail.html", {
        "request": request,
        "user": user,
        "profile": profile_dict,
        "item": item_info,
        "stats": stats,
        "vas_prices": vas_prices
    })

@app.post("/profile/{profile_id}/items/{item_id}/vas")
async def apply_vas(profile_id: int, item_id: int, vas_id: str = Form(...),
                    session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = apply_avito_vas(dict(profile), item_id, vas_id)
    return RedirectResponse(url=f"/profile/{profile_id}/items/{item_id}?result={json.dumps(result)}",
                            status_code=302)

# ============ Statistics ============

@app.get("/profile/{profile_id}/stats", response_class=HTMLResponse)
async def profile_stats(request: Request, profile_id: int,
                        date_from: str = None, date_to: str = None,
                        session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_dict = dict(profile)

    # Set default date range (last 30 days)
    if not date_to:
        date_to = datetime.now().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    # Get items first
    items_data = get_avito_items(profile_dict, per_page=100)
    item_ids = []
    if items_data.get("resources"):
        item_ids = [item["id"] for item in items_data["resources"]]

    stats = {}
    calls_stats = {}
    if item_ids:
        stats = get_avito_items_stats(profile_dict, item_ids, date_from, date_to)
        calls_stats = get_avito_calls_stats(profile_dict, item_ids, date_from, date_to)

    return templates.TemplateResponse("stats.html", {
        "request": request,
        "user": user,
        "profile": profile_dict,
        "stats": stats,
        "calls_stats": calls_stats,
        "date_from": date_from,
        "date_to": date_to
    })

# ============ Messages ============

@app.get("/profile/{profile_id}/messages", response_class=HTMLResponse)
async def profile_messages(request: Request, profile_id: int,
                           unread_only: bool = False,
                           session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_dict = dict(profile)
    chats = get_avito_chats(profile_dict, unread_only=unread_only)

    return templates.TemplateResponse("messages.html", {
        "request": request,
        "user": user,
        "profile": profile_dict,
        "chats": chats,
        "unread_only": unread_only
    })

@app.get("/profile/{profile_id}/messages/{chat_id}", response_class=HTMLResponse)
async def chat_detail(request: Request, profile_id: int, chat_id: str,
                      session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_dict = dict(profile)
    messages = get_avito_chat_messages(profile_dict, chat_id)

    # Mark chat as read
    read_avito_chat(profile_dict, chat_id)

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "user": user,
        "profile": profile_dict,
        "chat_id": chat_id,
        "messages": messages
    })

@app.post("/profile/{profile_id}/messages/{chat_id}/send")
async def send_message(profile_id: int, chat_id: str, message: str = Form(...),
                       session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = send_avito_message(dict(profile), chat_id, message)
    return RedirectResponse(url=f"/profile/{profile_id}/messages/{chat_id}", status_code=302)

@app.post("/profile/{profile_id}/messages/{chat_id}/delete/{message_id}")
async def delete_message(profile_id: int, chat_id: str, message_id: str,
                         session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = delete_avito_message(dict(profile), chat_id, message_id)
    return RedirectResponse(url=f"/profile/{profile_id}/messages/{chat_id}", status_code=302)

# ============ Wallet/Balance ============

@app.get("/profile/{profile_id}/wallet", response_class=HTMLResponse)
async def profile_wallet(request: Request, profile_id: int,
                         page: int = 1,
                         session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_dict = dict(profile)
    balance = get_avito_balance(profile_dict)
    operations = get_avito_operations(profile_dict, page=page)

    return templates.TemplateResponse("wallet.html", {
        "request": request,
        "user": user,
        "profile": profile_dict,
        "balance": balance,
        "operations": operations,
        "current_page": page
    })

# ============ Autoload Reports ============

@app.get("/profile/{profile_id}/autoload", response_class=HTMLResponse)
async def profile_autoload(request: Request, profile_id: int,
                           page: int = 1,
                           session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_dict = dict(profile)
    reports = get_avito_autoload_reports(profile_dict, page=page)
    last_report = get_avito_autoload_last_report(profile_dict)

    return templates.TemplateResponse("autoload.html", {
        "request": request,
        "user": user,
        "profile": profile_dict,
        "reports": reports,
        "last_report": last_report,
        "current_page": page
    })

@app.get("/profile/{profile_id}/autoload/{report_id}", response_class=HTMLResponse)
async def autoload_report_detail(request: Request, profile_id: int, report_id: int,
                                 session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_dict = dict(profile)
    report = get_avito_autoload_report(profile_dict, report_id)

    return templates.TemplateResponse("autoload_report.html", {
        "request": request,
        "user": user,
        "profile": profile_dict,
        "report": report
    })

# ============ API Endpoints (for AJAX) ============

@app.get("/api/profile/{profile_id}/items")
async def api_items(profile_id: int, page: int = 1, status: str = None,
                    session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)

    return JSONResponse(get_avito_items(dict(profile), page=page, status=status))

@app.get("/api/profile/{profile_id}/chats")
async def api_chats(profile_id: int, unread_only: bool = False,
                    session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)

    return JSONResponse(get_avito_chats(dict(profile), unread_only=unread_only))

@app.get("/api/profile/{profile_id}/balance")
async def api_balance(profile_id: int, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    profile = cursor.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                             (profile_id, user["id"])).fetchone()
    conn.close()

    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)

    return JSONResponse(get_avito_balance(dict(profile)))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8300)
