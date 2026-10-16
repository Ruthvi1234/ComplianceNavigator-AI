from __future__ import annotations

import logging
import re

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.services.crawler.constants import (
    WASTE_RELEVANCE_KEYWORDS,
)


logger = logging.getLogger(__name__)


# ============================================================
# EXCEPTIONS
# ============================================================

class RobotsDisallowedError(Exception):
    """Raised when robots.txt does not allow crawling a URL."""


# ============================================================
# DATE PATTERNS
# ============================================================

_DATE_PATTERNS = [

    re.compile(
        r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b"
    ),

    re.compile(
        r"\b(\d{1,2})-(\d{1,2})-(20\d{2})\b"
    ),

    re.compile(
        r"\b(\d{1,2})\.(\d{1,2})\.(20\d{2})\b"
    ),

    re.compile(
        r"\b(\d{1,2})\s+"
        r"(January|February|March|April|May|June|"
        r"July|August|September|October|November|December)"
        r"\s+(20\d{2})\b",
        re.IGNORECASE,
    ),
]


_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


# ============================================================
# DISCOVERED DOCUMENT
# ============================================================

@dataclass
class DiscoveredDocument:

    title: str
    detail_page_url: str
    pdf_url: str
    authority: str
    published_on: str | None = None

    @property
    def source_url(self) -> str:
        return (
            self.detail_page_url
            or self.pdf_url
            or ""
        )

    @property
    def file_url(self) -> str:
        return self.pdf_url or ""


# ============================================================
# BASE SPIDER
# ============================================================

class BaseSpider(ABC):

    authority: str

    def __init__(self) -> None:

        settings = get_settings()

        self._session = requests.Session()

        self._session.headers.update(
            {
                "User-Agent": settings.crawler_user_agent
            }
        )

        self._robots_cache: dict[
            str,
            RobotFileParser,
        ] = {}

    # ========================================================
    # DISCOVERY
    # ========================================================

    @abstractmethod
    def discover(self) -> list[DiscoveredDocument]:
        raise NotImplementedError

    # ========================================================
    # ROBOTS
    # ========================================================

    def _get_robots_parser(
        self,
        url: str,
    ) -> RobotFileParser:

        parsed = urlparse(url)

        origin = (
            f"{parsed.scheme}://{parsed.netloc}"
        )

        if origin not in self._robots_cache:

            robots_url = urljoin(
                origin,
                "/robots.txt",
            )

            parser = RobotFileParser()

            parser.set_url(
                robots_url
            )

            try:
                parser.read()

            except Exception as exc:

                logger.warning(
                    "Could not read robots.txt from %s: %s",
                    robots_url,
                    exc,
                )

            self._robots_cache[
                origin
            ] = parser

        return self._robots_cache[
            origin
        ]

    # ========================================================
    # ROBOTS CHECK
    # ========================================================

    def _check_allowed(
        self,
        url: str,
    ) -> None:

        settings = get_settings()

        parser = self._get_robots_parser(
            url
        )

        if not parser.can_fetch(
            settings.crawler_user_agent,
            url,
        ):

            raise RobotsDisallowedError(
                f"{urlparse(url).netloc}'s robots.txt "
                f"disallows automated access to {url}."
            )

    # ========================================================
    # GET HTML
    # ========================================================

    def _get_soup(
        self,
        url: str,
    ) -> BeautifulSoup:

        self._check_allowed(url)

        logger.info(
            "%s: fetching %s",
            self.authority,
            url,
        )

        response = self._session.get(
            url,
            timeout=30,
        )

        response.raise_for_status()

        return BeautifulSoup(
            response.text,
            "html.parser",
        )

    # ========================================================
    # NORMALISE
    # ========================================================

    @staticmethod
    def _normalise(
        text: str,
    ) -> str:

        text = str(
            text or ""
        ).lower()

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # ========================================================
    # WASTE RELEVANCE
    # ========================================================

    @staticmethod
    def _is_waste_relevant(
        title: str,
        relevance_keywords: list[str],
    ) -> bool:

        title_normalised = (
            BaseSpider._normalise(
                title
            )
        )

        if not title_normalised:
            return False

        for keyword in relevance_keywords:

            keyword_normalised = (
                BaseSpider._normalise(
                    keyword
                )
            )

            if (
                keyword_normalised
                and keyword_normalised
                in title_normalised
            ):
                return True

        return False

    # ========================================================
    # DATE EXTRACTION
    # ========================================================

    @staticmethod
    def _extract_publication_date(
        title: str,
    ) -> str | None:

        if not title:
            return None

        for pattern in _DATE_PATTERNS[:3]:

            match = pattern.search(
                title
            )

            if not match:
                continue

            try:

                day = int(
                    match.group(1)
                )

                month = int(
                    match.group(2)
                )

                year = int(
                    match.group(3)
                )

                return date(
                    year,
                    month,
                    day,
                ).isoformat()

            except ValueError:
                continue

        match = _DATE_PATTERNS[3].search(
            title
        )

        if match:

            try:

                day = int(
                    match.group(1)
                )

                month = _MONTHS[
                    match.group(2).lower()
                ]

                year = int(
                    match.group(3)
                )

                return date(
                    year,
                    month,
                    day,
                ).isoformat()

            except (
                ValueError,
                KeyError,
            ):
                pass

        return None

    # ========================================================
    # PDF LINK EXTRACTION
    # ========================================================

    def extract_pdf_links(
        self,
        soup: BeautifulSoup,
        base_url: str,
        relevance_keywords: list[str] | None = None,
    ) -> list[DiscoveredDocument]:

        if relevance_keywords is None:
            relevance_keywords = (
                WASTE_RELEVANCE_KEYWORDS
            )

        results: list[
            DiscoveredDocument
        ] = []

        seen_urls: set[str] = set()

        for link in soup.find_all(
            "a",
            href=True,
        ):

            href = str(
                link.get("href") or ""
            ).strip()

            if not href:
                continue

            # Accept .pdf even when query parameters exist.
            if not re.search(
                r"\.pdf(?:[?#].*)?$",
                href,
                re.IGNORECASE,
            ):
                continue

            full_url = urljoin(
                base_url,
                href,
            )

            if full_url in seen_urls:
                continue

            title = link.get_text(
                " ",
                strip=True,
            )

            if not title:

                title = str(
                    link.get("title") or ""
                ).strip()

            if not title:

                image = link.find(
                    "img"
                )

                if image:

                    title = str(
                        image.get("alt") or ""
                    ).strip()

            if not title:

                title = Path(
                    urlparse(
                        full_url
                    ).path
                ).stem

            title = re.sub(
                r"\s+",
                " ",
                title,
            ).strip()

            if not title:
                continue

            if relevance_keywords:

                if not self._is_waste_relevant(
                    title,
                    relevance_keywords,
                ):
                    continue

            published_on = (
                self._extract_publication_date(
                    title
                )
            )

            seen_urls.add(
                full_url
            )

            results.append(
                DiscoveredDocument(
                    title=title,
                    detail_page_url=base_url,
                    pdf_url=full_url,
                    authority=self.authority,
                    published_on=published_on,
                )
            )

        logger.info(
            "%s: extracted %d relevant PDFs from %s",
            self.authority,
            len(results),
            base_url,
        )

        return results