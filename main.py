import os
import sqlite3
import secrets
import requests
from urllib.parse import urlencode

from fastapi import FastAPI, Request, Response, Depends, HTTPException, status, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from jose import jwt, JWTError
from dotenv import load_dotenv

# ** 세션 인증 방식으로 변경하기, firebase 확인해보기

# .env 세팅
load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

DB_PATH = "./users.db"

app = FastAPI()

# --- DB 유틸 ---

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def find_user(provider, provider_id):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE provider = ? AND provider_id = ?",
        (provider, provider_id)
    ).fetchone()
    conn.close()
    return user

def create_user(provider, provider_id, email, name, picture):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (provider, provider_id, email, name, picture) VALUES (?, ?, ?, ?, ?)",
        (provider, provider_id, email, name, picture)
    )
    conn.commit()
    new_user = conn.execute(
        "SELECT * FROM users WHERE provider = ? AND provider_id = ?",
        (provider, provider_id)
    ).fetchone()
    conn.close()
    return new_user

def find_user_by_id(id):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (id,)
    ).fetchone()
    conn.close()
    return user

# --- 구글 OAuth2 로그인 ---

@app.get("/auth/google")
async def google_auth(response: Response):
    state = secrets.token_hex(16)
    response.set_cookie("oauth_state", state, httponly=True, samesite="lax")
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url)

@app.get("/auth/google/callback")
async def google_callback(request: Request,
                          code: str = None,
                          state: str = None,
                          oauth_state: str = Cookie(None)):
    if not code or not state or not oauth_state or state != oauth_state:
        return JSONResponse({"error":"Invalid state"}, status_code=400)
    
    # 코드 -> 토큰 교환
    token_res = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        },
        headers={"Content-Type":"application/x-www-form-urlencoded"}
    )
    if token_res.status_code != 200:
        return JSONResponse({"error": "Token exchange failed"}, status_code=400)
    id_token = token_res.json().get("id_token")
    if not id_token:
        return JSONResponse({"error": "Missing id_token"}, status_code=400)
    
    # id_token 디코딩
    try:
        payload = jwt.decode(id_token, options={"verify_signature": False}, algorithms=["RS256", "HS256"])
        google_sub = payload["sub"]
        email = payload.get("email")
        name = payload.get("name")
    except Exception as e:
        return JSONResponse({"error":"ID token decode failed"}, status_code=400)

    # 유저 생성/조회
    user = find_user("google", google_sub)
    if not user:
        user = create_user("google", google_sub, email, name, picture)

    # 서비스 JWT 발급
    our_token = jwt.encode({"userId": user["id"], "email": user["email"]}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    resp = RedirectResponse(url="/login-success")  # 원하는 프론트 페이지로!
    resp.set_cookie("token", our_token, httponly=True, samesite="lax")
    return resp

# --- 인증된 사용자 API ---

def get_current_user(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = find_user_by_id(decoded['userId'])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/profile")
def profile(user = Depends(get_current_user)):
    return {
        "id": user["id"],
        "provider": user["provider"],
        "email": user["email"],
        "name": user["name"],
        "picture": user["picture"],
        "created_at": user["created_at"]
    }

# --- 로그아웃 API ---
@app.post("/logout")
def logout(response: Response):
    response.delete_cookie("token")
    return {"message": "Logged out"}

from fastapi.responses import RedirectResponse

@app.get("/")
async def root():
    return RedirectResponse(url="/docs")
