from typing import List
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from database import get_db
from models import WishlistToggle, ProductOut
from auth import get_current_user

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@router.get("", response_model=List[ProductOut])
async def get_wishlist(user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.wishlists.find_one({"customerId": user["sub"]})
    if not doc or not doc.get("productIds"):
        return []
    ids = [ObjectId(pid) for pid in doc["productIds"]]
    cursor = db.products.find({"_id": {"$in": ids}})
    results = []
    async for p in cursor:
        p["id"] = str(p.pop("_id"))
        results.append(p)
    return results


@router.post("/toggle")
async def toggle_wishlist(body: WishlistToggle, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.wishlists.find_one({"customerId": user["sub"]})
    product_ids = doc["productIds"] if doc else []

    if body.productId in product_ids:
        product_ids.remove(body.productId)
        wishlisted = False
    else:
        product_ids.append(body.productId)
        wishlisted = True

    await db.wishlists.update_one(
        {"customerId": user["sub"]},
        {"$set": {"productIds": product_ids}},
        upsert=True,
    )
    return {"wishlisted": wishlisted, "productId": body.productId}


@router.get("/ids")
async def get_wishlist_ids(user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.wishlists.find_one({"customerId": user["sub"]})
    return {"productIds": doc["productIds"] if doc else []}
