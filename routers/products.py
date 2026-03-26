import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from bson import ObjectId
from database import get_db
from models import ProductIn, ProductOut
from auth import require_admin
from storage import upload_image, delete_image


def _generate_sku(category: str) -> str:
    prefix = "".join(w[0] for w in category.upper().split()[:3])[:3].ljust(3, "X")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"BSG-{prefix}-{suffix}"


router = APIRouter(prefix="/products", tags=["products"])


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("", response_model=List[ProductOut])
async def list_products(
    category: Optional[str] = None,
    available_only: bool = True,
    featured_only: bool = False,
    label: Optional[str] = None,
    collection: Optional[str] = None,
    brand: Optional[str] = None,
    visible_on_home: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
):
    db = get_db()
    query: dict = {}
    if available_only:
        query["isAvailable"] = True
        query["isActive"] = True
    if category and category != "All":
        query["category"] = category
    if featured_only:
        query["isFeatured"] = True
    if label:
        query["labels"] = label
    if collection:
        query["collections"] = collection
    if brand:
        query["brand"] = brand
    if visible_on_home is not None:
        query["visibleOnHome"] = visible_on_home
    cursor = db.products.find(query).sort("displayPriority", 1).skip(skip).limit(limit)
    return [_serialize(doc) async for doc in cursor]


@router.get("/search", response_model=List[ProductOut])
async def search_products(q: str = Query(..., min_length=1)):
    db = get_db()
    cursor = db.products.find(
        {"$text": {"$search": q}, "isAvailable": True, "isActive": True},
        {"score": {"$meta": "textScore"}},
    ).sort([("score", {"$meta": "textScore"})]).limit(50)
    return [_serialize(doc) async for doc in cursor]


@router.get("/meta/categories")
async def get_categories():
    db = get_db()
    cats = await db.products.distinct("category", {"isAvailable": True, "isActive": True})
    return sorted(cats)


@router.get("/meta/labels")
async def get_labels():
    db = get_db()
    pipeline = [
        {"$match": {"isAvailable": True, "isActive": True}},
        {"$unwind": "$labels"},
        {"$group": {"_id": "$labels"}},
        {"$sort": {"_id": 1}},
    ]
    result = await db.products.aggregate(pipeline).to_list(None)
    return [r["_id"] for r in result]


@router.get("/meta/collections")
async def get_collections():
    db = get_db()
    pipeline = [
        {"$match": {"isAvailable": True, "isActive": True}},
        {"$unwind": "$collections"},
        {"$group": {"_id": "$collections"}},
        {"$sort": {"_id": 1}},
    ]
    result = await db.products.aggregate(pipeline).to_list(None)
    return [r["_id"] for r in result]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: str):
    db = get_db()
    doc = await db.products.find_one({"_id": ObjectId(product_id)})
    if not doc:
        raise HTTPException(404, "Product not found")
    return _serialize(doc)


@router.post("", response_model=ProductOut, dependencies=[Depends(require_admin)])
async def create_product(body: ProductIn):
    db = get_db()
    data = body.model_dump()
    if not data.get("sku"):
        data["sku"] = _generate_sku(data["category"])
    result = await db.products.insert_one(data)
    data["id"] = str(result.inserted_id)
    return data


@router.put("/{product_id}", response_model=ProductOut, dependencies=[Depends(require_admin)])
async def update_product(product_id: str, body: ProductIn):
    """Sin 22 fix: use $set to preserve server-managed fields (sku, createdAt, etc.)"""
    db = get_db()
    oid = ObjectId(product_id)
    existing = await db.products.find_one({"_id": oid}, {"sku": 1})
    if not existing:
        raise HTTPException(404, "Product not found")
    data = body.model_dump()
    # Always preserve the server-generated SKU
    if not data.get("sku"):
        data["sku"] = existing.get("sku")
    await db.products.update_one({"_id": oid}, {"$set": data})
    doc = await db.products.find_one({"_id": oid})
    return _serialize(doc)


@router.patch("/{product_id}/availability", dependencies=[Depends(require_admin)])
async def toggle_availability(product_id: str):
    db = get_db()
    doc = await db.products.find_one({"_id": ObjectId(product_id)}, {"isAvailable": 1})
    if not doc:
        raise HTTPException(404, "Product not found")
    new_val = not doc["isAvailable"]
    await db.products.update_one({"_id": ObjectId(product_id)}, {"$set": {"isAvailable": new_val}})
    return {"isAvailable": new_val}


@router.delete("/{product_id}", dependencies=[Depends(require_admin)])
async def delete_product(product_id: str):
    db = get_db()
    await db.products.delete_one({"_id": ObjectId(product_id)})
    return {"ok": True}


@router.post("/images/upload", dependencies=[Depends(require_admin)])
async def upload_product_image(file: UploadFile = File(...)):
    url = await upload_image(file, folder="products")
    return {"url": url}


@router.delete("/images/delete", dependencies=[Depends(require_admin)])
async def delete_product_image(key: str = Query(...)):
    await delete_image(key)
    return {"ok": True}
