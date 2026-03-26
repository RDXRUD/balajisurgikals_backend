from typing import List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from bson import ObjectId
from database import get_db
from models import PromotionIn, PromotionOut
from auth import require_admin
from storage import upload_image

router = APIRouter(prefix="/promotions", tags=["promotions"])


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("", response_model=List[PromotionOut])
async def list_promotions(active_only: bool = True):
    db = get_db()
    query = {"isActive": True} if active_only else {}
    cursor = db.promotions.find(query).sort("displayPriority", 1)
    return [_serialize(doc) async for doc in cursor]


@router.post("", response_model=PromotionOut, dependencies=[Depends(require_admin)])
async def create_promotion(body: PromotionIn):
    db = get_db()
    data = body.model_dump()
    result = await db.promotions.insert_one(data)
    data["id"] = str(result.inserted_id)
    return data


@router.put("/{promo_id}", response_model=PromotionOut, dependencies=[Depends(require_admin)])
async def update_promotion(promo_id: str, body: PromotionIn):
    db = get_db()
    data = body.model_dump()
    result = await db.promotions.find_one_and_replace(
        {"_id": ObjectId(promo_id)}, data, return_document=True
    )
    if not result:
        raise HTTPException(404, "Promotion not found")
    return _serialize(result)


@router.delete("/{promo_id}", dependencies=[Depends(require_admin)])
async def delete_promotion(promo_id: str):
    db = get_db()
    await db.promotions.delete_one({"_id": ObjectId(promo_id)})
    return {"ok": True}


@router.post("/images/upload", dependencies=[Depends(require_admin)])
async def upload_promo_image(file: UploadFile = File(...)):
    url = await upload_image(file, folder="promotions")
    return {"url": url}
