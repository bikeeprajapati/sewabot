import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# ── Config ───────────────────────────────────────────────
SECRET_KEY   = os.getenv("SECRET_KEY", "sewabot-secret-change-in-production")
ALGORITHM    = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES  = 15
REFRESH_TOKEN_EXPIRE_DAYS    = 7

# ── Password hashing ─────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Convert plain password to bcrypt hash."""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Check plain password against stored hash."""
    return pwd_context.verify(plain, hashed)

# ── JWT tokens ───────────────────────────────────────────
def create_access_token(data: dict) -> str:
    """
    Create short-lived access token (15 min).
    Used for every API request.
    """
    payload = data.copy()
    payload["exp"]  = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["type"] = "access"
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """
    Create long-lived refresh token (7 days).
    Used only to get a new access token when it expires.
    """
    payload = data.copy()
    payload["exp"]  = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload["type"] = "refresh"
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.
    Returns the payload dict or None if invalid/expired.
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None