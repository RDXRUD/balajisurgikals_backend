from typing import Optional, List, Dict
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class PhoneLoginRequest(BaseModel):
    phone: str

class TokenResponse(BaseModel):
    access_token: str
    role: str
    name: str
    email: str
    addresses: List[str] = []


# ── Product ───────────────────────────────────────────────────────────────────

class ProductVariation(BaseModel):
    name: str
    options: List[str]
    priceModifier: float = Field(default=0, ge=0)
    optionStock: Dict[str, int] = {}

    @field_validator("optionStock")
    @classmethod
    def stock_non_negative(cls, v):
        if any(qty < 0 for qty in v.values()):
            raise ValueError("optionStock values must be >= 0")
        return v

class ProductIn(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    category: str = Field(min_length=1)
    subcategory: Optional[str] = None
    sku: Optional[str] = None
    brand: Optional[str] = None
    price: float = Field(ge=0)
    originalPrice: Optional[float] = Field(default=None, ge=0)
    stock: int = Field(default=10, ge=0)
    lowStockThreshold: int = Field(default=3, ge=0)
    images: List[str] = []
    isAvailable: bool = True
    isFeatured: bool = False
    isActive: bool = True
    visibleOnHome: bool = True
    labels: List[str] = []
    tags: List[str] = []
    collections: List[str] = []
    variations: List[ProductVariation] = []
    displayPriority: int = Field(default=99, ge=0)
    expiryDate: Optional[str] = None
    specifications: Optional[Dict[str, str]] = None

class ProductOut(ProductIn):
    id: str


# ── Promotion ─────────────────────────────────────────────────────────────────

class PromotionIn(BaseModel):
    title: str = Field(min_length=1)
    subtitle: str = ""
    imageUrl: Optional[str] = None
    actionLabel: Optional[str] = None
    actionRoute: Optional[str] = None
    isActive: bool = True
    displayPriority: int = Field(default=99, ge=0)
    gradientStart: Optional[str] = None
    gradientEnd: Optional[str] = None

class PromotionOut(PromotionIn):
    id: str


# ── Customer ──────────────────────────────────────────────────────────────────

class CustomerIn(BaseModel):
    phone: str = Field(min_length=5)
    name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    isActive: bool = True
    accessUntil: Optional[datetime] = None

class CustomerOut(CustomerIn):
    id: str
    addresses: List[str] = []


# ── Order ─────────────────────────────────────────────────────────────────────

class OrderItemIn(BaseModel):
    productId: str
    quantity: int = Field(ge=1)
    selectedVariations: Dict[str, str] = {}

class OrderIn(BaseModel):
    items: List[OrderItemIn] = Field(min_length=1)
    address: str = Field(min_length=1)
    paymentMethod: str = "UPI"
    deliverySlot: Optional[str] = None
    coupon: Optional[str] = None

class OrderItemOut(BaseModel):
    product: ProductOut
    quantity: int
    selectedVariations: Dict[str, str] = {}

class OrderOut(BaseModel):
    id: str
    customerId: str
    items: List[OrderItemOut]
    address: str
    status: str
    placedAt: datetime
    deliveryFee: float
    discount: float
    paymentMethod: str
    deliverySlot: Optional[str] = None
    subtotal: float
    total: float

class OrderStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v):
        valid = {"confirmed", "shipped", "outForDelivery", "delivered", "cancelled"}
        if v not in valid:
            raise ValueError(f"status must be one of {valid}")
        return v


# ── Analytics ─────────────────────────────────────────────────────────────────

class AnalyticsEvent(BaseModel):
    productId: str
    event: str

    @field_validator("event")
    @classmethod
    def valid_event(cls, v):
        if v not in {"click", "share"}:
            raise ValueError("event must be 'click' or 'share'")
        return v


# ── Wishlist ──────────────────────────────────────────────────────────────────

class WishlistToggle(BaseModel):
    productId: str


# ── User ──────────────────────────────────────────────────────────────────────

class AddressIn(BaseModel):
    address: str = Field(min_length=1)
