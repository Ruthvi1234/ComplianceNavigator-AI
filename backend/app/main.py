import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.services.search.engine import search_engine
from app.services.search.seed_data import load_from_mongo
from app.workers import auto_updater


settings = get_settings()

logger = logging.getLogger(
    "compliance_navigator.startup"
)


@asynccontextmanager
async def lifespan(app: FastAPI):

    # ---------------------------------------------------------------
    # LOAD REAL DOCUMENTS FROM MONGODB
    # ---------------------------------------------------------------

    try:

        mongo_docs = await load_from_mongo()

    except Exception as exc:

        logger.exception(
            "Failed to load documents from MongoDB: %s",
            exc,
        )

        mongo_docs = []

    # ---------------------------------------------------------------
    # BUILD SEARCH INDEX
    # ---------------------------------------------------------------

    search_engine.build(
        mongo_docs
    )

    auto_updater.state.indexed_documents = (
        len(mongo_docs)
    )

    logger.info(
        "Search index initialized with %d MongoDB documents.",
        len(mongo_docs),
    )

    # ---------------------------------------------------------------
    # START AUTOMATIC CRAWLER
    # ---------------------------------------------------------------

    auto_updater.start()

    try:

        yield

    finally:

        await auto_updater.stop()


app = FastAPI(
    title=settings.app_name,
    description=(
        "Information Retrieval system for Indian "
        "industrial waste management regulations "
        "from MoEFCC, CPCB and KSPCB."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
)


@app.get(
    "/health",
    tags=["health"],
)
async def health() -> dict:

    return {
        "status": "ok",
        "app": settings.app_name,
        "indexedDocuments": len(
            search_engine.all_documents()
        ),
    }