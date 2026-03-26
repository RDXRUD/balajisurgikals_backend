from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings
from database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    user = decode_token(creds.credentials)
    # For customer tokens, check accessUntil on every request
    if user.get("role") == "user":
        from bson import ObjectId
        db = get_db()
        doc = await db.customers.find_one(
            {"_id": ObjectId(user["sub"])},
            {"isActive": 1, "accessUntil": 1},
        )
        if not doc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
        if not doc.get("isActive", True):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account disabled")
        access_until = doc.get("accessUntil")
        if access_until is not None:
            if access_until.tzinfo is None:
                access_until = access_until.replace(tzinfo=timezone.utc)
            if access_until < datetime.now(timezone.utc):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Access expired")
    return user

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
