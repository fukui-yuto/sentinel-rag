import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.session import get_db
from src.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_TTL = timedelta(hours=8)
JWT_ALGORITHM = "HS256"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    display_name: str
    role: str

    model_config = {"from_attributes": True}


def create_access_token(user_id: str, tenant_id: str, role: str) -> tuple[str, datetime]:
    """Create a JWT access token."""
    expires = datetime.now(timezone.utc) + SESSION_TTL
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expires,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)
    return token, expires


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate user from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Check Redis session blacklist
    try:
        r = aioredis.from_url(settings.redis_url)
        jti = payload.get("jti", "")
        if await r.get(f"session:revoked:{jti}"):
            await r.aclose()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked")
        await r.aclose()
    except Exception:
        pass

    # Set RLS tenant context (validate UUID format to prevent SQL injection)
    tenant_id = payload.get("tenant_id")
    if tenant_id:
        validated_tid = str(uuid.UUID(tenant_id))  # raises ValueError if not a valid UUID
        from sqlalchemy import text

        await db.execute(text(f"SET LOCAL app.current_tenant_id = '{validated_tid}'"))

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


@router.get("/login")
async def login_redirect() -> dict[str, str]:
    """Redirect to SSO provider. In production, this returns the OIDC auth URL."""
    if not settings.oidc_issuer_url:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OIDC not configured. Use /auth/dev-login in development.",
        )
    auth_url = f"{settings.oidc_issuer_url}/protocol/openid-connect/auth"
    return {"redirect_url": auth_url, "client_id": settings.oidc_client_id}


@router.post("/dev-login", response_model=TokenResponse)
async def dev_login(
    email: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Development-only login by email (no password). Disabled in production."""
    if not settings.is_development:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not available")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    token, expires = create_access_token(
        str(user.id), str(user.tenant_id), user.role
    )
    return TokenResponse(
        access_token=token,
        expires_in=int(SESSION_TTL.total_seconds()),
    )


@router.post("/logout")
async def logout(request: Request, user: User = Depends(get_current_user)) -> dict[str, str]:
    """Revoke current session."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.split(" ", 1)[1] if " " in auth_header else ""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
        jti = payload.get("jti", "")
        r = aioredis.from_url(settings.redis_url)
        await r.setex(f"session:revoked:{jti}", int(SESSION_TTL.total_seconds()), "1")
        await r.aclose()
    except Exception:
        pass
    return {"status": "logged_out"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> User:
    """Get current user info."""
    return user
