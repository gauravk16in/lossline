"""Organization-admin provisioning APIs."""
from __future__ import annotations

import datetime
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.security import UserContext, decode_clerk_token, hash_ingestion_secret, require_admin
from src.db.models import IntegrationCredential, Organization, Restaurant
from src.db.session import get_db_session

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

class OrganizationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)

class OutletPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outlet_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    timezone: str = "UTC"
    currency: str = "INR"

class IntegrationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allowed_outlet_ids: tuple[str, ...]

@router.post("/organizations", status_code=201)
async def register_organization(payload: OrganizationPayload,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db_session)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Clerk bearer token required")
    claims = decode_clerk_token(authorization[7:]); org = claims.get("o") or {}
    clerk_id = claims.get("org_id") or org.get("id"); role = claims.get("org_role") or org.get("rol")
    if not clerk_id or role != "org:admin":
        raise HTTPException(status_code=403, detail="Active organization administrator required")
    existing = (await db.execute(select(Organization).where(Organization.clerk_organization_id == clerk_id))).scalars().first()
    if existing: return existing
    row = Organization(clerk_organization_id=clerk_id, name=payload.name.strip()); db.add(row); await db.flush()
    return row

@router.put("/outlets/{outlet_id}")
async def upsert_outlet(outlet_id: str, payload: OutletPayload,
    user: UserContext = Depends(require_admin), db: AsyncSession = Depends(get_db_session)):
    if outlet_id != payload.outlet_id: raise HTTPException(status_code=422, detail="Outlet IDs must match")
    row = await db.get(Restaurant, outlet_id)
    if row is not None and row.organization_id != user.organization_id:
        raise HTTPException(status_code=404, detail="Outlet not found")
    if row is None:
        row = Restaurant(id=outlet_id, organization_id=user.organization_id, synthetic=False); db.add(row)
    row.name, row.timezone, row.currency = payload.name, payload.timezone, payload.currency
    await db.flush(); return row

@router.post("/integrations", status_code=201)
async def issue_integration(payload: IntegrationPayload, user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)):
    allowed = set(payload.allowed_outlet_ids)
    owned = set((await db.execute(select(Restaurant.id).where(Restaurant.organization_id == user.organization_id,
        Restaurant.id.in_(allowed)))).scalars().all()) if allowed else set()
    if allowed != owned: raise HTTPException(status_code=422, detail="Every allowed outlet must belong to the active organization")
    prefix, secret = f"lli_{secrets.token_hex(4)}", secrets.token_urlsafe(32)
    row = IntegrationCredential(public_prefix=prefix, secret_hash=hash_ingestion_secret(secret),
        organization_id=user.organization_id, allowed_outlet_ids=sorted(allowed)); db.add(row); await db.flush()
    return {"integration_id": row.id, "credential": f"{prefix}.{secret}", "allowed_outlet_ids": sorted(allowed)}

@router.post("/integrations/{integration_id}/revoke")
async def revoke_integration(integration_id: int, user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)):
    row = (await db.execute(select(IntegrationCredential).where(IntegrationCredential.id == integration_id,
        IntegrationCredential.organization_id == user.organization_id))).scalars().first()
    if row is None: raise HTTPException(status_code=404, detail="Integration not found")
    row.revoked_at = datetime.datetime.now(datetime.timezone.utc); return {"status": "revoked"}
