"""JWT token creation/verification and password hashing."""

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import RefreshToken, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    # iat 必须存在：没有 iat 时同一秒内生成的 token 完全相同，
    # refresh 轮换会撞 refresh_tokens.token_hash 的 UNIQUE 约束
    to_encode.update({"iat": now, "exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    # jti（uuid4 随机）+ iat：refresh token 必须每次唯一。仅 iat 不够——
    # 同秒内 login 与 refresh 轮换会生成相同 token，撞 refresh_tokens.token_hash
    # 的 UNIQUE 约束（实测复现）。jti 保证轮换安全（也防重放）。
    to_encode.update({"iat": now, "exp": expire, "type": "refresh", "jti": uuid4().hex})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def store_refresh_token(db: AsyncSession, user_id: int, raw_token: str) -> None:
    """Store hashed refresh token in DB."""
    expires = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            expires_at=expires,
        )
    )
    await db.commit()


async def revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    """Revoke a refresh token by its hash."""
    token_hash = hash_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
        )
    )
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked = True
        await db.commit()


async def rotate_refresh_token(
    db: AsyncSession, old_raw: str, user_id: int
) -> str:
    """Revoke old refresh token, issue and store a new one."""
    await revoke_refresh_token(db, old_raw)
    new_token = create_refresh_token({"sub": str(user_id)})
    await store_refresh_token(db, user_id, new_token)
    return new_token


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user
