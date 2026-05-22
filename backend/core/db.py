"""MongoDB client (Motor) — single shared instance."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient

from .config import MONGO_URL, DB_NAME

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
