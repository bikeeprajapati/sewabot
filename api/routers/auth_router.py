import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from api.database import get_db
from api.models import User, Worker
from api.schemas import RegisterRequest, LoginRequest, TokenResponse, WorkerRegisterExtra, RefreshRequest
from api.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── REGISTER ─────────────────────────────────────────────
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new client or worker.
    Workers are created with is_verified=False — admin must approve.
    """

    # Check email not already taken
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered. Please login."
        )

    # Create user
    user = User(
        id            = str(uuid.uuid4()),
        email         = request.email,
        password_hash = hash_password(request.password),
        role          = request.role,
        full_name     = request.full_name,
        phone         = request.phone,
        is_active     = True
    )
    db.add(user)
    db.commit() 
    db.refresh(user)


    return {
        "message":   f"Account created successfully. Welcome to SewaBot, {user.full_name}!",
        "user_id":   user.id,
        "role":      user.role,
        "next_step": "POST /auth/login to get your access token"
    }


# ── REGISTER WORKER PROFILE ──────────────────────────────
@router.post("/register/worker-profile", status_code=status.HTTP_201_CREATED)
def register_worker_profile(
    user_id: str,
    extra: WorkerRegisterExtra,
    db: Session = Depends(get_db)
):
    """
    Step 2 for workers — add skills, rate, and location after account creation.
    """
    user = db.query(User).filter(User.id == user_id, User.role == "worker").first()
    if not user:
        raise HTTPException(status_code=404, detail="Worker account not found")

    existing = db.query(Worker).filter(Worker.user_id == user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Worker profile already exists")

    point = from_shape(Point(extra.lng, extra.lat), srid=4326)

    worker = Worker(
        id            = str(uuid.uuid4()),
        user_id       = user_id,
        skill_tags    = extra.skill_tags,
        hourly_rate   = extra.hourly_rate,
        bio           = extra.bio,
        location      = point,
        is_available  = True,
        is_verified   = False   # admin must approve
    )
    db.add(worker)
    db.commit()

    return {
        "message": "Worker profile created. Pending admin verification.",
        "worker_id": worker.id
    }


# ── LOGIN ────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email + password.
    Returns access token (15min) + refresh token (7 days).
    """

    # Find user
    user = db.query(User).filter(User.email == request.email).first()

    # Verify password — same error for both wrong email and wrong password
    # (security: don't reveal which one is wrong)
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact support."
        )

    # Create tokens
    token_data = {
        "user_id":   user.id,
        "email":     user.email,
        "role":      user.role,
        "full_name": user.full_name
    }

    return TokenResponse(
        access_token  = create_access_token(token_data),
        refresh_token = create_refresh_token(token_data),
        role          = user.role,
        full_name     = user.full_name
    )


# ── REFRESH TOKEN ────────────────────────────────────────
@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):
    """
    Get a new access token using a valid refresh token.
    Called automatically by the frontend when access token expires.
    """
    payload = decode_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token. Please login again."
        )

    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token_data = {
        "user_id":   user.id,
        "email":     user.email,
        "role":      user.role,
        "full_name": user.full_name
    }

    return TokenResponse(
        access_token  = create_access_token(token_data),
        refresh_token = create_refresh_token(token_data),
        role          = user.role,
        full_name     = user.full_name
    )


# ── PROTECTED DEPENDENCY (reusable) ─────────────────────
def get_current_user(
    token: str,
    db:    Session = Depends(get_db)
) -> User:
    """
    Reusable FastAPI dependency.
    Add to any endpoint that requires login:
    current_user: User = Depends(get_current_user)
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login again."
        )

    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user