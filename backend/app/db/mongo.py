"""
Async MongoDB access via Motor. One client for the process lifetime,
created on startup and closed on shutdown (see app/main.py).

serverSelectionTimeoutMS is set explicitly (default 8s, see core/config.py's
mongo_timeout_ms) rather than left at Motor's own 30s default. Without this,
main.py's startup check ("is there real crawled data in Mongo?") could block
the whole app for a long time any time Mongo isn't reachable - the common
case for anyone who hasn't set it up yet, mistyped a connection string, or
hit a network/firewall issue with a cloud database like Atlas. If it times
out, the caller's try/except falls back to the seed dataset instead of
hanging.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

settings = get_settings()

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=settings.mongo_timeout_ms)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongo_db_name]


async def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def ensure_indexes() -> None:
    """Create indexes needed for search and lookups. Safe to call repeatedly."""
    db = get_db()
    await db.documents.create_index(
        [("title", "text"), ("content_text", "text"), ("keywords", "text")],
        name="document_text_index",
    )
    await db.documents.create_index("authority")
    await db.documents.create_index("waste_category")
    await db.documents.create_index("state")
    await db.documents.create_index("publication_date")
    await db.users.create_index("email", unique=True)
