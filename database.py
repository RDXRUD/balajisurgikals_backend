from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import settings

_client: AsyncIOMotorClient = None


def get_db() -> AsyncIOMotorDatabase:
    return _client[settings.MONGODB_DB]


async def connect():
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URI)


async def disconnect():
    global _client
    if _client:
        _client.close()
        _client = None
