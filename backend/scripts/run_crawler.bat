@echo off
REM Runs the crawler once, then refreshes the live search index.
REM This is the script Windows Task Scheduler calls on a timer — see
REM docs/ROADMAP.md and the README for how to register it.

cd /d %~dp0\..

call .venv\Scripts\activate.bat

echo [%date% %time%] Starting crawl... >> crawl_log.txt
python -m app.workers.scheduler --once >> crawl_log.txt 2>&1

echo [%date% %time%] Refreshing search index... >> crawl_log.txt
curl -X POST http://localhost:8000/api/v1/admin/reindex >> crawl_log.txt 2>&1

echo [%date% %time%] Done. >> crawl_log.txt
