"""
In-process automatic document updater.

This is what removes the manual step. Previously you had to (1) run the
crawler script yourself and (2) POST /admin/reindex so new documents became
searchable. Now the API server itself owns that loop:

  * on startup it schedules a crawl (after `startup_delay_seconds`, so the
    server starts answering requests immediately),
  * it re-crawls every `CN_CRAWLER_INTERVAL_HOURS` hours for as long as the
    server is running,
  * after every successful pass it rebuilds the in-memory search index from
    MongoDB automatically - no /admin/reindex call needed.

Enabled by default; set `CN_CRAWLER_AUTOSTART=false` to turn it off (useful
if you'd rather drive crawls from an external cron / GitHub Actions
schedule, which still works via `python -m app.workers.scheduler --once`).

Caveat worth being explicit about: "automatic" means automatic *while the
backend process is alive*. If you run uvicorn on your laptop and close the
terminal, nothing crawls. Deploy the backend somewhere always-on (the
docker-compose service with `restart: unless-stopped`, a VM, Render,
Railway, Fly, etc.) and it keeps updating itself indefinitely.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import get_settings
from app.services.search.engine import search_engine
from app.services.search.seed_data import load_from_mongo
from app.workers.scheduler import run_once

logger = logging.getLogger("compliance_navigator.auto_updater")


class AutoUpdaterState:
    """Small mutable record of what the background loop has done, exposed
    through GET /admin/auto-update so the UI can show real status instead of
    hardcoded values."""

    def __init__(self) -> None:
        self.enabled: bool = False
        self.running: bool = False
        self.last_started_at: str | None = None
        self.last_finished_at: str | None = None
        self.next_run_at: str | None = None
        self.last_summary: dict | None = None
        self.last_error: str | None = None
        self.indexed_documents: int = 0
        self.total_runs: int = 0

    def as_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "running": self.running,
            "lastStartedAt": self.last_started_at,
            "lastFinishedAt": self.last_finished_at,
            "nextRunAt": self.next_run_at,
            "lastSummary": self.last_summary,
            "lastError": self.last_error,
            "indexedDocuments": self.indexed_documents,
            "totalRuns": self.total_runs,
            "intervalHours": get_settings().crawler_interval_hours,
        }


state = AutoUpdaterState()
_task: asyncio.Task | None = None
_lock = asyncio.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def refresh_index() -> int:
    """Rebuild the search index from MongoDB. Returns document count; leaves
    the current index untouched if Mongo is empty or unreachable."""
    try:
        docs = await load_from_mongo()
    except Exception as exc:  # Mongo down - keep serving the existing index
        logger.warning("Reindex skipped, MongoDB unreachable: %s", exc)
        return state.indexed_documents

    if not docs:
        logger.info("Reindex skipped, MongoDB has no documents yet.")
        return state.indexed_documents

    search_engine.build(docs)
    state.indexed_documents = len(docs)
    logger.info("Search index rebuilt automatically with %d documents.", len(docs))
    return len(docs)


async def run_update_cycle() -> dict:
    """One crawl + reindex pass. Safe to call concurrently - the lock means a
    manual trigger never overlaps the scheduled run."""
    async with _lock:
        state.running = True
        state.last_started_at = _now()
        state.last_error = None
        try:
            # Spiders do blocking HTTP; keep the event loop responsive.
            summary = await run_once()
            state.last_summary = summary
            await refresh_index()
        except Exception as exc:
            logger.exception("Automatic update cycle failed")
            state.last_error = str(exc)
            state.last_summary = None
        finally:
            state.total_runs += 1
            state.running = False
            state.last_finished_at = _now()
        return state.as_dict()


async def _loop() -> None:
    settings = get_settings()
    interval = max(1, settings.crawler_interval_hours) * 3600
    delay = settings.crawler_startup_delay_seconds

    if delay > 0:
        state.next_run_at = _now()
        await asyncio.sleep(delay)

    while True:
        await run_update_cycle()
        state.next_run_at = datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + interval, tz=timezone.utc
        ).isoformat()
        logger.info("Next automatic update at %s", state.next_run_at)
        await asyncio.sleep(interval)


def start(app_loop_enabled: bool | None = None) -> None:
    """Start the background loop. Called from the FastAPI lifespan."""
    global _task
    settings = get_settings()
    enabled = settings.crawler_autostart if app_loop_enabled is None else app_loop_enabled
    state.enabled = enabled

    if not enabled:
        logger.info("Automatic updates disabled (CN_CRAWLER_AUTOSTART=false).")
        return
    if _task and not _task.done():
        return

    _task = asyncio.create_task(_loop(), name="compliance-navigator-auto-updater")
    logger.info(
        "Automatic updates enabled: first crawl in %ss, then every %sh.",
        settings.crawler_startup_delay_seconds,
        settings.crawler_interval_hours,
    )


async def stop() -> None:
    """Cancel the loop cleanly on shutdown."""
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):
            pass
    _task = None
