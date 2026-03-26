from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from database import get_db
from models import CustomerIn, CustomerOut
from auth import require_admin

router = APIRouter(prefix="/customers", tags=["customers"])


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("", response_model=List[CustomerOut], dependencies=[Depends(require_admin)])
async def list_customers(search: Optional[str] = None, skip: int = 0, limit: int = 100):
    db = get_db()
    query = {}
    if search:
        query["$or"] = [
            {"phone": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
        ]
    cursor = db.customers.find(query).skip(skip).limit(limit)
    return [_serialize(doc) async for doc in cursor]


@router.post("", response_model=CustomerOut, dependencies=[Depends(require_admin)])
async def create_customer(body: CustomerIn):
    db = get_db()
    if await db.customers.find_one({"phone": body.phone}):
        raise HTTPException(400, "Phone already registered")
    data = body.model_dump()
    data.setdefault("addresses", [])
    result = await db.customers.insert_one(data)
    data["id"] = str(result.inserted_id)
    return data


@router.put("/{customer_id}", response_model=CustomerOut, dependencies=[Depends(require_admin)])
async def update_customer(customer_id: str, body: CustomerIn):
    """Sin 21 fix: use $set so addresses field is never touched."""
    db = get_db()
    oid = ObjectId(customer_id)
    if not await db.customers.find_one({"_id": oid}):
        raise HTTPException(404, "Customer not found")
    update_fields = body.model_dump(exclude_none=True)
    await db.customers.update_one({"_id": oid}, {"$set": update_fields})
    doc = await db.customers.find_one({"_id": oid})
    return _serialize(doc)


@router.patch("/{customer_id}/access", dependencies=[Depends(require_admin)])
async def toggle_access(customer_id: str):
    db = get_db()
    doc = await db.customers.find_one({"_id": ObjectId(customer_id)}, {"isActive": 1})
    if not doc:
        raise HTTPException(404, "Customer not found")
    new_val = not doc["isActive"]
    await db.customers.update_one({"_id": ObjectId(customer_id)}, {"$set": {"isActive": new_val}})
    return {"isActive": new_val}


@router.delete("/{customer_id}", dependencies=[Depends(require_admin)])
async def delete_customer(customer_id: str):
    db = get_db()
    await db.customers.delete_one({"_id": ObjectId(customer_id)})
    return {"ok": True}
