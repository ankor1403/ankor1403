"""
Avito Management Platform - Full API Integration
"""
import os, sqlite3, secrets, hashlib, json
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode
import requests
from fastapi import FastAPI, Request, Form, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Avito Management Platform")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "data/app.db"))
AVITO_CLIENT_ID = os.getenv("AVITO_CLIENT_ID", "")
AVITO_CLIENT_SECRET = os.getenv("AVITO_CLIENT_SECRET", "")
AVITO_REDIRECT_URI = os.getenv("AVITO_REDIRECT_URI", "")
AVITO_AUTH_URL = "https://www.avito.ru/oauth"
AVITO_TOKEN_URL = "https://api.avito.ru/token"
AVITO_API_BASE = "https://api.avito.ru"

# All available scopes - comma-separated format for Avito OAuth
ALL_SCOPES = "messenger:read,messenger:write,items:info,items:apply_vas,stats:read,autoload:reports,user:read,user_balance:read,user_operations:read"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY, user_id INTEGER, token TEXT UNIQUE, expires_at TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, avito_user_id TEXT, avito_profile_name TEXT, avito_email TEXT, avito_phone TEXT, access_token TEXT, refresh_token TEXT, token_expires_at TIMESTAMP, connected_at TIMESTAMP, status TEXT DEFAULT 'pending')")
    conn.commit()
    conn.close()

init_db()

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

def create_session(uid):
    token = secrets.token_urlsafe(32)
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)", (uid, token, datetime.now() + timedelta(days=30)))
    conn.commit()
    conn.close()
    return token

def get_user(token):
    if not token: return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    r = conn.cursor().execute("SELECT u.* FROM users u JOIN sessions s ON u.id = s.user_id WHERE s.token = ? AND s.expires_at > ?", (token, datetime.now())).fetchone()
    conn.close()
    return dict(r) if r else None

def avito_api(profile, method, endpoint, data=None):
    """Make Avito API request with proper error handling"""
    token = profile.get("access_token")
    if not token: return {"error": "No token"}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{AVITO_API_BASE}{endpoint}"

    try:
        if method == "GET":
            r = requests.get(url, headers=headers, params=data, timeout=30)
        elif method == "POST":
            r = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            return {"error": "Bad method"}

        print(f"API {method} {endpoint}: {r.status_code}")

        # Try to parse JSON, handle non-JSON responses
        try:
            result = r.json()
        except:
            if r.status_code == 403:
                return {"error": "Forbidden - need scope"}
            elif r.status_code == 404:
                return {"error": "Not found"}
            return {"error": f"HTTP {r.status_code}"}

        # Check for error in response
        if "error" in result:
            return {"error": result["error"].get("message", str(result["error"]))}

        return result
    except Exception as e:
        return {"error": str(e)}

def get_user_self(token):
    """Get user info after OAuth"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{AVITO_API_BASE}/core/v1/accounts/self", headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
    except: pass
    return {}

# ============ API Functions ============
def get_balance(p):
    uid = p.get("avito_user_id")
    if not uid: return {"error": "No user ID"}
    return avito_api(p, "GET", f"/core/v1/accounts/{uid}/balance/")

def get_items(p, page=1):
    uid = p.get("avito_user_id")
    if not uid: return {"error": "No user ID"}
    # Try v2 API first, then v1
    result = avito_api(p, "GET", f"/core/v2/items", {"per_page": 25, "page": page})
    if result.get("error"):
        result = avito_api(p, "GET", f"/core/v1/accounts/{uid}/items/", {"per_page": 25, "page": page})
    return result

def get_chats(p):
    uid = p.get("avito_user_id")
    if not uid: return {"error": "No user ID"}
    # Try v2 API (newer messenger)
    result = avito_api(p, "GET", f"/messenger/v2/accounts/{uid}/chats")
    if result.get("error"):
        result = avito_api(p, "GET", f"/messenger/v1/accounts/{uid}/chats")
    return result

def get_chat_messages(p, chat_id):
    uid = p.get("avito_user_id")
    if not uid: return {"error": "No user ID"}
    result = avito_api(p, "GET", f"/messenger/v2/accounts/{uid}/chats/{chat_id}/messages/")
    if result.get("error"):
        result = avito_api(p, "GET", f"/messenger/v1/accounts/{uid}/chats/{chat_id}/messages/")
    return result

def send_message(p, chat_id, text):
    uid = p.get("avito_user_id")
    if not uid: return {"error": "No user ID"}
    result = avito_api(p, "POST", f"/messenger/v2/accounts/{uid}/chats/{chat_id}/messages", {"message": {"text": text}})
    if result.get("error"):
        result = avito_api(p, "POST", f"/messenger/v1/accounts/{uid}/chats/{chat_id}/messages", {"message": {"text": text}})
    return result

def get_stats(p, item_ids, date_from=None, date_to=None):
    uid = p.get("avito_user_id")
    if not uid: return {"error": "No user ID"}
    data = {"itemIds": item_ids}
    if date_from: data["dateFrom"] = date_from
    if date_to: data["dateTo"] = date_to
    return avito_api(p, "POST", f"/stats/v1/accounts/{uid}/items", data)

# ============ Routes ============
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session: Optional[str] = Cookie(None)):
    if get_user(session): return RedirectResponse("/dashboard", 302)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    u = conn.cursor().execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, hash_password(password))).fetchone()
    conn.close()
    if not u: return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    response = RedirectResponse("/dashboard", 302)
    response.set_cookie("session", create_session(u["id"]), max_age=30*24*60*60, httponly=True)
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.cursor().execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        uid = conn.cursor().execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        response = RedirectResponse("/dashboard", 302)
        response.set_cookie("session", create_session(uid), max_age=30*24*60*60, httponly=True)
        return response
    except:
        conn.close()
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username exists"})

@app.get("/logout")
async def logout(session: Optional[str] = Cookie(None)):
    if session:
        conn = sqlite3.connect(DB_PATH)
        conn.cursor().execute("DELETE FROM sessions WHERE token=?", (session,))
        conn.commit()
        conn.close()
    response = RedirectResponse("/", 302)
    response.delete_cookie("session")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: Optional[str] = Cookie(None)):
    user = get_user(session)
    if not user: return RedirectResponse("/login", 302)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    profiles = [dict(p) for p in conn.cursor().execute("SELECT * FROM profiles WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()]
    conn.close()
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "profiles": profiles})

@app.post("/profile/add")
async def add_profile(name: str = Form(...), session: Optional[str] = Cookie(None)):
    user = get_user(session)
    if not user: return RedirectResponse("/login", 302)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO profiles (user_id, name, status) VALUES (?, ?, 'pending')", (user["id"], name))
    pid = c.lastrowid
    conn.commit()
    conn.close()
    return RedirectResponse(f"/profile/{pid}/connect", 302)

@app.get("/profile/{pid}")
async def profile_detail(request: Request, pid: int, session: Optional[str] = Cookie(None)):
    user = get_user(session)
    if not user: return RedirectResponse("/login", 302)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    p = conn.cursor().execute("SELECT * FROM profiles WHERE id=? AND user_id=?", (pid, user["id"])).fetchone()
    conn.close()
    if not p: raise HTTPException(404)
    profile = dict(p)
    balance = get_balance(profile) if profile.get("avito_user_id") else None
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "profile": profile, "balance": balance})

@app.get("/profile/{pid}/connect")
async def connect(pid: int, session: Optional[str] = Cookie(None)):
    user = get_user(session)
    if not user: return RedirectResponse("/login", 302)
    # Request all scopes - Avito will only grant what's configured for the app
    params = {"response_type": "code", "client_id": AVITO_CLIENT_ID, "redirect_uri": AVITO_REDIRECT_URI, "scope": ALL_SCOPES, "state": str(pid)}
    return RedirectResponse(f"{AVITO_AUTH_URL}?{urlencode(params)}", 302)

@app.get("/profile/{pid}/reconnect")
async def reconnect(pid: int, session: Optional[str] = Cookie(None)):
    user = get_user(session)
    if not user: return RedirectResponse("/login", 302)
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("UPDATE profiles SET access_token=NULL, refresh_token=NULL, avito_user_id=NULL, status='pending' WHERE id=? AND user_id=?", (pid, user["id"]))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/profile/{pid}/connect", 302)

@app.post("/profile/{pid}/delete")
async def delete_profile(pid: int, session: Optional[str] = Cookie(None)):
    user = get_user(session)
    if not user: return RedirectResponse("/login", 302)
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("DELETE FROM profiles WHERE id=? AND user_id=?", (pid, user["id"]))
    conn.commit()
    conn.close()
    return RedirectResponse("/dashboard", 302)

@app.get("/avito/callback")
@app.get("/api/v1/avito/callback")
async def callback(request: Request, code: str = None, state: str = None, error: str = None):
    print(f"=== CALLBACK: code={code[:20] if code else None}..., state={state}, error={error}")

    if error: return HTMLResponse(f"<h1>Error: {error}</h1><a href='/dashboard'>Back</a>")
    if not code or not state: return HTMLResponse("<h1>Missing params</h1><a href='/dashboard'>Back</a>")

    try: pid = int(state)
    except: return HTMLResponse("<h1>Invalid state</h1><a href='/dashboard'>Back</a>")

    # Exchange code for token
    r = requests.post(AVITO_TOKEN_URL, headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code", "code": code, "client_id": AVITO_CLIENT_ID,
              "client_secret": AVITO_CLIENT_SECRET, "redirect_uri": AVITO_REDIRECT_URI})

    print(f"Token response: {r.status_code} - {r.text[:300]}")

    if r.status_code != 200:
        return HTMLResponse(f"<h1>Token Error</h1><pre>{r.text}</pre><a href='/dashboard'>Back</a>")

    data = r.json()
    if "error" in data:
        return HTMLResponse(f"<h1>Error: {data.get('error_description', data['error'])}</h1><a href='/dashboard'>Back</a>")

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    scope = data.get("scope", "")

    print(f"Got token, scope: {scope}")

    if not access_token:
        return HTMLResponse(f"<h1>No token</h1><pre>{json.dumps(data)}</pre><a href='/dashboard'>Back</a>")

    # Get user info
    user_info = get_user_self(access_token)
    avito_user_id = user_info.get("id")
    avito_name = user_info.get("name")
    avito_email = user_info.get("email")
    avito_phone = user_info.get("phone")

    print(f"User: id={avito_user_id}, name={avito_name}")

    # Save to DB
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("""UPDATE profiles SET access_token=?, refresh_token=?, token_expires_at=?,
        avito_user_id=?, avito_profile_name=?, avito_email=?, avito_phone=?, status='connected', connected_at=?
        WHERE id=?""", (access_token, refresh_token, datetime.now() + timedelta(seconds=data.get("expires_in", 86400)),
        avito_user_id, avito_name, avito_email, avito_phone, datetime.now(), pid))
    conn.commit()
    conn.close()

    return RedirectResponse(f"/profile/{pid}", 302)

# ============ Feature Pages ============
@app.get("/profile/{pid}/messages")
async def messages_page(request: Request, pid: int, session: Optional[str] = Cookie(None)):
    user = get_user(session)
    if not user: return RedirectResponse("/login", 302)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    p = conn.cursor().execute("SELECT * FROM profiles WHERE id=? AND user_id=?", (pid, user["id"])).fetchone()
    conn.close()
    if not p: raise HTTPException(404)
    profile = dict(p)
    chats = get_chats(profile)
    return templates.TemplateResponse("messages.html", {"request": request, "user": user, "profile": profile, "chats": chats})

@app.get("/profile/{pid}/chat/{chat_id}")
async def chat_page(request: Request, pid: int, chat_id: str, session: Optional[str] = Cookie(None)):
    user = get_user(session)
    if not user: return RedirectResponse("/login", 302)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    p = conn.cursor().execute("SELECT * FROM profiles WHERE id=? AND user_id=?", (pid, user["id"])).fetchone()
    conn.close()
    if not p: raise HTTPException(404)
    profile = dict(p)
    messages = get_chat_messages(profile, chat_id)
    return templates.TemplateResponse("chat.html", {"request": request, "user": user, "profile": profile, "chat_id": chat_id, "messages": messages})

@app.post("/profile/{pid}/chat/{chat_id}/send")
async def send_msg(pid: int, chat_id: str, message: str = Form(...), session: Optional[str] = Cookie(None)):
    user = get_user(session)
    if not user: return RedirectResponse("/login", 302)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    p = conn.cursor().execute("SELECT * FROM profiles WHERE id=? AND user_id=?", (pid, user["id"])).fetchone()
    conn.close()
    if not p: raise HTTPException(404)
    send_message(dict(p), chat_id, message)
    return RedirectResponse(f"/profile/{pid}/chat/{chat_id}", 302)

@app.get("/profile/{pid}/items")
async def items_page(request: Request, pid: int, page: int = 1, session: Optional[str] = Cookie(None)):
    user = get_user(session)
    if not user: return RedirectResponse("/login", 302)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    p = conn.cursor().execute("SELECT * FROM profiles WHERE id=? AND user_id=?", (pid, user["id"])).fetchone()
    conn.close()
    if not p: raise HTTPException(404)
    profile = dict(p)
    items = get_items(profile, page)
    return templates.TemplateResponse("items.html", {"request": request, "user": user, "profile": profile, "items_data": items, "current_page": page})

@app.get("/profile/{pid}/wallet")
async def wallet_page(request: Request, pid: int, session: Optional[str] = Cookie(None)):
    user = get_user(session)
    if not user: return RedirectResponse("/login", 302)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    p = conn.cursor().execute("SELECT * FROM profiles WHERE id=? AND user_id=?", (pid, user["id"])).fetchone()
    conn.close()
    if not p: raise HTTPException(404)
    profile = dict(p)
    balance = get_balance(profile)
    return templates.TemplateResponse("wallet.html", {"request": request, "user": user, "profile": profile, "balance": balance})

@app.get("/profile/{pid}/stats")
async def stats_page(request: Request, pid: int, session: Optional[str] = Cookie(None)):
    user = get_user(session)
    if not user: return RedirectResponse("/login", 302)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    p = conn.cursor().execute("SELECT * FROM profiles WHERE id=? AND user_id=?", (pid, user["id"])).fetchone()
    conn.close()
    if not p: raise HTTPException(404)
    profile = dict(p)
    # Get items first, then stats
    items_data = get_items(profile)
    item_ids = [i["id"] for i in items_data.get("resources", [])] if not items_data.get("error") else []
    stats = get_stats(profile, item_ids) if item_ids else {"error": "No items"}
    return templates.TemplateResponse("stats.html", {"request": request, "user": user, "profile": profile, "stats": stats})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8300)
