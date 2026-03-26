from fastapi import APIRouter, Depends
from database import get_db
from models import AnalyticsEvent
from auth import get_current_user, require_admin

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/event")
async def record_event(body: AnalyticsEvent, user: dict = Depends(get_current_user)):
    db = get_db()
    field = "clicks" if body.event == "click" else "shares"
    await db.analytics.update_one(
        {"productId": body.productId},
        {"$inc": {field: 1}},
        upsert=True,
    )
    return {"ok": True}


@router.get("/summary", dependencies=[Depends(require_admin)])
async def summary():
    db = get_db()
    pipeline = [{"$group": {"_id": None, "totalClicks": {"$sum": "$clicks"},
                             "totalShares": {"$sum": "$shares"}}}]
    result = await db.analytics.aggregate(pipeline).to_list(1)
    totals = result[0] if result else {"totalClicks": 0, "totalShares": 0}
    totals.pop("_id", None)
    top = await db.analytics.find().sort("clicks", -1).limit(20).to_list(20)
    totals["topByClicks"] = [
        {"productId": d["productId"], "clicks": d.get("clicks", 0), "shares": d.get("shares", 0)}
        for d in top
    ]
    return totals


@router.get("/dashboard", dependencies=[Depends(require_admin)])
async def dashboard():
    db = get_db()
    total_products = await db.products.count_documents({})
    active_products = await db.products.count_documents({"isAvailable": True, "isActive": True})
    total_orders = await db.orders.count_documents({})
    active_orders = await db.orders.count_documents({"status": {"$nin": ["delivered", "cancelled"]}})
    total_customers = await db.customers.count_documents({})
    active_customers = await db.customers.count_documents({"isActive": True})

    # Revenue from delivered orders
    pipeline = [
        {"$match": {"status": "delivered"}},
        {"$group": {"_id": None, "revenue": {"$sum": "$total"}}},
    ]
    rev_result = await db.orders.aggregate(pipeline).to_list(1)
    revenue = rev_result[0]["revenue"] if rev_result else 0.0

    # Low stock products
    low_stock = await db.products.count_documents(
        {"isActive": True, "$expr": {"$and": [
            {"$gt": ["$stock", 0]},
            {"$lte": ["$stock", "$lowStockThreshold"]},
        ]}}
    )
    out_of_stock = await db.products.count_documents({"isActive": True, "stock": 0})

    return {
        "totalProducts": total_products,
        "activeProducts": active_products,
        "totalOrders": total_orders,
        "activeOrders": active_orders,
        "totalCustomers": total_customers,
        "activeCustomers": active_customers,
        "revenue": revenue,
        "lowStockProducts": low_stock,
        "outOfStockProducts": out_of_stock,
    }
