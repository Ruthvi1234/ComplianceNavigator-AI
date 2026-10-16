"""
CPCB spider.

Discovers waste-management documents from official CPCB listing pages.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from app.services.crawler.base_spider import (
    BaseSpider,
    DiscoveredDocument,
    RobotsDisallowedError,
)
from app.services.crawler.constants import (
    WASTE_RELEVANCE_KEYWORDS,
)

logger = logging.getLogger(__name__)


# ============================================================
# OFFICIAL CPCB LISTING PAGES
# ============================================================
#
# IMPORTANT:
# Put VERIFIED CPCB listing/index pages here.
#
# Do NOT put individual PDFs here.
#
# Example:
#
# CPCB_LISTING_URLS = [
#     "VERIFIED_OFFICIAL_CPCB_DOCUMENT_LISTING_URL",
# ]
#
# ============================================================

CPCB_LISTING_URLS: list[str] = [
    # Add verified official CPCB document listing URLs here.
]


class CpcbSpider(BaseSpider):

    authority = "CPCB"

    # ========================================================
    # NORMALISE
    # ========================================================

    @staticmethod
    def _normalise(text: str) -> str:
        text = str(text or "").lower()

        text = re.sub(
            r"[\-_\/]+",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # ========================================================
    # WASTE CHECK
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
            self._normalise(keyword) in combined
            for keyword in WASTE_RELEVANCE_KEYWORDS
        )

    # ========================================================
    # DISCOVER
    # ========================================================

    def discover(self) -> list[DiscoveredDocument]:

        results: list[DiscoveredDocument] = []

        seen_urls: set[str] = set()

        if not CPCB_LISTING_URLS:
            logger.warning(
                "CPCB_LISTING_URLS is empty. "
                "No CPCB documents will be discovered."
            )

            return results

        for listing_url in CPCB_LISTING_URLS:

            try:

                soup = self._get_soup(
                    listing_url
                )

            except RobotsDisallowedError as exc:

                logger.warning(
                    "CPCB robots restriction: %s",
                    exc,
                )

                continue

            except Exception as exc:

                logger.exception(
                    "CPCB failed to fetch %s: %s",
                    listing_url,
                    exc,
                )

                continue

            try:

                documents = self.extract_pdf_links(
                    soup,
                    base_url=listing_url,
                    relevance_keywords=WASTE_RELEVANCE_KEYWORDS,
                )

            except Exception as exc:

                logger.exception(
                    "CPCB PDF extraction failed for %s: %s",
                    listing_url,
                    exc,
                )

                continue

            for doc in documents:

                pdf_url = (
                    doc.pdf_url or ""
                ).strip()

                if not pdf_url:
                    continue

                if pdf_url in seen_urls:
                    continue

                if not self._is_waste_document(
                    doc.title,
                    pdf_url,
                ):
                    continue

                seen_urls.add(pdf_url)

                results.append(
                    doc
                )

        logger.info(
            "CPCB discovery complete: %d documents",
            len(results),
        )

        return results