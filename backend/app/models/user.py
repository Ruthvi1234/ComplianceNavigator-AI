from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    ADMIN = "admin"
    AUDITOR = "auditor"
    COMPLIANCE_OFFICER = "compliance_officer"
    INDUSTRY_USER = "industry_user"


class UserInDB(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    organization: str | None = None
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    organization: str | None = None
