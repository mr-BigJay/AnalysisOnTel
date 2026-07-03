"""Self-tuning parameters based on historical prediction performance."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import DATA_DIR
from tracking.database import count_by_outcome, get_conn, utc_now_iso

logger = logging.getLogger(__name__)

TUNING_FILE = DATA_DIR / "tuning_params.json"
MIN_SAMPLES_FOR_TUNE = 15
TUNE_COOLDOWN_HOURS = 24
MAX_DELTA_PER_TUNE = 2


@dataclass
class TuningParams:
    min_entry_score: int = 70
    min_checklist_score: int = 70
    min_checklist_passed: int = 8
    last_tune_at: str | None = None
    last_tune_reason: str | None = None


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def load_params() -> TuningParams:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not TUNING_FILE.exists():
        return TuningParams()
    try:
        data = json.loads(TUNING_FILE.read_text(encoding="utf-8"))
        return TuningParams(**data)
    except Exception:
        logger.exception("Failed to load tuning params, using defaults")
        return TuningParams()


def save_params(params: TuningParams) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TUNING_FILE.write_text(json.dumps(asdict(params), indent=2), encoding="utf-8")


def get_min_entry_score() -> int:
    return load_params().min_entry_score


def get_min_checklist_score() -> int:
    return load_params().min_checklist_score


def get_min_checklist_passed() -> int:
    return load_params().min_checklist_passed


def _ensure_tuning_history_table() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tuning_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tuned_at TEXT NOT NULL,
                reason TEXT NOT NULL,
                win_rate_30d REAL,
                samples_30d INTEGER,
                old_params TEXT NOT NULL,
                new_params TEXT NOT NULL
            )
            """
        )


def _win_rate_days(days: int) -> tuple[float | None, int]:
    counts = count_by_outcome(days)
    wins = counts.get("win", 0)
    losses = counts.get("loss", 0)
    decided = wins + losses
    if decided == 0:
        return None, 0
    return (wins / decided) * 100, decided


def _can_tune_now(params: TuningParams) -> bool:
    if not params.last_tune_at:
        return True
    last = datetime.strptime(params.last_tune_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last >= timedelta(hours=TUNE_COOLDOWN_HOURS)


def auto_tune() -> TuningParams | None:
    """
    Adjust thresholds based on 30-day win rate.
    Returns new params if changed, else None.
    """
    _ensure_tuning_history_table()
    params = load_params()
    if not _can_tune_now(params):
        return None

    rate_30, samples_30 = _win_rate_days(30)
    if samples_30 < MIN_SAMPLES_FOR_TUNE or rate_30 is None:
        logger.info("Auto-tune skipped: samples=%s (need %s)", samples_30, MIN_SAMPLES_FOR_TUNE)
        return None

    rate_7, samples_7 = _win_rate_days(7)
    old = TuningParams(**asdict(params))
    reason_parts: list[str] = []
    changed = False

    if rate_30 < 50:
        params.min_entry_score = _clamp(params.min_entry_score + 2, 62, 85)
        params.min_checklist_score = _clamp(params.min_checklist_score + 2, 60, 85)
        reason_parts.append(f"Win Rate 30d پایین ({rate_30:.1f}%) → سخت‌گیری بیشتر")
        changed = True
    elif rate_30 > 62 and samples_30 >= 20:
        params.min_entry_score = _clamp(params.min_entry_score - 1, 62, 85)
        reason_parts.append(f"Win Rate 30d خوب ({rate_30:.1f}%) → کمی انعطاف بیشتر")
        changed = True

    if rate_7 is not None and samples_7 >= 10 and rate_7 < 45:
        params.min_checklist_passed = _clamp(params.min_checklist_passed + 1, 6, 9)
        reason_parts.append(f"Win Rate 7d ضعیف ({rate_7:.1f}%) → چک‌لیست سخت‌تر")
        changed = True

    if not changed:
        return None

    params.last_tune_at = utc_now_iso()
    params.last_tune_reason = " | ".join(reason_parts)
    save_params(params)

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO tuning_history (tuned_at, reason, win_rate_30d, samples_30d, old_params, new_params)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                params.last_tune_at,
                params.last_tune_reason,
                rate_30,
                samples_30,
                json.dumps(asdict(old)),
                json.dumps(asdict(params)),
            ),
        )

    logger.info("Auto-tune applied: %s", params.last_tune_reason)
    return params


def format_tuning_status() -> str:
    p = load_params()
    lines = [
        "━━ پارامترهای فعلی (خود-اصلاح) ━━",
        f"حد ورود: <b>{p.min_entry_score}</b>",
        f"حد چک‌لیست: <b>{p.min_checklist_score}</b>",
        f"حداقل ✅ چک‌لیست: <b>{p.min_checklist_passed}/10</b>",
    ]
    if p.last_tune_at:
        lines.append(f"آخرین اصلاح: {p.last_tune_at}")
        if p.last_tune_reason:
            lines.append(f"دلیل: {p.last_tune_reason}")
    else:
        lines.append("هنوز خود-اصلاح انجام نشده (نیاز: ۱۵+ برد/باخت)")
    return "\n".join(lines)
