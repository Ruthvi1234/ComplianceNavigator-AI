from __future__ import annotations

import asyncio
import logging
import re

from datetime import date, datetime, timezone
from typing import Any

from app.db.mongo import get_db

from app.services.crawler.constants import (
    CATEGORY_KEYWORDS,
    VALID_WASTE_CATEGORIES,
    WASTE_RELEVANCE_KEYWORDS,
)

from app.services.crawler.spiders.cpcb_spider import (
    CpcbSpider,
)

from app.services.crawler.spiders.kspcb_spider import (
    KspcbSpider,
)

from app.services.crawler.spiders.moefcc_spider import (
    MoefccSpider,
)

from app.services.document_processing.pdf_extractor import (
    extract_pdf_text,
)


logger = logging.getLogger(
    __name__
)


# ============================================================
# EXCLUDED KEYWORDS
# ============================================================

EXCLUDED_KEYWORDS = [
    "cyber security",
    "cybersecurity",
    "information technology",
    "information technology policy",
    "it policy",
    "software development",
    "software",
    "human resources",
    "human resource",
    "recruitment",
    "vacancy",
    "job notification",
    "tender",
    "procurement",
    "accounts",
    "finance",
    "audit",
    "salary",
    "pension",
    "establishment",
    "administration",
    "administrative",
    "air quality",
    "air pollution",
    "water quality",
    "water pollution",
    "noise pollution",
    "noise pollution",
    "forest",
    "wildlife",
    "climate change",
]


# ============================================================
# HELPERS
# ============================================================

def _normalise(
    value: Any,
) -> str:

    text = str(
        value or ""
    ).lower()

    text = re.sub(
        r"[^a-z0-9&+/\-\s]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def _english_title(
    title: str,
) -> str:

    title = str(
        title or ""
    )

    title = re.sub(
        r"\s+",
        " ",
        title,
    )

    return title.strip()


def _is_explicitly_excluded(
    text: str,
) -> bool:

    normalized = _normalise(
        text
    )

    for keyword in EXCLUDED_KEYWORDS:

        if keyword in normalized:
            return True

    return False


def _is_waste_relevant(
    title: str,
    pdf_url: str | None = None,
) -> bool:

    combined = _normalise(
        " ".join(
            [
                title,
                pdf_url or "",
            ]
        )
    )

    if not combined:
        return False

    if _is_explicitly_excluded(
        combined
    ):
        return False

    for keyword in WASTE_RELEVANCE_KEYWORDS:

        normalized_keyword = _normalise(
            keyword
        )

        if (
            normalized_keyword
            and normalized_keyword
            in combined
        ):
            return True

    return False


# ============================================================
# CATEGORY
# ============================================================

def _infer_waste_category(
    title: str,
    content_text: str = "",
) -> list[str]:

    combined = _normalise(
        " ".join(
            [
                title,
                content_text,
            ]
        )
    )

    categories: list[str] = []

    for category in VALID_WASTE_CATEGORIES:

        keywords = CATEGORY_KEYWORDS.get(
            category,
            [],
        )

        for keyword in keywords:

            normalized_keyword = _normalise(
                keyword
            )

            if (
                normalized_keyword
                and normalized_keyword
                in combined
            ):

                categories.append(
                    category
                )

                break

    return list(
        dict.fromkeys(
            categories
        )
    )


# ============================================================
# DOCUMENT TYPE
# ============================================================

def _infer_document_type(
    title: str,
) -> str:

    normalized = _normalise(
        title
    )

    if "amendment" in normalized:
        return "Amendment"

    if "guideline" in normalized:
        return "Guideline"

    if "circular" in normalized:
        return "Circular"

    if "notification" in normalized:
        return "Notification"

    if (
        "rule" in normalized
        or "rules" in normalized
    ):
        return "Rule"

    return "Notification"


# ============================================================
# KEYWORDS
# ============================================================

def _keywords_for_document(
    title: str,
    content_text: str,
    categories: list[str],
) -> list[str]:

    normalized = _normalise(
        " ".join(
            [
                title,
                content_text,
            ]
        )
    )

    keywords: list[str] = []

    for category in categories:

        keywords.append(
            category
        )

    for keyword in WASTE_RELEVANCE_KEYWORDS:

        normalized_keyword = _normalise(
            keyword
        )

        if (
            normalized_keyword
            and normalized_keyword
            in normalized
        ):

            keywords.append(
                keyword
            )

    return list(
        dict.fromkeys(
            keywords
        )
    )


# ============================================================
# REFERENCE CODE
# ============================================================

def _generate_reference_code(
    title: str,
    source_url: str,
) -> str:

    text = _normalise(
        title
    )

    match = re.search(
        r"\b\d{4}\b",
        text,
    )

    year = (
        match.group(0)
        if match
        else ""
    )

    if "plastic" in text:

        prefix = "PLASTIC"

    elif (
        "e-waste" in text
        or "e waste" in text
        or "electronic waste" in text
    ):

        prefix = "EWASTE"

    elif "battery" in text:

        prefix = "BATTERY"

    elif "hazardous" in text:

        prefix = "HAZARDOUS"

    elif "biomedical" in text:

        prefix = "BIOMEDICAL"

    elif (
        "construction" in text
        or "demolition" in text
        or "c&d" in text
    ):

        prefix = "C&D"

    elif "solid waste" in text:

        prefix = "SOLID-WASTE"

    else:

        prefix = "WASTE"

    if year:
        return f"{prefix}-{year}"

    return prefix


# ============================================================
# PUBLICATION DATE
# ============================================================

def _normalise_publication_date(
    value: Any,
) -> str | None:

    if value is None:
        return None

    if isinstance(
        value,
        datetime,
    ):

        return value.date().isoformat()

    if isinstance(
        value,
        date,
    ):

        return value.isoformat()

    value = str(
        value
    ).strip()

    if not value:
        return None

    # YYYY-MM-DD
    match = re.search(
        r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b",
        value,
    )

    if match:

        try:

            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            ).isoformat()

        except ValueError:
            pass

    # DD/MM/YYYY or DD-MM-YYYY
    match = re.search(
        r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b",
        value,
    )

    if match:

        try:

            return date(
                int(match.group(3)),
                int(match.group(2)),
                int(match.group(1)),
            ).isoformat()

        except ValueError:
            pass

    return None


# ============================================================
# SUMMARY
# ============================================================

def _build_summary(
    title: str,
    content_text: str,
) -> str:

    if content_text:

        cleaned = re.sub(
            r"\s+",
            " ",
            content_text,
        ).strip()

        if cleaned:
            return cleaned[:500]

    return _english_title(
        title
    )


# ============================================================
# URL COMPATIBILITY
# ============================================================

def _get_pdf_url(
    doc: Any,
) -> str | None:

    value = (
        getattr(
            doc,
            "file_url",
            None,
        )
        or getattr(
            doc,
            "pdf_url",
            None,
        )
    )

    if not value:
        return None

    value = str(
        value
    ).strip()

    return value or None


def _get_source_url(
    doc: Any,
) -> str:

    value = (
        getattr(
            doc,
            "source_url",
            None,
        )
        or getattr(
            doc,
            "detail_page_url",
            None,
        )
        or _get_pdf_url(doc)
        or ""
    )

    return str(
        value
    ).strip()


# ============================================================
# MONGO CONVERSION
# ============================================================

def _to_mongo_document(
    doc: Any,
    content_text: str = "",
    page_count: int | None = None,
) -> dict[str, Any]:

    title = _english_title(
        getattr(
            doc,
            "title",
            "",
        )
    )

    authority = getattr(
        doc,
        "authority",
        None,
    )

    if hasattr(
        authority,
        "value",
    ):

        authority = authority.value

    authority = str(
        authority or ""
    )

    source_url = _get_source_url(
        doc
    )

    file_url = _get_pdf_url(
        doc
    )

    categories = _infer_waste_category(
        title,
        content_text,
    )

    keywords = _keywords_for_document(
        title,
        content_text,
        categories,
    )

    publication_date = (
        _normalise_publication_date(
            getattr(
                doc,
                "published_on",
                None,
            )
        )
    )

    return {
        "title": title,
        "authority": authority,
        "document_type": _infer_document_type(
            title
        ),
        "waste_category": categories,
        "state": getattr(
            doc,
            "state",
            None,
        ),
        "publication_date": publication_date,
        "reference_code": _generate_reference_code(
            title,
            source_url,
        ),
        "keywords": keywords,
        "summary": _build_summary(
            title,
            content_text,
        ),
        "source_url": source_url,
        "file_url": file_url,
        "detail_page_url": getattr(
            doc,
            "detail_page_url",
            source_url,
        ),
        "pdf_url": getattr(
            doc,
            "pdf_url",
            file_url,
        ),
        "page_count": page_count,
        "content_text": content_text,
        "original_title": title,
        "updated_at": datetime.now(
            timezone.utc
        ),
    }


# ============================================================
# EXISTING DOCUMENT
# ============================================================

async def _get_existing_document(
    collection: Any,
    source_url: str,
    file_url: str | None,
) -> dict[str, Any] | None:

    if file_url:

        existing = await collection.find_one(
            {
                "$or": [
                    {
                        "file_url": file_url
                    },
                    {
                        "pdf_url": file_url
                    },
                ]
            }
        )

        if existing:
            return existing

    if source_url:

        existing = await collection.find_one(
            {
                "$or": [
                    {
                        "source_url": source_url
                    },
                    {
                        "detail_page_url": source_url
                    },
                ]
            }
        )

        if existing:
            return existing

    return None


# ============================================================
# NEEDS ENRICHMENT
# ============================================================

def _needs_enrichment(
    existing: dict[str, Any],
) -> bool:

    content_text = str(
        existing.get(
            "content_text",
            "",
        )
        or ""
    ).strip()

    page_count = existing.get(
        "page_count"
    )

    keywords = existing.get(
        "keywords",
        [],
    )

    categories = existing.get(
        "waste_category",
        [],
    )

    return (
        not content_text
        or page_count is None
        or not keywords
        or not categories
    )


# ============================================================
# ENRICH EXISTING DOCUMENT
# ============================================================

async def _enrich_existing_document(
    collection: Any,
    existing: dict[str, Any],
) -> bool:

    file_url = (
        existing.get(
            "file_url"
        )
        or existing.get(
            "pdf_url"
        )
    )

    if not file_url:
        return False

    try:

        content_text, page_count = (
            await asyncio.to_thread(
                extract_pdf_text,
                file_url,
            )
        )

    except Exception as exc:

        logger.warning(
            "Failed enriching %s: %s",
            file_url,
            exc,
        )

        return False

    title = str(
        existing.get(
            "title",
            "",
        )
        or ""
    )

    categories = _infer_waste_category(
        title,
        content_text,
    )

    keywords = _keywords_for_document(
        title,
        content_text,
        categories,
    )

    update = {
        "content_text": content_text,
        "page_count": page_count,
        "keywords": keywords,
        "waste_category": categories,
        "summary": _build_summary(
            title,
            content_text,
        ),
        "updated_at": datetime.now(
            timezone.utc
        ),
    }

    await collection.update_one(
        {
            "_id": existing["_id"]
        },
        {
            "$set": update
        },
    )

    return True


# ============================================================
# PROCESS DOCUMENT
# ============================================================

async def _process_document(
    collection: Any,
    doc: Any,
) -> bool:

    title = _english_title(
        getattr(
            doc,
            "title",
            "",
        )
    )

    pdf_url = _get_pdf_url(
        doc
    )

    source_url = _get_source_url(
        doc
    )

    logger.info(
        "Processing [%s] %s",
        getattr(
            doc,
            "authority",
            "UNKNOWN",
        ),
        title,
    )

    # --------------------------------------------------------
    # Relevance
    # --------------------------------------------------------

    if not _is_waste_relevant(
        title,
        pdf_url,
    ):

        logger.info(
            "Rejected non-waste document: %s",
            title,
        )

        return False

    # --------------------------------------------------------
    # PDF extraction
    # --------------------------------------------------------

    content_text = ""
    page_count = None

    if pdf_url:

        try:

            (
                content_text,
                page_count,
            ) = await asyncio.to_thread(
                extract_pdf_text,
                pdf_url,
            )

        except Exception as exc:

            logger.warning(
                "PDF extraction failed for %s: %s",
                pdf_url,
                exc,
            )

    # --------------------------------------------------------
    # Build Mongo document
    # --------------------------------------------------------

    mongo_document = _to_mongo_document(
        doc,
        content_text,
        page_count,
    )

    # --------------------------------------------------------
    # Require at least one usable URL
    # --------------------------------------------------------

    if not source_url and not pdf_url:

        logger.warning(
            "Skipping document with no usable URL: %s",
            title,
        )

        return False

    # --------------------------------------------------------
    # Upsert
    # --------------------------------------------------------

    query = {}

    if pdf_url:

        query = {
            "$or": [
                {
                    "file_url": pdf_url
                },
                {
                    "pdf_url": pdf_url
                },
            ]
        }

    else:

        query = {
            "$or": [
                {
                    "source_url": source_url
                },
                {
                    "detail_page_url": source_url
                },
            ]
        }

    await collection.update_one(
        query,
        {
            "$set": mongo_document,
            "$setOnInsert": {
                "created_at": datetime.now(
                    timezone.utc
                ),
            },
        },
        upsert=True,
    )

    logger.info(
        "Stored document: [%s] %s",
        mongo_document["authority"],
        title,
    )

    return True


# ============================================================
# DISCOVER ALL AUTHORITIES
# ============================================================

async def _discover_documents() -> list[Any]:

    documents: list[Any] = []

    spiders = [
        CpcbSpider(),
        MoefccSpider(),
        KspcbSpider(),
    ]

    for spider in spiders:

        authority = getattr(
            spider,
            "authority",
            spider.__class__.__name__,
        )

        try:

            result = await asyncio.to_thread(
                spider.discover
            )

            result = result or []

            documents.extend(
                result
            )

            logger.info(
                "%s crawler discovered %d documents",
                authority,
                len(result),
            )

        except Exception as exc:

            logger.exception(
                "%s crawler failed: %s",
                authority,
                exc,
            )

            continue

    return documents


# ============================================================
# ONE UPDATE CYCLE
# ============================================================

async def run_once() -> None:

    logger.info(
        "Starting compliance document update cycle."
    )

    db = get_db()

    collection = db[
        "regulation_documents"
    ]

    documents = await _discover_documents()

    logger.info(
        "Total discovered documents: %d",
        len(documents),
    )

    inserted_or_updated = 0
    enriched = 0
    rejected = 0
    failed = 0

    for doc in documents:

        try:

            title = _english_title(
                getattr(
                    doc,
                    "title",
                    "",
                )
            )

            file_url = _get_pdf_url(
                doc
            )

            source_url = _get_source_url(
                doc
            )

            existing = (
                await _get_existing_document(
                    collection,
                    source_url,
                    file_url,
                )
            )

            if existing:

                if _needs_enrichment(
                    existing
                ):

                    success = (
                        await _enrich_existing_document(
                            collection,
                            existing,
                        )
                    )

                    if success:
                        enriched += 1

                continue

            success = (
                await _process_document(
                    collection,
                    doc,
                )
            )

            if success:
                inserted_or_updated += 1
            else:
                rejected += 1

        except Exception as exc:

            failed += 1

            logger.exception(
                "Failed processing document %s: %s",
                getattr(
                    doc,
                    "title",
                    "<unknown>",
                ),
                exc,
            )

    logger.info(
        "Update cycle complete: "
        "inserted_or_updated=%d "
        "enriched=%d "
        "rejected=%d "
        "failed=%d",
        inserted_or_updated,
        enriched,
        rejected,
        failed,
    )


# ============================================================
# CONTINUOUS SCHEDULER
# ============================================================

async def run_forever(
    interval_seconds: int = 86400,
) -> None:

    while True:

        try:

            await run_once()

        except Exception as exc:

            logger.exception(
                "Unexpected scheduler failure: %s",
                exc,
            )

        await asyncio.sleep(
            interval_seconds
        )