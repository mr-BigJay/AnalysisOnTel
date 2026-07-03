"""SQLite storage for predictions and outcomes."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from config import DATA_DIR, PREDICTIONS_DB

SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    eval_after TEXT NOT NULL,
    source TEXT NOT NULL,
    symbol TEXT NOT NULL DEFAULT 'BTC/USD',
    bias TEXT NOT NULL,
    action TEXT NOT NULL,
    price_at_signal REAL NOT NULL,
    entry_low REAL,
    entry_high REAL,
    stop_loss REAL,
    take_profit REAL,
    confidence INTEGER,
    quality_score INTEGER,
    checklist_score INTEGER,
    daily_trend TEXT,
    h4_trend TEXT,
    h1_trend TEXT,
    prediction_note TEXT,
    outcome TEXT NOT NULL DEFAULT 'pending',
    outcome_price REAL,
    outcome_at TEXT,
    outcome_note TEXT
);

CREATE INDEX IF NOT EXISTS idx_predictions_outcome ON predictions(outcome);
CREATE INDEX IF NOT EXISTS idx_predictions_created ON predictions(created_at);
"""


@dataclass
class PredictionRow:
    id: int
    created_at: str
    eval_after: str
    source: str
    symbol: str
    bias: str
    action: str
    price_at_signal: float
    entry_low: float | None
    entry_high: float | None
    stop_loss: float | None
    take_profit: float | None
    confidence: int | None
    quality_score: int | None
    checklist_score: int | None
    daily_trend: str | None
    h4_trend: str | None
    h1_trend: str | None
    prediction_note: str | None
    outcome: str
    outcome_price: float | None
    outcome_at: str | None
    outcome_note: str | None


def init_db(db_path: Path | None = None) -> Path:
    path = db_path or PREDICTIONS_DB
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    return path


@contextmanager
def get_conn(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = init_db(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def insert_prediction(
    *,
    source: str,
    symbol: str,
    bias: str,
    action: str,
    price_at_signal: float,
    eval_after: str,
    entry_low: float | None = None,
    entry_high: float | None = None,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    confidence: int | None = None,
    quality_score: int | None = None,
    checklist_score: int | None = None,
    daily_trend: str | None = None,
    h4_trend: str | None = None,
    h1_trend: str | None = None,
    prediction_note: str | None = None,
) -> int:
    created_at = utc_now_iso()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO predictions (
                created_at, eval_after, source, symbol, bias, action, price_at_signal,
                entry_low, entry_high, stop_loss, take_profit,
                confidence, quality_score, checklist_score,
                daily_trend, h4_trend, h1_trend, prediction_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                eval_after,
                source,
                symbol,
                bias,
                action,
                price_at_signal,
                entry_low,
                entry_high,
                stop_loss,
                take_profit,
                confidence,
                quality_score,
                checklist_score,
                daily_trend,
                h4_trend,
                h1_trend,
                prediction_note,
            ),
        )
        return int(cur.lastrowid)


def get_recent_duplicate(bias: str, action: str, within_minutes: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM predictions
            WHERE bias = ? AND action = ?
              AND datetime(created_at) >= datetime('now', ?)
            LIMIT 1
            """,
            (bias, action, f"-{within_minutes} minutes"),
        ).fetchone()
        return row is not None


def fetch_pending_for_eval() -> list[PredictionRow]:
    now = utc_now_iso()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM predictions
            WHERE outcome = 'pending' AND eval_after <= ?
            ORDER BY eval_after ASC
            """,
            (now,),
        ).fetchall()
    return [_row_to_dataclass(r) for r in rows]


def update_outcome(
    prediction_id: int,
    outcome: str,
    outcome_price: float | None,
    outcome_note: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE predictions
            SET outcome = ?, outcome_price = ?, outcome_at = ?, outcome_note = ?
            WHERE id = ?
            """,
            (outcome, outcome_price, utc_now_iso(), outcome_note, prediction_id),
        )


def fetch_stats(since_days: int | None = None) -> list[PredictionRow]:
    with get_conn() as conn:
        if since_days is None:
            rows = conn.execute(
                "SELECT * FROM predictions WHERE outcome != 'pending' ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM predictions
                WHERE outcome != 'pending'
                  AND datetime(created_at) >= datetime('now', ?)
                ORDER BY created_at DESC
                """,
                (f"-{since_days} days",),
            ).fetchall()
    return [_row_to_dataclass(r) for r in rows]


def count_by_outcome(since_days: int | None = None) -> dict[str, int]:
    query = "SELECT outcome, COUNT(*) AS c FROM predictions WHERE outcome != 'pending'"
    params: tuple = ()
    if since_days is not None:
        query += " AND datetime(created_at) >= datetime('now', ?)"
        params = (f"-{since_days} days",)
    query += " GROUP BY outcome"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return {str(r["outcome"]): int(r["c"]) for r in rows}


def count_pending() -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM predictions WHERE outcome = 'pending'"
        ).fetchone()
        return int(row["c"]) if row else 0


def fetch_recent(limit: int = 5) -> list[PredictionRow]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_dataclass(r) for r in rows]


def _row_to_dataclass(row: sqlite3.Row) -> PredictionRow:
    return PredictionRow(
        id=int(row["id"]),
        created_at=str(row["created_at"]),
        eval_after=str(row["eval_after"]),
        source=str(row["source"]),
        symbol=str(row["symbol"]),
        bias=str(row["bias"]),
        action=str(row["action"]),
        price_at_signal=float(row["price_at_signal"]),
        entry_low=row["entry_low"],
        entry_high=row["entry_high"],
        stop_loss=row["stop_loss"],
        take_profit=row["take_profit"],
        confidence=row["confidence"],
        quality_score=row["quality_score"],
        checklist_score=row["checklist_score"],
        daily_trend=row["daily_trend"],
        h4_trend=row["h4_trend"],
        h1_trend=row["h1_trend"],
        prediction_note=row["prediction_note"],
        outcome=str(row["outcome"]),
        outcome_price=row["outcome_price"],
        outcome_at=row["outcome_at"],
        outcome_note=row["outcome_note"],
    )
