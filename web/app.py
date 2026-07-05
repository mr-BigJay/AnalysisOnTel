"""FastAPI web dashboard."""

from __future__ import annotations

import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from analysis.engine import load_report, run_analysis, save_report
from config import REFRESH_INTERVAL_MINUTES, WEB_PASSWORD

logger = logging.getLogger(__name__)
security = HTTPBasic(auto_error=False)
templates = Jinja2Templates(directory="web/templates")
_scheduler: BackgroundScheduler | None = None


def _auth(credentials: HTTPBasicCredentials | None = Depends(security)) -> None:
    if not WEB_PASSWORD:
        return
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth required")
    ok_user = secrets.compare_digest(credentials.username, "admin")
    ok_pass = secrets.compare_digest(credentials.password, WEB_PASSWORD)
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


def _refresh_report() -> None:
    try:
        report = run_analysis()
        save_report(report)
        logger.info("Report refreshed: %s %s", report.verdict, report.generated_at)
    except Exception:
        logger.exception("Report refresh failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    _refresh_report()
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _refresh_report,
        "interval",
        minutes=REFRESH_INTERVAL_MINUTES,
        id="report_refresh",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — refresh every %s min", REFRESH_INTERVAL_MINUTES)
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)


app = FastAPI(title="AnalysisOnTel", version="2.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, _: None = Depends(_auth)):
    report = load_report()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"report": report, "now": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")},
    )


@app.get("/api/report")
async def api_report(_: None = Depends(_auth)):
    report = load_report()
    if not report:
        raise HTTPException(404, "No report yet")
    return JSONResponse(report)


@app.post("/api/report/refresh")
async def api_refresh(_: None = Depends(_auth)):
    await asyncio.to_thread(_refresh_report)
    report = load_report()
    if not report:
        raise HTTPException(500, "Refresh failed")
    return JSONResponse({"ok": True, "generated_at": report.get("generated_at")})


@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}
