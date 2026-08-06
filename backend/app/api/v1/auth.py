"""Auth endpoints: register, login, refresh, me, logout, password reset/change."""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
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
    hash_token,
    revoke_refresh_token,
    rotate_refresh_token,
    store_refresh_token,
    verify_password,
)
from app.models.models import (
    Doctor,
    Patient,
    PasswordResetCode,
    RefreshToken,
    Therapist,
    User,
)
from app.schemas.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetCodeResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

logger = logging.getLogger("rehabflow.auth")
RESET_CODE_TTL_SECONDS = 300  # 验证码有效期 5 分钟

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
        phone=body.phone,
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


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """注销：撤销 refresh token（幂等——token 不存在/已撤销也返回成功）。"""
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        return {"message": "Logged out"}

    if payload.get("type") == "refresh":
        await revoke_refresh_token(db, body.refresh_token)

    return {"message": "Logged out"}


@router.post("/password-reset/request", response_model=PasswordResetCodeResponse)
async def password_reset_request(
    body: PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """忘记密码①：按手机号生成 6 位验证码（有效期 5 分钟）。

    院内系统暂无短信通道：验证码写入日志 + dev_code 字段返回。
    生产接入短信服务商后，改为短信下发并移除 dev_code。
    """
    # 手机号必须对应已注册用户（不泄露"该手机号是否存在"——统一提示）
    user = (
        await db.execute(select(User).where(User.phone == body.phone))
    ).scalar_one_or_none()
    if not user:
        logger.info("password reset requested for unregistered phone %s", body.phone)

    # 作废该手机号旧的未使用验证码（防堆积）
    now = datetime.now(timezone.utc)
    old_codes = (
        await db.execute(
            select(PasswordResetCode).where(
                PasswordResetCode.phone == body.phone,
                PasswordResetCode.used == False,  # noqa: E712
                PasswordResetCode.expires_at > now,
            )
        )
    ).scalars().all()
    for c in old_codes:
        c.used = True

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        PasswordResetCode(
            phone=body.phone,
            code_hash=hashlib.sha256(code.encode()).hexdigest(),
            expires_at=now + timedelta(seconds=RESET_CODE_TTL_SECONDS),
        )
    )
    await db.commit()

    logger.warning("密码重置验证码 phone=%s code=%s（5 分钟内有效）", body.phone, code)
    return PasswordResetCodeResponse(
        message="验证码已发送",
        expires_in=RESET_CODE_TTL_SECONDS,
        dev_code=code,  # TODO: 接入短信服务后移除
    )


@router.post("/password-reset/confirm")
async def password_reset_confirm(
    body: PasswordResetConfirm,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """忘记密码②：验证码校验 + 重置密码。"""
    now = datetime.now(timezone.utc)
    code_hash = hashlib.sha256(body.code.encode()).hexdigest()

    record = (
        await db.execute(
            select(PasswordResetCode).where(
                PasswordResetCode.phone == body.phone,
                PasswordResetCode.code_hash == code_hash,
                PasswordResetCode.used == False,  # noqa: E712
                PasswordResetCode.expires_at > now,
            )
        )
    ).scalars().first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期",
        )

    user = (
        await db.execute(select(User).where(User.phone == body.phone))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="手机号未注册",
        )

    # 重置密码 + 标记验证码已用 + 撤销该用户全部 refresh token（强制重新登录）
    user.password_hash = hash_password(body.new_password)
    record.used = True
    await db.execute(
        RefreshToken.__table__.update().where(
            RefreshToken.user_id == user.id, RefreshToken.revoked == False  # noqa: E712
        ).values(revoked=True)
    )
    await db.commit()

    logger.info("密码已重置 phone=%s user=%s", body.phone, user.username)
    return {"message": "密码重置成功，请重新登录"}


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """登录后修改密码：校验旧密码 → 更新新密码 → 撤销该用户全部 refresh token。"""
    if not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码不正确",
        )

    current_user.password_hash = hash_password(body.new_password)
    await db.execute(
        RefreshToken.__table__.update().where(
            RefreshToken.user_id == current_user.id, RefreshToken.revoked == False  # noqa: E712
        ).values(revoked=True)
    )
    await db.commit()

    logger.info("密码已修改 user=%s", current_user.username)
    return {"message": "密码修改成功，请重新登录"}
