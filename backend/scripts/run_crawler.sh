#!/bin/bash
# Runs the crawler once, then refreshes the live search index.
# This is the script cron calls on a timer — see docs/ROADMAP.md and the
# README for how to register it.

cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "[$(date)] Starting crawl..." >> crawl_log.txt
python -m app.workers.scheduler --once >> crawl_log.txt 2>&1

echo "[$(date)] Refreshing search index..." >> crawl_log.txt
curl -X POST http://localhost:8000/api/v1/admin/reindex >> crawl_log.txt 2>&1

echo "[$(date)] Done." >> crawl_log.txt
