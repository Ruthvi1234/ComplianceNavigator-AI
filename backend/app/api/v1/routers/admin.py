import logging

from fastapi import APIRouter

from app.services.search.engine import search_engine
from app.services.search.seed_data import load_from_mongo
from app.workers import auto_updater

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger("compliance_navigator.admin")


@router.post("/reindex")
async def reindex():
    """Manual index rebuild from MongoDB.

    Not normally needed any more: the backend crawls and reindexes itself on
    a timer (see app/workers/auto_updater.py). Kept as an escape hatch for
    when documents are loaded into Mongo by some other means.
    """
    try:
        docs = await load_from_mongo()
    except Exception as exc:
        return {"status": "error", "detail": f"Could not reach MongoDB: {exc}"}

    if not docs:
        return {"status": "empty", "detail": "MongoDB has no documents yet; index left unchanged."}

    search_engine.build(docs)
    auto_updater.state.indexed_documents = len(docs)
    return {"status": "ok", "indexed_documents": len(docs)}


@router.get("/auto-update")
async def auto_update_status():
    """Live status of the automatic updater: whether it's on, when it last
    ran, what it found, and when the next run is due."""
    return auto_updater.state.as_dict()


@router.post("/auto-update/run-now")
async def auto_update_run_now():
    """Force an immediate crawl + reindex without waiting for the timer.
    Runs the same code path as the scheduled pass and won't overlap it."""
    return await auto_updater.run_update_cycle()
