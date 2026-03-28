from fastapi import APIRouter, Depends
from pydantic import BaseModel
from auth import require_admin
from database import get_db

router = APIRouter(prefix="/config", tags=["config"])

class ShareConfig(BaseModel):
    template: str
    customMessage: str = ""

@router.get("/share")
async def get_share_config(_=Depends(require_admin)):
    db = get_db()
    doc = await db.config.find_one({"key": "share"})
    if not doc:
        return ShareConfig(
            template="{{name}}\n\n{{desc}}"
        )
    return ShareConfig(template=doc["template"], customMessage=doc.get("customMessage", ""))

@router.put("/share")
async def save_share_config(body: ShareConfig, _=Depends(require_admin)):
    db = get_db()
    await db.config.update_one(
        {"key": "share"},
        {"$set": {"key": "share", "template": body.template, "customMessage": body.customMessage}},
        upsert=True,
    )
    return {"ok": True}
