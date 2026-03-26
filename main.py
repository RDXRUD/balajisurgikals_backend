from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import connect, disconnect, get_db
from auth import hash_password
from config import settings
from routers import auth, products, orders, customers, analytics, promotions, wishlist


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()
    await _seed_admin()
    await _ensure_indexes()
    yield
    await disconnect()


async def _seed_admin():
    db = get_db()
    if not await db.admins.find_one({"email": settings.ADMIN_EMAIL}):
        await db.admins.insert_one({
            "email": settings.ADMIN_EMAIL,
            "password": hash_password(settings.ADMIN_PASSWORD),
            "name": "Admin",
        })


async def _ensure_indexes():
    db = get_db()
    await db.products.create_index([("name", "text"), ("description", "text"),
                                    ("tags", "text"), ("labels", "text"),
                                    ("collections", "text"), ("sku", "text")])
    await db.products.create_index("sku", unique=True, sparse=True)
    await db.products.create_index("category")
    await db.products.create_index("isAvailable")
    await db.products.create_index("displayPriority")
    await db.orders.create_index("customerId")
    await db.orders.create_index("placedAt")
    await db.customers.create_index("phone", unique=True)
    await db.analytics.create_index("productId", unique=True)
    await db.promotions.create_index("displayPriority")
    await db.wishlists.create_index("customerId", unique=True)


app = FastAPI(
    title="Balaji Surgikals API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(customers.router)
app.include_router(analytics.router)
app.include_router(promotions.router)
app.include_router(wishlist.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
