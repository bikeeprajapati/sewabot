from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime

# ── Auth schemas ─────────────────────────────────────────
class RegisterRequest(BaseModel):
    full_name: str
    email:     EmailStr
    password:  str
    role:      str        # "client" or "worker"
    phone:     Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("role")
    @classmethod
    def role_valid(cls, v):
        if v not in ["client", "worker"]:
            raise ValueError("Role must be 'client' or 'worker'")
        return v

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip()


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    role:          str
    full_name:     str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Worker schemas ───────────────────────────────────────
class WorkerRegisterExtra(BaseModel):
    """Extra info required when registering as a worker."""
    skill_tags:  List[str]
    hourly_rate: int
    bio:         Optional[str] = None
    lat:         float
    lng:         float

    @field_validator("hourly_rate")
    @classmethod
    def rate_positive(cls, v):
        if v < 100:
            raise ValueError("Hourly rate must be at least Rs. 100")
        if v > 10000:
            raise ValueError("Hourly rate cannot exceed Rs. 10,000")
        return v

    @field_validator("skill_tags")
    @classmethod
    def skills_not_empty(cls, v):
        if not v:
            raise ValueError("At least one skill tag is required")
        return v


# ── User response ────────────────────────────────────────
class UserOut(BaseModel):
    id:         str
    email:      str
    full_name:  str
    role:       str
    created_at: datetime

    class Config:
        from_attributes = True