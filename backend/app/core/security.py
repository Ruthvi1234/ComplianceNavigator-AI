"""
JWT issuance/verification and password hashing.

Kept deliberately free of FastAPI imports (except the dependency at the
bottom) so it can be unit tested in isolation.

Uses the `bcrypt` library directly rather than passlib. passlib's source
does an unconditional `from crypt import crypt` at import time (see
passlib/utils/__init__.py) to support a legacy hashing scheme this project
never uses - and Python 3.13 removed the stdlib `crypt` module entirely
(PEP 594), with no passlib release fixing this as of writing. That import
error would only show up on 3.13+, not on the 3.12 environment this was
built and tested against, so this was worth avoiding rather than pinning
around. Calling bcrypt directly for the one scheme actually used here is a
few lines, needs no legacy-compat shim, and works the same on 3.12 and 3.13.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user_claims(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    return decode_access_token(token)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user_claims(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    return decode_access_token(token)
