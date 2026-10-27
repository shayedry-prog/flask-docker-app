"""Database helpers.

Works with PostgreSQL in Docker (DATABASE_URL=postgresql://...) and with
SQLite for fast local tests (DATABASE_URL=sqlite:///path/to/file.db).
"""

import sqlite3
import time

from flask import current_app, g

SCHEMAS = {
    "postgres": """
        CREATE TABLE IF NOT EXISTS tasks (
            id          SERIAL PRIMARY KEY,
            title       TEXT NOT NULL,
            done        BOOLEAN NOT NULL DEFAULT FALSE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """,
    "sqlite": """
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            done        BOOLEAN NOT NULL DEFAULT 0,
            created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
}


def _engine(url):
    return "sqlite" if url.startswith("sqlite:///") else "postgres"


def _connect(url):
    if _engine(url) == "sqlite":
        conn = sqlite3.connect(url.removeprefix("sqlite:///"))
        conn.row_factory = sqlite3.Row
        return conn

    import psycopg  # imported here so SQLite-only test runs don't need it
    from psycopg.rows import dict_row

    return psycopg.connect(url, row_factory=dict_row)


def get_db():
    """Return a connection for the current request (opened on first use)."""
    if "db" not in g:
        g.db = _connect(current_app.config["DATABASE_URL"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, params=(), one=False, commit=False):
    """Run SQL written with %s placeholders on either engine; return dict rows."""
    url = current_app.config["DATABASE_URL"]
    if _engine(url) == "sqlite":
        sql = sql.replace("%s", "?")

    db = get_db()
    cur = db.cursor()
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()] if cur.description else []
    if commit:
        db.commit()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def init_db(app, retries=10, delay=2):
    """Create tables, retrying while the database container starts up."""
    url = app.config["DATABASE_URL"]
    for attempt in range(1, retries + 1):
        try:
            conn = _connect(url)
            conn.execute(SCHEMAS[_engine(url)])
            conn.commit()
            conn.close()
            return
        except Exception as exc:  # noqa: BLE001 - any DB error means "not ready yet"
            if attempt == retries:
                raise
            app.logger.warning("DB not ready (attempt %s/%s): %s", attempt, retries, exc)
            time.sleep(delay)
