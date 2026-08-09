"""Clerk user sessions and scoped machine-ingestion credentials."""

from __future__ import annotations

import datetime
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Annotated, Literal

import jwt
from fastapi import Depends, Header, HTTPException, Request, Response
from jwt import PyJWKClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models import IntegrationCredential, Organization, RateLimitBucket
from src.db.session import get_db_session


@dataclass(frozen=True)
class UserContext:
    subject: str
    clerk_organization_id: str
    organization_id: int
    role: Literal["org:member", "org:admin"]


@dataclass(frozen=True)
class IngestionContext:
    credential_id: int
    organization_id: int
    allowed_outlet_ids: frozenset[str]
    public_prefix: str


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def decode_clerk_token(token: str) -> dict:
    if not settings.CLERK_ISSUER or not settings.CLERK_JWKS_URL:
        raise HTTPException(status_code=503, detail="Clerk authentication is not configured")
    try:
        key = PyJWKClient(settings.CLERK_JWKS_URL).get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], issuer=settings.CLERK_ISSUER,
            options={"require": ["exp", "iss", "sub"]})
    except jwt.PyJWTError as exc:
        raise _unauthorized("Invalid or expired Clerk session") from exc
    parties = {item.strip() for item in settings.CLERK_AUTHORIZED_PARTIES.split(",") if item.strip()}
    if parties and claims.get("azp") not in parties:
        raise _unauthorized("Clerk token authorized party is not allowed")
    return claims


async def _limit(db: AsyncSession, *, key: str, limit: int, response: Response) -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    window = now.replace(second=0, microsecond=0)
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        result = await db.execute(text("""
            INSERT INTO rate_limit_buckets (bucket_key, window_start, request_count)
            VALUES (:key, :window, 1)
            ON CONFLICT (bucket_key) DO UPDATE SET
              window_start = CASE WHEN rate_limit_buckets.window_start = :window THEN rate_limit_buckets.window_start ELSE :window END,
              request_count = CASE WHEN rate_limit_buckets.window_start = :window THEN rate_limit_buckets.request_count + 1 ELSE 1 END
            RETURNING request_count
        """), {"key": key, "window": window})
        count = int(result.scalar_one())
    else:
        row = await db.get(RateLimitBucket, key)
        if row is None:
            row = RateLimitBucket(bucket_key=key, window_start=window, request_count=1); db.add(row)
        elif row.window_start.replace(tzinfo=datetime.timezone.utc) != window:
            row.window_start, row.request_count = window, 1
        else:
            row.request_count += 1
        count = row.request_count
        await db.flush()
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
    if count > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": "60"})


async def require_user(
    request: Request, response: Response,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db_session),
) -> UserContext:
    if not settings.SERVERLESS_MODE:
        # Local protected-demo compatibility without weakening production.
        return UserContext("local_manager", "local_demo", 0, "org:admin")
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized("Clerk bearer token required")
    claims = decode_clerk_token(authorization[7:])
    org = claims.get("o") or {}
    clerk_org_id = claims.get("org_id") or org.get("id")
    role = claims.get("org_role") or org.get("rol")
    if not clerk_org_id or role not in {"org:member", "org:admin"}:
        raise HTTPException(status_code=403, detail="An active Clerk organization and supported role are required")
    organization = (await db.execute(select(Organization).where(
        Organization.clerk_organization_id == clerk_org_id))).scalars().first()
    if organization is None:
        raise HTTPException(status_code=403, detail="Active organization is not registered in LOSSLine")
    await _limit(db, key=f"user:read:{claims['sub']}", limit=settings.READ_RATE_LIMIT, response=response)
    request.state.auth_subject = claims["sub"]
    request.state.organization_id = organization.id
    return UserContext(claims["sub"], clerk_org_id, organization.id, role)


async def require_manager(response: Response, user: UserContext = Depends(require_user),
    db: AsyncSession = Depends(get_db_session)) -> UserContext:
    await _limit(db, key=f"user:write:{user.subject}", limit=settings.WRITE_RATE_LIMIT, response=response)
    return user


async def require_admin(response: Response, user: UserContext = Depends(require_user),
    db: AsyncSession = Depends(get_db_session)) -> UserContext:
    if user.role != "org:admin":
        raise HTTPException(status_code=403, detail="Organization administrator role required")
    await _limit(db, key=f"user:admin:{user.subject}", limit=settings.ADMIN_RATE_LIMIT, response=response)
    return user


def hash_ingestion_secret(secret: str) -> str:
    if not settings.CREDENTIAL_PEPPER:
        raise HTTPException(status_code=503, detail="Credential pepper is not configured")
    return hmac.new(settings.CREDENTIAL_PEPPER.encode(), secret.encode(), hashlib.sha256).hexdigest()


async def require_ingestion(
    response: Response,
    supplied: Annotated[str | None, Header(alias="X-LOSSLine-Key")] = None,
    db: AsyncSession = Depends(get_db_session),
) -> IngestionContext:
    if not settings.SERVERLESS_MODE:
        if not settings.INGEST_API_KEY or supplied is None or not secrets.compare_digest(supplied, settings.INGEST_API_KEY):
            raise _unauthorized("Valid ingest API key required")
        return IngestionContext(0, 0, frozenset(), "local")
    if not supplied or "." not in supplied:
        raise _unauthorized("Valid ingestion credential required")
    prefix, secret = supplied.split(".", 1)
    row = (await db.execute(select(IntegrationCredential).where(
        IntegrationCredential.public_prefix == prefix))).scalars().first()
    if row is None or row.revoked_at is not None or not secrets.compare_digest(row.secret_hash, hash_ingestion_secret(secret)):
        raise _unauthorized("Valid ingestion credential required")
    await _limit(db, key=f"integration:{row.id}", limit=settings.EVENT_RATE_LIMIT, response=response)
    return IngestionContext(row.id, row.organization_id, frozenset(row.allowed_outlet_ids), prefix)


# Compatibility names used by local-only routes.
require_ingest_key = require_ingestion
require_manager_key = require_manager
require_admin_key = require_admin
