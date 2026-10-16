"""
Minimal auth router. Users are stored in Mongo's `users` collection; if
Mongo isn't reachable (e.g. running the frontend-only demo) these endpoints
will raise a clear connection error rather than failing silently — search
and document endpoints do not depend on auth being configured.
"""
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import create_access_token, get_current_user_claims, hash_password, verify_password
from app.db.mongo import get_db
from app.models.user import UserPublic
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> TokenResponse:
    db = get_db()
    existing = await db.users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")

    doc = {
        "email": payload.email,
        "full_name": payload.full_name,
        "role": payload.role.value,
        "organization": payload.organization,
        "hashed_password": hash_password(payload.password),
        "is_active": True,
    }
    result = await db.users.insert_one(doc)
    user_public = UserPublic(id=str(result.inserted_id), **{k: v for k, v in doc.items() if k != "hashed_password"})
    token = create_access_token(subject=str(result.inserted_id), extra_claims={"role": payload.role.value})
    return TokenResponse(access_token=token, user=user_public)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    db = get_db()
    user = await db.users.find_one({"email": payload.email})
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")

    user_public = UserPublic(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        organization=user.get("organization"),
    )
    token = create_access_token(subject=str(user["_id"]), extra_claims={"role": user["role"]})
    return TokenResponse(access_token=token, user=user_public)


@router.get("/me", response_model=UserPublic)
async def me(claims: dict = Depends(get_current_user_claims)) -> UserPublic:
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(claims["sub"])})
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return UserPublic(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        organization=user.get("organization"),
    )
