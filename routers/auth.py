from datetime import datetime, timezone
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends, Request
from bson import ObjectId
from database import get_db
from models import LoginRequest, PhoneLoginRequest, TokenResponse, AddressIn
from auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

# Sin 25 fix: simple in-process rate limiter for phone login
# { phone: [timestamp, ...] } — max 5 attempts per 5 minutes
_login_attempts: dict = defaultdict(list)
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300


def _check_rate_limit(key: str):
    now = datetime.now(timezone.utc).timestamp()
    attempts = [t for t in _login_attempts[key] if now - t < _WINDOW_SECONDS]
    _login_attempts[key] = attempts
    if len(attempts) >= _MAX_ATTEMPTS:
        raise HTTPException(429, "Too many login attempts. Try again in 5 minutes.")
    _login_attempts[key].append(now)


@router.post("/login/admin", response_model=TokenResponse)
async def admin_login(body: LoginRequest):
    db = get_db()
    user = await db.admins.find_one({"email": body.email})
    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")
    token = create_token({"sub": str(user["_id"]), "role": "admin", "email": user["email"]})
    return TokenResponse(access_token=token, role="admin", name=user["name"], email=user["email"])


@router.post("/login/phone", response_model=TokenResponse)
async def phone_login(body: PhoneLoginRequest, request: Request):
    # Rate limit by IP + phone to prevent enumeration
    rate_key = f"{request.client.host}:{body.phone}"
    _check_rate_limit(rate_key)

    db = get_db()
    customer = await db.customers.find_one({"phone": body.phone})
    if not customer:
        raise HTTPException(401, "Access not granted")
    if not customer.get("isActive", True):
        raise HTTPException(401, "Account disabled")

    # Sin 26 fix: compare timezone-aware datetimes correctly
    access_until = customer.get("accessUntil")
    if access_until is not None:
        if access_until.tzinfo is None:
            access_until = access_until.replace(tzinfo=timezone.utc)
        if access_until < datetime.now(timezone.utc):
            raise HTTPException(401, "Access expired")

    token = create_token({"sub": str(customer["_id"]), "role": "user", "phone": customer["phone"]})
    return TokenResponse(
        access_token=token,
        role="user",
        name=customer.get("name") or customer["phone"],
        email=customer.get("email") or "",
        addresses=customer.get("addresses") or [],
    )


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    db = get_db()
    oid = ObjectId(user["sub"])
    if user["role"] == "admin":
        doc = await db.admins.find_one({"_id": oid})
        return {"role": "admin", "name": doc["name"], "email": doc["email"], "addresses": []}
    doc = await db.customers.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "User not found")
    return {
        "role": "user",
        "name": doc.get("name") or doc["phone"],
        "email": doc.get("email") or "",
        "addresses": doc.get("addresses") or [],
    }


@router.post("/addresses")
async def add_address(body: AddressIn, user: dict = Depends(get_current_user)):
    if user["role"] != "user":
        raise HTTPException(403, "Users only")
    db = get_db()
    await db.customers.update_one(
        {"_id": ObjectId(user["sub"])},
        {"$addToSet": {"addresses": body.address}},
    )
    return {"ok": True}


@router.delete("/addresses")
async def remove_address(body: AddressIn, user: dict = Depends(get_current_user)):
    if user["role"] != "user":
        raise HTTPException(403, "Users only")
    db = get_db()
    await db.customers.update_one(
        {"_id": ObjectId(user["sub"])},
        {"$pull": {"addresses": body.address}},
    )
    return {"ok": True}
