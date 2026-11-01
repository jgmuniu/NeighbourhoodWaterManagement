from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, func, text

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / "desktop"
sys.path.insert(0, str(DESKTOP))

from database import SessionLocal, initialize_database, engine
from models import Household, Meter, Reading, BillingPeriod, Bill, Payment, PaymentAllocation, AuditLog, User, SyncRequest
import services

APP_SECRET = os.getenv("NWM_API_SECRET", "")
TOKEN_MINUTES = int(os.getenv("NWM_TOKEN_MINUTES", "720"))

app = FastAPI(title="Neighbourhood Water Management API", version="0.6.0", description="Local-network and internet API for the Neighbourhood Water Management system.")
origins = [x.strip() for x in os.getenv("NWM_CORS_ORIGINS", "http://localhost,http://127.0.0.1").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type", "X-Idempotency-Key", "X-Device-Id"])

@app.on_event("startup")
def startup():
    initialize_database()


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def token_for(user: dict) -> str:
    if not APP_SECRET:
        raise HTTPException(503, "Set NWM_API_SECRET before starting the API. See backend/.env.example.")
    now = int(time.time())
    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64(json.dumps({"sub": user["username"], "uid": user["id"], "role": user["role"], "iat": now, "exp": now + TOKEN_MINUTES * 60}, separators=(",", ":")).encode())
    signing = f"{header}.{payload}".encode()
    signature = b64(hmac.new(APP_SECRET.encode(), signing, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required.")
    try:
        header, payload, signature = authorization[7:].split(".")
        expected = b64(hmac.new(APP_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not APP_SECRET or not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(data["exp"]) < int(time.time()):
            raise ValueError("expired")
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.id == int(data["uid"]), User.active.is_(True)))
            if not user:
                raise ValueError("inactive")
            return {"id": user.id, "username": user.username, "role": user.role}
    except Exception:
        raise HTTPException(401, "Invalid or expired access token.")


def require_roles(*roles):
    def check(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "Your account does not have permission for this action.")
        return user
    return check


class LoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1, max_length=256)

class HouseholdInput(BaseModel):
    house_number: str = Field(min_length=1, max_length=50)
    owner_name: str = ""
    tenant_name: str = ""
    phone: str = ""
    location: str = ""

class ReadingInput(BaseModel):
    meter_id: int
    period: str = Field(min_length=1, max_length=30)
    previous_value: Decimal = Field(ge=0)
    current_value: Decimal = Field(ge=0)

class PaymentInput(BaseModel):
    household_id: int
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    method: str = Field(min_length=1, max_length=30)
    reference: str = Field(default="", max_length=100)
    paid_on: date

class SyncPushInput(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    changes: list[dict] = Field(default_factory=list, max_length=500)


@app.get("/health")
def health():
    return {"status": "ok", "service": "Neighbourhood Water Management API", "version": app.version, "time": datetime.now(timezone.utc).isoformat()}

@app.get("/health/ready")
def readiness():
    """Readiness probe: confirms the API can reach its configured database."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "database": "reachable", "version": app.version}
    except Exception as exc:
        raise HTTPException(503, {"status": "not_ready", "database": "unavailable", "detail": str(exc)[:300]})

@app.post("/auth/login")
def login(payload: LoginInput):
    user = services.authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(401, "Incorrect username or password.")
    return {"access_token": token_for(user), "token_type": "bearer", "expires_in": TOKEN_MINUTES * 60, "user": user}

@app.get("/auth/me")
def me(user=Depends(current_user)):
    return user

@app.get("/households")
def households(active: Optional[bool] = None, user=Depends(current_user)):
    with SessionLocal() as db:
        stmt = select(Household).order_by(Household.house_number)
        if active is not None:
            stmt = stmt.where(Household.active.is_(active))
        rows = db.scalars(stmt).all()
        return [{"id": x.id, "house_number": x.house_number, "owner_name": x.owner_name, "tenant_name": x.tenant_name, "phone": x.phone, "location": x.location, "active": x.active} for x in rows]

@app.post("/households", status_code=201)
def add_household(payload: HouseholdInput, user=Depends(require_roles("Administrator", "Operator"))):
    try:
        item_id = services.add_household(payload.house_number, payload.owner_name, payload.tenant_name, payload.phone, payload.location)
        services.audit(user["username"], "API_HOUSEHOLD_CREATED", "Household", item_id, payload.house_number)
        return {"id": item_id, "message": "Household created."}
    except Exception as exc:
        raise HTTPException(400, str(exc))

@app.get("/meters")
def meters(household_id: Optional[int] = None, user=Depends(current_user)):
    with SessionLocal() as db:
        stmt = select(Meter).order_by(Meter.serial_number)
        if household_id is not None:
            stmt = stmt.where(Meter.household_id == household_id)
        return [{"id": x.id, "serial_number": x.serial_number, "meter_type": x.meter_type, "household_id": x.household_id, "active": x.active, "installed_on": x.installed_on} for x in db.scalars(stmt).all()]

@app.get("/billing-periods")
def billing_periods(user=Depends(current_user)):
    with SessionLocal() as db:
        rows = db.scalars(select(BillingPeriod).order_by(BillingPeriod.start_date.desc())).all()
        return [{"id": x.id, "name": x.name, "start_date": x.start_date, "end_date": x.end_date, "due_date": x.due_date, "status": x.status} for x in rows]

@app.get("/readings")
def readings(period: Optional[str] = None, user=Depends(current_user)):
    with SessionLocal() as db:
        stmt = select(Reading).order_by(Reading.recorded_at.desc())
        if period:
            stmt = stmt.where(Reading.period == period)
        return [{"id": x.id, "meter_id": x.meter_id, "period": x.period, "previous_value": str(x.previous_value), "current_value": str(x.current_value), "consumption": str(x.consumption), "recorded_at": x.recorded_at, "recorded_by": x.recorded_by, "approved": x.approved} for x in db.scalars(stmt.limit(1000)).all()]

@app.post("/readings", status_code=201)
def add_reading(payload: ReadingInput, user=Depends(require_roles("Administrator", "Operator"))):
    try:
        consumption = services.record_reading(payload.meter_id, payload.period, payload.previous_value, payload.current_value, user["username"])
        with SessionLocal() as db:
            row = db.scalar(select(Reading).where(Reading.meter_id == payload.meter_id, Reading.period == payload.period))
            return {"id": row.id, "consumption": str(consumption)}
    except Exception as exc:
        raise HTTPException(400, str(exc))

@app.get("/bills")
def bills(household_id: Optional[int] = None, period: Optional[str] = None, user=Depends(current_user)):
    with SessionLocal() as db:
        stmt = select(Bill).order_by(Bill.created_at.desc())
        if household_id is not None:
            stmt = stmt.where(Bill.household_id == household_id)
        if period:
            stmt = stmt.where(Bill.period == period)
        rows = db.scalars(stmt.limit(2000)).all()
        return [{"id": x.id, "bill_number": x.bill_number, "household_id": x.household_id, "period": x.period, "consumption": str(x.consumption), "unit_price": str(x.unit_price), "water_charge": str(x.water_charge), "arrears": str(x.arrears), "total_due": str(x.total_due), "due_date": x.due_date, "status": x.status} for x in rows]

@app.get("/households/{household_id}/account")
def account(household_id: int, user=Depends(current_user)):
    try:
        return services.household_account(household_id)
    except Exception as exc:
        raise HTTPException(404, str(exc))

@app.post("/payments", status_code=201)
def make_payment(payload: PaymentInput, user=Depends(require_roles("Administrator", "Operator"))):
    try:
        result = services.record_household_payment(payload.household_id, payload.amount, payload.method, payload.reference, payload.paid_on, user["username"])
        return result
    except Exception as exc:
        raise HTTPException(400, str(exc))

@app.get("/sync/pull")
def sync_pull(after_id: int = Query(default=0, ge=0), limit: int = Query(default=500, ge=1, le=1000), user=Depends(current_user)):
    """Return audit-backed change notifications. Clients fetch canonical records via normal GET endpoints."""
    with SessionLocal() as db:
        rows = db.scalars(select(AuditLog).where(AuditLog.id > after_id).order_by(AuditLog.id).limit(limit)).all()
        return {"changes": [{"cursor": x.id, "entity_type": x.entity_type, "entity_id": x.entity_id, "action": x.action, "changed_at": x.created_at, "actor": x.username} for x in rows], "next_cursor": rows[-1].id if rows else after_id, "has_more": len(rows) == limit}

def _idempotent_write(request_key: str, device_id: str, entity_type: str, payload: dict, actor: str, operation):
    if not request_key or len(request_key) > 120:
        raise HTTPException(400, "A valid X-Idempotency-Key header is required (1–120 characters).")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    with SessionLocal() as db:
        existing = db.get(SyncRequest, request_key)
        if existing:
            if existing.payload_hash != digest or existing.entity_type != entity_type:
                raise HTTPException(409, "This idempotency key was already used for a different request.")
            if existing.status == "completed":
                return json.loads(existing.response_json)
            if existing.status == "processing":
                raise HTTPException(409, "This request is still processing. Check its status before retrying.")
            raise HTTPException(409, "The earlier attempt did not complete cleanly. Administrator review is required before retrying.")
        db.add(SyncRequest(request_key=request_key, device_id=device_id, entity_type=entity_type,
                           payload_hash=digest, status="processing"))
        db.commit()
    try:
        result = operation()
        response = {"status": "completed", "change_id": request_key, "result": result}
        with SessionLocal() as db:
            row = db.get(SyncRequest, request_key)
            row.status = "completed"
            row.response_json = json.dumps(response, default=str)
            row.updated_at = datetime.now()
            db.add(AuditLog(username=actor, action="SYNC_CHANGE_APPLIED", entity_type=entity_type,
                            entity_id=request_key, details=f"Device {device_id}; idempotent write completed"))
            db.commit()
        return response
    except HTTPException:
        raise
    except Exception as exc:
        with SessionLocal() as db:
            row = db.get(SyncRequest, request_key)
            if row:
                row.status = "review_required"
                row.error_message = str(exc)[:2000]
                row.updated_at = datetime.now()
                db.commit()
        raise HTTPException(400, str(exc))


@app.post("/sync/readings", status_code=200)
def sync_reading(payload: ReadingInput, x_idempotency_key: str = Header(default=""),
                 x_device_id: str = Header(default="unknown-device"),
                 user=Depends(require_roles("Administrator", "Operator"))):
    def apply():
        consumption = services.record_reading(payload.meter_id, payload.period, payload.previous_value,
                                              payload.current_value, user["username"])
        with SessionLocal() as db:
            row = db.scalar(select(Reading).where(Reading.meter_id == payload.meter_id,
                                                  Reading.period == payload.period))
            return {"reading_id": row.id, "consumption": str(consumption)}
    return _idempotent_write(x_idempotency_key, x_device_id, "reading", payload.model_dump(mode="json"), user["username"], apply)


@app.post("/sync/payments", status_code=200)
def sync_payment(payload: PaymentInput, x_idempotency_key: str = Header(default=""),
                 x_device_id: str = Header(default="unknown-device"),
                 user=Depends(require_roles("Administrator", "Operator"))):
    def apply():
        result = services.record_household_payment(payload.household_id, payload.amount, payload.method,
                                                   payload.reference, payload.paid_on, user["username"])
        return result
    return _idempotent_write(x_idempotency_key, x_device_id, "payment", payload.model_dump(mode="json"), user["username"], apply)


@app.get("/sync/requests/{request_key}")
def sync_request_status(request_key: str, user=Depends(current_user)):
    with SessionLocal() as db:
        row = db.get(SyncRequest, request_key)
        if not row:
            raise HTTPException(404, "Sync request not found.")
        return {"change_id": row.request_key, "device_id": row.device_id, "entity_type": row.entity_type,
                "status": row.status, "result": json.loads(row.response_json),
                "error": row.error_message, "created_at": row.created_at, "updated_at": row.updated_at}


@app.get("/sync/status")
def sync_status(user=Depends(require_roles("Administrator"))):
    with SessionLocal() as db:
        rows = db.scalars(select(SyncRequest).order_by(SyncRequest.updated_at.desc()).limit(100)).all()
        counts = {state: db.scalar(select(func.count(SyncRequest.request_key)).where(SyncRequest.status == state)) or 0
                  for state in ("processing", "completed", "review_required")}
        return {"counts": counts, "recent": [{"change_id": x.request_key, "device_id": x.device_id,
                "entity_type": x.entity_type, "status": x.status, "error": x.error_message,
                "updated_at": x.updated_at} for x in rows]}


@app.post("/sync/push")
def sync_push(payload: SyncPushInput, user=Depends(require_roles("Administrator", "Operator"))):
    raise HTTPException(410, "Acknowledgement-only sync has been retired. Submit readings to /sync/readings and payments to /sync/payments with X-Idempotency-Key.")
