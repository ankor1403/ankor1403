"""
Avito Management Platform
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
from fastapi import FastAPI, Request, Form, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Avito Management Platform")
templates = Jinja2Templates(directory="templates")

DB_PATH = os.getenv("DB_PATH", "data/app.db")
AVITO_CLIENT_ID = os.getenv("AVITO_CLIENT_ID", "")
AVITO_CLIENT_SECRET = os.getenv("AVITO_CLIENT_SECRET", "")
AVITO_REDIRECT_URI = os.getenv("AVITO_REDIRECT_URI", "")
AVITO_AUTH_URL = "https://www.avito.ru/oauth"
AVITO_TOKEN_URL = "https://api.avito.ru/token"
AVITO_API_BASE = "https://api.avito.ru"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, token TEXT UNIQUE NOT NULL, expires_at TIMESTAMP NOT NULL)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL, avito_user_id TEXT, avito_profile_name TEXT, access_token TEXT, refresh_token TEXT, token_expires_at TIMESTAMP, connected_at TIMESTAMP, status TEXT DEFAULT 'pending')""")
    conn.commit()
    conn.close()

init_db()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=30)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)", (user_id, token, expires_at))
    conn.commit()
    conn.close()
    return token

def get_user_from_session(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    result = cursor.execute("SELECT u.* FROM users u JOIN sessions s ON u.id = s.user_id WHERE s.token = ? AND s.expires_at > ?", (token, datetime.now())).fetchone()
    conn.close()
    return dict(result) if result else None

def get_avito_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

def make_avito_request(profile: dict, method: str, endpoint: str, data: dict = None) -> dict:
    access_token = profile.get("access_token")
    if not access_token:
        return {"error": "No access token"}
    url = f"{AVITO_API_BASE}{endpoint}"
    headers = get_avito_headers(access_token)
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=data, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            return {"error": "Invalid method"}
        print(f"API {method} {endpoint}: {response.status_code} - {response.text[:200]}")
        return response.json() if response.text else {"status": response.status_code}
    except Exception as e:
        return {"error": str(e)}

def get_avito_user_self(access_token: str) -> dict:
    """Get current user info using access token directly"""
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    try:
        # Try different endpoints to get user info
        endpoints = [
            "/core/v1/users/self",
            "/core/v1/accounts/self",
        ]
        for endpoint in endpoints:
            url = f"{AVITO_API_BASE}{endpoint}"
            print(f"Trying endpoint: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            print(f"Response {response.status_code}: {response.text[:300]}")
            if response.status_code == 200:
                data = response.json()
                if data.get("id"):
                    return data
        return {"error": "Could not get user info from any endpoint"}
    except Exception as e:
        print(f"Error getting user self: {e}")
        return {"error": str(e)}

def get_avito_balance(profile: dict) -> dict:
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "GET", f"/core/v1/accounts/{user_id}/balance/")

def get_avito_items(profile: dict, page: int = 1) -> dict:
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "GET", f"/core/v1/accounts/{user_id}/items/", {"page": page, "per_page": 25})

def get_avito_chats(profile: dict) -> dict:
    user_id = profile.get("avito_user_id")
    if not user_id:
        return {"error": "No Avito user ID"}
    return make_avito_request(profile, "GET", f"/messenger/v1/accounts/{user_id}/chats/")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    user = conn.cursor().execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, hash_password(password))).fetchone()
    conn.close()
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    token = create_session(user["id"])
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie("session", token, max_age=30*24*60*60, httponly=True)
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        token = create_session(user_id)
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie("session", token, max_age=30*24*60*60, httponly=True)
        return response
    except sqlite3.IntegrityError:
        conn.close()
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists"})

@app.get("/logout")
async def logout(session: Optional[str] = Cookie(None)):
    if session:
        conn = sqlite3.connect(DB_PATH)
        conn.cursor().execute("DELETE FROM sessions WHERE token = ?", (session,))
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
    profiles = conn.cursor().execute("SELECT * FROM profiles WHERE user_id = ? ORDER BY id DESC", (user["id"],)).fetchall()
    conn.close()
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "profiles": [dict(p) for p in profiles]})

@app.post("/profile/add")
async def add_profile(name: str = Form(...), session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO profiles (user_id, name, status) VALUES (?, ?, 'pending')", (user["id"], name))
    profile_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/profile/{profile_id}/connect", status_code=302)

@app.get("/profile/{profile_id}", response_class=HTMLResponse)
async def profile_detail(request: Request, profile_id: int, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    profile = conn.cursor().execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?", (profile_id, user["id"])).fetchone()
    conn.close()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile_dict = dict(profile)
    balance = get_avito_balance(profile_dict) if profile_dict.get("avito_user_id") else None
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "profile": profile_dict, "balance": balance})

@app.get("/profile/{profile_id}/connect")
async def connect_avito(profile_id: int, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    params = {
        "response_type": "code",
        "client_id": AVITO_CLIENT_ID,
        "redirect_uri": AVITO_REDIRECT_URI,
        "scope": "user:read",
        "state": str(profile_id)
    }
    auth_url = f"{AVITO_AUTH_URL}?{urlencode(params)}"
    print(f"Redirecting to: {auth_url}")
    return RedirectResponse(url=auth_url, status_code=302)

@app.get("/profile/{profile_id}/reconnect")
async def reconnect_avito(profile_id: int, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("UPDATE profiles SET access_token = NULL, refresh_token = NULL, avito_user_id = NULL, status = 'pending' WHERE id = ? AND user_id = ?", (profile_id, user["id"]))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/profile/{profile_id}/connect", status_code=302)

@app.post("/profile/{profile_id}/delete")
async def delete_profile(profile_id: int, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("DELETE FROM profiles WHERE id = ? AND user_id = ?", (profile_id, user["id"]))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/avito/callback")
@app.get("/api/v1/avito/callback")
async def avito_callback(request: Request, code: str = None, state: str = None, error: str = None):
    print(f"=== AVITO CALLBACK ===")
    print(f"Full URL: {request.url}")
    print(f"Code: {code[:20] if code else None}..., State: {state}, Error: {error}")

    if error:
        return HTMLResponse(f"<h1>OAuth Error: {error}</h1><a href='/dashboard'>Back</a>")
    if not code or not state:
        return HTMLResponse("<h1>Missing code or state</h1><a href='/dashboard'>Back</a>")

    try:
        profile_id = int(state)
    except ValueError:
        return HTMLResponse("<h1>Invalid state</h1><a href='/dashboard'>Back</a>")

    try:
        print(f"Exchanging code for token...")

        token_response = requests.post(AVITO_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": AVITO_CLIENT_ID,
                "client_secret": AVITO_CLIENT_SECRET,
                "redirect_uri": AVITO_REDIRECT_URI
            })

        print(f"Token response status: {token_response.status_code}")
        print(f"Token response body: {token_response.text}")

        if token_response.status_code != 200:
            return HTMLResponse(f"<h1>Token Error: HTTP {token_response.status_code}</h1><pre>{token_response.text}</pre><a href='/dashboard'>Back</a>")

        token_data = token_response.json()

        if "error" in token_data:
            return HTMLResponse(f"<h1>Token Error: {token_data.get('error_description', token_data.get('error'))}</h1><a href='/dashboard'>Back</a>")

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        print(f"Got access_token: {access_token[:30] if access_token else 'None'}...")

        if not access_token:
            return HTMLResponse(f"<h1>No access_token!</h1><pre>{json.dumps(token_data, indent=2)}</pre><a href='/dashboard'>Back</a>")

        # Get user_id via API call since it's not in token response
        print("Getting user info via API...")
        user_info = get_avito_user_self(access_token)
        avito_user_id = user_info.get("id")
        avito_name = user_info.get("name") or user_info.get("profile_name")

        print(f"User info result: id={avito_user_id}, name={avito_name}")
        print(f"Full user_info: {user_info}")

        expires_at = datetime.now() + timedelta(seconds=token_data.get("expires_in", 86400))

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE profiles SET access_token = ?, refresh_token = ?, token_expires_at = ?,
                avito_user_id = ?, avito_profile_name = ?, status = 'connected', connected_at = ?
            WHERE id = ?
        """, (access_token, refresh_token, expires_at, avito_user_id, avito_name, datetime.now(), profile_id))
        conn.commit()
        conn.close()

        print(f"Profile {profile_id} updated: user_id={avito_user_id}, name={avito_name}")
        return RedirectResponse(url=f"/profile/{profile_id}", status_code=302)

    except Exception as e:
        print(f"Exception in callback: {e}")
        import traceback
        traceback.print_exc()
        return HTMLResponse(f"<h1>Error: {str(e)}</h1><a href='/dashboard'>Back</a>")

@app.get("/profile/{profile_id}/items", response_class=HTMLResponse)
async def profile_items(request: Request, profile_id: int, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    profile = conn.cursor().execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?", (profile_id, user["id"])).fetchone()
    conn.close()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    items_data = get_avito_items(dict(profile))
    return templates.TemplateResponse("items.html", {"request": request, "user": user, "profile": dict(profile), "items_data": items_data, "current_page": 1})

@app.get("/profile/{profile_id}/messages", response_class=HTMLResponse)
async def profile_messages(request: Request, profile_id: int, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    profile = conn.cursor().execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?", (profile_id, user["id"])).fetchone()
    conn.close()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    chats = get_avito_chats(dict(profile))
    return templates.TemplateResponse("messages.html", {"request": request, "user": user, "profile": dict(profile), "chats": chats})

@app.get("/profile/{profile_id}/wallet", response_class=HTMLResponse)
async def profile_wallet(request: Request, profile_id: int, session: Optional[str] = Cookie(None)):
    user = get_user_from_session(session)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    profile = conn.cursor().execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?", (profile_id, user["id"])).fetchone()
    conn.close()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    balance = get_avito_balance(dict(profile))
    return templates.TemplateResponse("wallet.html", {"request": request, "user": user, "profile": dict(profile), "balance": balance})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8300)
