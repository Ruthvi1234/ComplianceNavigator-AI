from unittest.mock import MagicMock

import pytest

from app.services.crawler.base_spider import BaseSpider, DiscoveredDocument, RobotsDisallowedError


class _FakeSpider(BaseSpider):
    """Bypasses network setup entirely - tests only the robots.txt gate,
    not real HTTP behavior."""

    authority = "TEST"

    def __init__(self):
        self._robots_cache = {}

    def discover(self) -> list[DiscoveredDocument]:
        return []


def test_disallowed_site_raises_before_fetching():
    spider = _FakeSpider()
    mock_parser = MagicMock()
    mock_parser.can_fetch.return_value = False
    spider._robots_cache["https://blocked.example"] = mock_parser

    with pytest.raises(RobotsDisallowedError):
        spider._check_allowed("https://blocked.example/some-page")


def test_allowed_site_does_not_raise():
    spider = _FakeSpider()
    mock_parser = MagicMock()
    mock_parser.can_fetch.return_value = True
    spider._robots_cache["https://allowed.example"] = mock_parser

    spider._check_allowed("https://allowed.example/some-page")  # should not raise


def test_disallow_error_message_names_the_domain():
    spider = _FakeSpider()
    mock_parser = MagicMock()
    mock_parser.can_fetch.return_value = False
    spider._robots_cache["https://blocked.example"] = mock_parser

    with pytest.raises(RobotsDisallowedError, match="blocked.example"):
        spider._check_allowed("https://blocked.example/some-page")
