"""Auth endpoints: register, login, refresh, me."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    rotate_refresh_token,
    store_refresh_token,
)
from app.models.models import Doctor, Patient, RefreshToken, Therapist, User
from app.schemas.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a new user with role selection."""
    # Check username uniqueness
    existing = (
        await db.execute(select(User).where(User.username == body.username))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Create user
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
        display_name=body.display_name,
    )
    db.add(user)
    await db.flush()

    # Create role-specific profile
    if body.role == "therapist":
        db.add(
            Therapist(
                user_id=user.id,
                name=body.display_name,
                group_name="PT",  # default; admin can change later
            )
        )
    elif body.role == "doctor":
        db.add(Doctor(user_id=user.id, name=body.display_name))
    elif body.role == "patient":
        db.add(Patient(user_id=user.id, name=body.display_name))

    await db.commit()

    return {"message": "User registered", "user_id": user.id}


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticate and return access + refresh tokens."""
    user = await authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    await store_refresh_token(db, user.id, refresh_token)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Return current user info."""
    return current_user


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    raw_token = body.refresh_token

    try:
        payload = decode_token(raw_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token type must be 'refresh'",
        )

    user_id = int(payload["sub"])

    # Verify refresh token exists and is not revoked
    token_hash = hash_token(raw_token)

    rt = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,  # noqa: E712
            )
        )
    ).scalar_one_or_none()

    if not rt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or not found",
        )

    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_access = create_access_token({"sub": str(user.id), "role": user.role})
    new_refresh = await rotate_refresh_token(db, raw_token, user.id)

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)
