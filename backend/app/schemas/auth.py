from pydantic import BaseModel, EmailStr

from app.models.user import UserPublic, UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.INDUSTRY_USER
    organization: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
