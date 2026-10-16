"""
MoEFCC spider.

Discovers waste-management-related documents
from official MoEFCC pages.
"""

from __future__ import annotations

import logging

from app.services.crawler.constants import (
    WASTE_RELEVANCE_KEYWORDS,
)

from app.services.crawler.base_spider import (
    BaseSpider,
    DiscoveredDocument,
    RobotsDisallowedError,
)


logger = logging.getLogger(
    __name__
)


# ============================================================
# OFFICIAL MOEFCC LISTING PAGES
# ============================================================

LISTING_URLS = [
    "https://moef.gov.in/rules-regulations-3",
    "https://www.moef.gov.in/rules-regulations-3",
]


class MoefccSpider(BaseSpider):

    authority = "MoEFCC"

    # ========================================================
    # NORMALISE
    # ========================================================

    def _normalise(
        self,
        text: str,
    ) -> str:

        return (
            str(text or "")
            .lower()
            .replace("-", " ")
            .replace("_", " ")
            .replace("/", " ")
        )

    # ========================================================
    # RELEVANCE
    # ========================================================

    def _is_waste_document(
        self,
        title: str,
        pdf_url: str = "",
    ) -> bool:

        combined = self._normalise(
            f"{title} {pdf_url}"
        )

        if not combined:
            return False

        return any(
            self._normalise(
                keyword
            ) in combined
            for keyword
            in WASTE_RELEVANCE_KEYWORDS
        )

    # ========================================================
    # DISCOVER
    # ========================================================

    def discover(
        self,
    ) -> list[DiscoveredDocument]:

        results: list[
            DiscoveredDocument
        ] = []

        seen_urls: set[str] = set()

        for listing_url in LISTING_URLS:

            try:

                soup = self._get_soup(
                    listing_url
                )

            except RobotsDisallowedError as exc:

                logger.warning(
                    "MoEFCC robots restriction: %s",
                    exc,
                )

                continue

            except Exception as exc:

                logger.exception(
                    "MoEFCC failed to fetch %s: %s",
                    listing_url,
                    exc,
                )

                continue

            try:

                documents = (
                    self.extract_pdf_links(
                        soup,
                        base_url=listing_url,
                        relevance_keywords=WASTE_RELEVANCE_KEYWORDS,
                    )
                )

            except Exception as exc:

                logger.exception(
                    "MoEFCC PDF extraction failed: %s",
                    exc,
                )

                continue

            accepted = 0

            for doc in documents:

                pdf_url = (
                    doc.pdf_url.strip()
                )

                if not pdf_url:
                    continue

                if pdf_url in seen_urls:
                    continue

                if not self._is_waste_document(
                    doc.title,
                    pdf_url,
                ):
                    continue

                seen_urls.add(
                    pdf_url
                )

                results.append(
                    doc
                )

                accepted += 1

            logger.info(
                "MoEFCC: accepted %d documents from %s",
                accepted,
                listing_url,
            )

        logger.info(
            "MoEFCC crawler complete: %d documents",
            len(results),
        )

        return results