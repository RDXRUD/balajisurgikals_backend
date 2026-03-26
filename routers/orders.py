from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime, timezone
from database import get_db
from models import OrderIn, OrderOut, OrderStatusUpdate
from auth import get_current_user, require_admin

router = APIRouter(prefix="/orders", tags=["orders"])

DELIVERY_FEE = 40.0
FREE_DELIVERY_THRESHOLD = 499.0
COUPONS = {"SAVE50": 50.0, "FIRST100": 100.0}


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.post("", response_model=OrderOut)
async def place_order(body: OrderIn, user: dict = Depends(get_current_user)):
    db = get_db()
    items_out = []
    subtotal = 0.0
    # Collect stock decrements — validate all first, then apply atomically
    stock_updates = []

    for item in body.items:
        doc = await db.products.find_one({"_id": ObjectId(item.productId)})
        if not doc:
            raise HTTPException(404, f"Product {item.productId} not found")
        if not doc.get("isAvailable") or not doc.get("isActive"):
            raise HTTPException(400, f"'{doc['name']}' is not available")

        # Sin 24 fix: check stock before accepting order
        current_stock = doc.get("stock", 0)
        if current_stock < item.quantity:
            raise HTTPException(400, f"'{doc['name']}' has only {current_stock} units in stock")

        price = doc["price"]
        for v in doc.get("variations", []):
            selected = item.selectedVariations.get(v["name"])
            if selected:
                price += v.get("priceModifier", 0)

        subtotal += price * item.quantity
        product_out = {**doc, "id": str(doc["_id"])}
        product_out.pop("_id", None)
        items_out.append({
            "product": product_out,
            "quantity": item.quantity,
            "selectedVariations": item.selectedVariations,
        })
        stock_updates.append((ObjectId(item.productId), item.quantity))

    delivery_fee = 0.0 if subtotal >= FREE_DELIVERY_THRESHOLD else DELIVERY_FEE
    discount = COUPONS.get((body.coupon or "").upper(), 0.0)

    order_doc = {
        "customerId": user["sub"],
        "items": items_out,
        "address": body.address,
        "status": "confirmed",
        "placedAt": datetime.now(timezone.utc),
        "deliveryFee": delivery_fee,
        "discount": discount,
        "paymentMethod": body.paymentMethod,
        "deliverySlot": body.deliverySlot,
        "subtotal": subtotal,
        "total": subtotal + delivery_fee - discount,
    }
    result = await db.orders.insert_one(order_doc)

    # Decrement stock after successful order insert
    for product_oid, qty in stock_updates:
        await db.products.update_one(
            {"_id": product_oid},
            {"$inc": {"stock": -qty}},
        )

    order_doc["id"] = str(result.inserted_id)
    return order_doc


@router.get("/my", response_model=List[OrderOut])
async def my_orders(user: dict = Depends(get_current_user)):
    db = get_db()
    cursor = db.orders.find({"customerId": user["sub"]}).sort("placedAt", -1)
    return [_serialize(doc) async for doc in cursor]


@router.get("", response_model=List[OrderOut], dependencies=[Depends(require_admin)])
async def all_orders(status: Optional[str] = None, skip: int = 0, limit: int = 100):
    db = get_db()
    query = {}
    if status:
        query["status"] = status
    cursor = db.orders.find(query).sort("placedAt", -1).skip(skip).limit(limit)
    return [_serialize(doc) async for doc in cursor]


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.orders.find_one({"_id": ObjectId(order_id)})
    if not doc:
        raise HTTPException(404, "Order not found")
    if user["role"] != "admin" and doc["customerId"] != user["sub"]:
        raise HTTPException(403, "Forbidden")
    return _serialize(doc)


@router.patch("/{order_id}/status", dependencies=[Depends(require_admin)])
async def update_status(order_id: str, body: OrderStatusUpdate):
    db = get_db()
    doc = await db.orders.find_one({"_id": ObjectId(order_id)}, {"status": 1})
    if not doc:
        raise HTTPException(404, "Order not found")

    # Restore stock if order is cancelled
    if body.status == "cancelled" and doc["status"] != "cancelled":
        full = await db.orders.find_one({"_id": ObjectId(order_id)}, {"items": 1})
        for item in full.get("items", []):
            pid = item["product"].get("id") or item["product"].get("_id")
            if pid:
                await db.products.update_one(
                    {"_id": ObjectId(str(pid))},
                    {"$inc": {"stock": item["quantity"]}},
                )

    await db.orders.update_one(
        {"_id": ObjectId(order_id)}, {"$set": {"status": body.status}}
    )
    return {"status": body.status}
