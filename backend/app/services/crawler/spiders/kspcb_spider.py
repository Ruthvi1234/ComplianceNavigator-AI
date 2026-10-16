"""
KSPCB spider.

Uses explicitly supplied official KSPCB document URLs.
Does not bypass robots.txt.
"""

from __future__ import annotations

import logging

from app.services.crawler.base_spider import (
    BaseSpider,
    DiscoveredDocument,
)

from app.services.crawler.constants import (
    WASTE_RELEVANCE_KEYWORDS,
)


logger = logging.getLogger(__name__)


# ============================================================
# VERIFIED KSPCB DOCUMENTS
# ============================================================
#
# Add official URLs obtained from KSPCB.
#
# ============================================================

KSPCB_DOCUMENTS: list[dict[str, str | None]] = [
    # {
    #     "title": "Example official waste document",
    #     "pdf_url": "VERIFIED_KSPCB_PDF_URL",
    #     "published_on": "2024-01-01",
    # },
]


class KspcbSpider(BaseSpider):

    authority = "KSPCB"

    def _is_waste_document(
        self,
        title: str,
        pdf_url: str = "",
    ) -> bool:

        combined = self._normalise(
            f"{title} {pdf_url}"
        )

        return any(
            self._normalise(keyword)
            in combined
            for keyword in WASTE_RELEVANCE_KEYWORDS
        )

    def discover(
        self,
    ) -> list[DiscoveredDocument]:

        results: list[
            DiscoveredDocument
        ] = []

        seen_urls: set[str] = set()

        for item in KSPCB_DOCUMENTS:

            title = str(
                item.get("title") or ""
            ).strip()

            pdf_url = str(
                item.get("pdf_url") or ""
            ).strip()

            published_on = item.get(
                "published_on"
            )

            if not title or not pdf_url:
                continue

            if pdf_url in seen_urls:
                continue

            if not self._is_waste_document(
                title,
                pdf_url,
            ):
                continue

            seen_urls.add(
                pdf_url
            )

            results.append(
                DiscoveredDocument(
                    title=title,
                    detail_page_url=pdf_url,
                    pdf_url=pdf_url,
                    authority=self.authority,
                    published_on=published_on,
                )
            )

        logger.info(
            "KSPCB: discovered %d supplied official documents",
            len(results),
        )

        return results