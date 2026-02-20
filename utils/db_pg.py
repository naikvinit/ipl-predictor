"""
PostgreSQL (Supabase) data access layer for the IPL Predictor app.

- Uses SQLAlchemy + psycopg2 behind the scenes.
- Exposes a near-identical API to the original SQLite utils/db.py so you can switch with minimal changes.
- Reads connection string from Streamlit secrets: st.secrets["DB_URL"].
- All functions return plain Python types (dicts, lists, ints) to be pandas/Streamlit-friendly.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Result


# ----------------------------
# Engine / Connection helpers
# ----------------------------

_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Create (or reuse) a global SQLAlchemy engine based on Streamlit secrets."""
    global _engine
    if _engine is not None:
        return _engine

    # Expecting: st.secrets["DB_URL"] = "postgresql://user:password@host:5432/dbname"
    db_url = st.secrets.get("DB_URL")
    if not db_url:
        raise RuntimeError(
            "DB_URL not found in Streamlit secrets. "
            "Add it under App → Settings → Secrets or .streamlit/secrets.toml"
        )

    # You can tune pool size if needed
    _engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        future=True,  # Use SQLAlchemy 2.0-style engine
    )
    return _engine


def _fetchall(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Run a SELECT and return list of dicts."""
    eng = get_engine()
    with eng.connect() as conn:
        result: Result = conn.execute(text(query), params or {})
        # SQLAlchemy 2.0 returns Row objects; .mappings() yields dict-like mappings
        rows = result.mappings().all()
        return [dict(r) for r in rows]


def _fetchone(query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Run a SELECT and return a single dict or None."""
    eng = get_engine()
    with eng.connect() as conn:
        result: Result = conn.execute(text(query), params or {})
        row = result.mappings().first()
        return dict(row) if row else None


def _execute(query: str, params: Optional[Dict[str, Any]] = None) -> None:
    """Run an INSERT/UPDATE/DELETE in a transaction."""
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(text(query), params or {})


def _executemany(query: str, rows: List[Dict[str, Any]]) -> None:
    """Run many INSERT/UPDATE/DELETE with a single statement in a transaction."""
    if not rows:
        return
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(text(query), rows)


# ----------------------------
# Schema init (optional)
# ----------------------------

def init_db() -> None:
    """
    Create tables if they don't exist. This mirrors the SQLite schema.
    You can also create this via Supabase SQL editor; this function is convenient for local dev.
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        name TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS fixtures (
        match_id INTEGER PRIMARY KEY,
        match_date TEXT,   -- store ISO datetime string
        team_a TEXT,
        team_b TEXT,
        week INTEGER
    );

    CREATE TABLE IF NOT EXISTS results (
        match_id INTEGER PRIMARY KEY REFERENCES fixtures(match_id) ON DELETE CASCADE,
        winner TEXT
    );

    CREATE TABLE IF NOT EXISTS predictions_match (
        email TEXT REFERENCES users(email) ON DELETE CASCADE,
        match_id INTEGER REFERENCES fixtures(match_id) ON DELETE CASCADE,
        predicted_winner TEXT,
        PRIMARY KEY (email, match_id)
    );

    CREATE TABLE IF NOT EXISTS predictions_meta (
        email TEXT PRIMARY KEY REFERENCES users(email) ON DELETE CASCADE,
        playoff_teams TEXT,  -- JSON string
        finalists TEXT,      -- JSON string
        champion TEXT
    );

    CREATE TABLE IF NOT EXISTS meta_actuals (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """
    # Execute the whole block in one transaction (Postgres supports multi-statement)
    eng = get_engine()
    with eng.begin() as conn:
        for statement in [s.strip() for s in ddl.split(";") if s.strip()]:
            conn.execute(text(statement + ";"))


# ----------------------------
# Users
# ----------------------------

def upsert_user(email: str, name: str) -> None:
    _execute(
        """
        INSERT INTO users (email, name, created_at)
        VALUES (:email, :name, NOW())
        ON CONFLICT (email)
        DO UPDATE SET name = EXCLUDED.name;
        """,
        {"email": email.strip().lower(), "name": name.strip()},
    )


def get_user(email: str) -> Optional[Dict[str, Any]]:
    return _fetchone(
        "SELECT email, name, created_at FROM users WHERE email = :email;",
        {"email": email.strip().lower()},
    )


def list_users() -> List[Dict[str, Any]]:
    return _fetchall("SELECT email, name, created_at FROM users ORDER BY name COLLATE \"C\";")
    # Note: COLLATE "C" ensures a deterministic order; adjust if you prefer ICU collations.


# ----------------------------
# Fixtures & Results
# ----------------------------

def insert_fixtures(rows: List[Dict[str, Any]]) -> None:
    """
    rows: list of dicts with keys match_id, match_date, team_a, team_b, week
    """
    # Use UPSERT to allow re-imports/updates
    _executemany(
        """
        INSERT INTO fixtures (match_id, match_date, team_a, team_b, week)
        VALUES (:match_id, :match_date, :team_a, :team_b, :week)
        ON CONFLICT (match_id)
        DO UPDATE SET
            match_date = EXCLUDED.match_date,
            team_a     = EXCLUDED.team_a,
            team_b     = EXCLUDED.team_b,
            week       = EXCLUDED.week;
        """,
        rows,
    )


def insert_results(rows: List[Dict[str, Any]]) -> None:
    """
    rows: list of dicts with keys match_id, winner
    """
    _executemany(
        """
        INSERT INTO results (match_id, winner)
        VALUES (:match_id, :winner)
        ON CONFLICT (match_id)
        DO UPDATE SET winner = EXCLUDED.winner;
        """,
        rows,
    )


def list_fixtures() -> List[Dict[str, Any]]:
    """
    Return fixtures joined with results (winner), ordered by match_date then match_id.
    Columns: match_id, match_date, team_a, team_b, week, winner
    """
    return _fetchall(
        """
        SELECT f.match_id, f.match_date, f.team_a, f.team_b, f.week, r.winner
        FROM fixtures f
        LEFT JOIN results r ON r.match_id = f.match_id
        ORDER BY f.match_date NULLS LAST, f.match_id;
        """
    )


def list_weeks() -> List[int]:
    rows = _fetchall("SELECT DISTINCT week FROM fixtures WHERE week IS NOT NULL ORDER BY week;")
    return [int(r["week"]) for r in rows if r.get("week") is not None]


def list_teams() -> List[str]:
    """
    Unique team names from team_a and team_b columns.
    """
    rows = _fetchall(
        """
        SELECT t FROM (
            SELECT DISTINCT team_a AS t FROM fixtures
            UNION
            SELECT DISTINCT team_b AS t FROM fixtures
        ) q
        WHERE t IS NOT NULL
        ORDER BY t COLLATE "C";
        """
    )
    return [r["t"] for r in rows]


# ----------------------------
# Predictions (match-level)
# ----------------------------

def save_match_prediction(email: str, match_id: str, predicted_winner: str) -> None:
    _execute(
        """
        INSERT INTO predictions_match (email, match_id, predicted_winner)
        VALUES (:email, :match_id, :predicted_winner)
        ON CONFLICT (email, match_id)
        DO UPDATE SET predicted_winner = EXCLUDED.predicted_winner;
        """,
        {
            "email": email.strip().lower(),
            "match_id": str(match_id),
            "predicted_winner": predicted_winner,
        },
    )


def get_user_match_predictions(email: str) -> Dict[str, str]:
    rows = _fetchall(
        """
        SELECT match_id, predicted_winner
        FROM predictions_match
        WHERE email = :email;
        """,
        {"email": email.strip().lower()},
    )
    return {str(r["match_id"]): r["predicted_winner"] for r in rows}


# ----------------------------
# Predictions (meta)
# ----------------------------

def save_meta_predictions(email: str, playoff_teams: List[str], finalists: List[str], champion: str) -> None:
    _execute(
        """
        INSERT INTO predictions_meta (email, playoff_teams, finalists, champion)
        VALUES (:email, :playoff_teams, :finalists, :champion)
        ON CONFLICT (email)
        DO UPDATE SET
            playoff_teams = EXCLUDED.playoff_teams,
            finalists     = EXCLUDED.finalists,
            champion      = EXCLUDED.champion;
        """,
        {
            "email": email.strip().lower(),
            "playoff_teams": json.dumps(list(playoff_teams)),
            "finalists": json.dumps(list(finalists)),
            "champion": champion,
        },
    )


def get_meta_predictions(email: str) -> Optional[Dict[str, Any]]:
    return _fetchone(
        """
        SELECT email, playoff_teams, finalists, champion
        FROM predictions_meta
        WHERE email = :email;
        """,
        {"email": email.strip().lower()},
    )


# ----------------------------
# Actuals (playoffs, finalists, champion)
# ----------------------------

def set_actual_meta(key: str, value: Any) -> None:
    _execute(
        """
        INSERT INTO meta_actuals (key, value)
        VALUES (:key, :value)
        ON CONFLICT (key)
        DO UPDATE SET value = EXCLUDED.value;
        """,
        {"key": key, "value": json.dumps(value)},
    )


def get_actual_meta(key: str) -> Any:
    row = _fetchone("SELECT value FROM meta_actuals WHERE key = :key;", {"key": key})
    if not row or row.get("value") is None:
        return None
    try:
        return json.loads(row["value"])
    except Exception:
        # If value wasn't valid JSON, return raw string
        return row["value"]