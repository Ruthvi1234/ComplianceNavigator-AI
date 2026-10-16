"""
One-time migration.

Downloads every existing PDF in MongoDB and fills:

    content_text
    page_count
    keywords
    updated_at

Run from backend:

    python scripts/backfill_pdf_text.py
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone

from app.db.mongo import get_db
from app.services.document_processing.pdf_extractor import (
    extract_pdf_text,
)


logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(
    "compliance_navigator.backfill"
)


CATEGORY_KEYWORDS = {
    "Plastic": [
        "plastic",
        "plastic waste",
        "plastic packaging",
    ],

    "E-Waste": [
        "e-waste",
        "e waste",
        "electronic waste",
    ],

    "Battery": [
        "battery",
        "batteries",
        "battery waste",
    ],

    "Hazardous": [
        "hazardous",
        "hazardous waste",
    ],

    "Solid Waste": [
        "solid waste",
        "municipal solid waste",
    ],

    "Biomedical": [
        "biomedical",
        "bio-medical",
        "bio medical",
    ],

    "Construction & Demolition": [
        "construction",
        "demolition",
        "construction and demolition",
        "c&d",
    ],
}


def infer_categories(
    text: str,
) -> list[str]:

    text = text.lower()

    result = []

    for category, keywords in CATEGORY_KEYWORDS.items():

        if any(
            keyword.lower() in text
            for keyword in keywords
        ):
            result.append(category)

    return result


def make_keywords(
    title: str,
    categories: list[str],
    content: str,
) -> list[str]:

    values: set[str] = set()

    for category in categories:
        values.add(
            category.lower()
        )

    words = re.findall(
        r"[a-zA-Z][a-zA-Z0-9&-]{2,}",
        title.lower(),
    )

    values.update(words)

    content_lower = content.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():

        if category not in categories:
            continue

        for keyword in keywords:

            if keyword.lower() in content_lower:
                values.add(
                    keyword.lower()
                )

    return sorted(values)[:50]


async def main():

    db = get_db()

    cursor = db.documents.find({})

    processed = 0
    successful = 0
    failed = 0

    async for row in cursor:

        processed += 1

        pdf_url = row.get(
            "file_url"
        )

        if not pdf_url:

            logger.warning(
                "Skipping %s: no file_url",
                row.get("_id"),
            )

            continue

        logger.info(
            "[%d] Extracting: %s",
            processed,
            row.get("title"),
        )

        try:

            text, page_count = (
                await asyncio.to_thread(
                    extract_pdf_text,
                    pdf_url,
                )
            )

            text = text.strip()

            title = str(
                row.get(
                    "title",
                    "",
                )
            )

            categories = infer_categories(
                f"{title} {text[:200000]}"
            )

            keywords = make_keywords(
                title,
                categories,
                text,
            )

            update = {
                "content_text": text,
                "page_count": page_count,
                "keywords": keywords,
                "updated_at": datetime.now(
                    timezone.utc
                ),
            }

            if categories:

                update[
                    "waste_category"
                ] = categories

            await db.documents.update_one(
                {
                    "_id": row["_id"]
                },
                {
                    "$set": update
                },
            )

            successful += 1

            logger.info(
                "SUCCESS: %s | %d chars | %d pages | %s",
                title,
                len(text),
                page_count or 0,
                categories,
            )

        except Exception as exc:

            failed += 1

            logger.exception(
                "FAILED: %s: %s",
                pdf_url,
                exc,
            )

    logger.info(
        "Backfill complete. processed=%d successful=%d failed=%d",
        processed,
        successful,
        failed,
    )


if __name__ == "__main__":
    asyncio.run(main())