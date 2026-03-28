# utils/db.py
import sqlite3
from pathlib import Path
from datetime import datetime
import json
from typing import List, Dict, Optional, Tuple

DB_PATH = Path("ipl.db")


def _connect(row_factory=None):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    if row_factory is not None:
        conn.row_factory = row_factory
    return conn


def get_conn():
    return _connect(sqlite3.Row)


def get_engine():
    """Return a raw SQLite connection for read_sql compatibility."""
    return _connect()

def _rows_to_dicts(rows):
    return [dict(r) for r in rows] if rows else []

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        name TEXT,
        created_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS fixtures (
        match_id TEXT PRIMARY KEY,
        team_a TEXT,
        team_b TEXT,
        match_date TEXT,   -- ISO datetime string
        day TEXT,
        time_ist TEXT,
        venue TEXT,
        week INTEGER       -- Admin-defined "week" number for grouping
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        match_id TEXT PRIMARY KEY,
        winner TEXT        -- team name same as team_a/team_b
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions_match (
        email TEXT,
        match_id TEXT,
        predicted_winner TEXT,
        PRIMARY KEY (email, match_id),
        FOREIGN KEY(email) REFERENCES users(email),
        FOREIGN KEY(match_id) REFERENCES fixtures(match_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions_meta (
        email TEXT PRIMARY KEY,
        playoff_teams TEXT,  -- JSON array of 4
        finalists TEXT,      -- JSON array of 2
        champion TEXT,
        FOREIGN KEY(email) REFERENCES users(email)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS meta_actuals (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)
    conn.commit()
    conn.close()
    _ensure_fixture_columns()


def _ensure_fixture_columns():
    """Add optional day/time/venue columns if the DB was created before they existed."""
    conn = get_conn()
    cur = conn.cursor()
    for column in [
        ("day", "TEXT"),
        ("time_ist", "TEXT"),
        ("venue", "TEXT"),
    ]:
        try:
            cur.execute(f"ALTER TABLE fixtures ADD COLUMN {column[0]} {column[1]};")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc):
                raise
    conn.commit()
    conn.close()

def upsert_user(email: str, name: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO users (email, name, created_at) VALUES (?, ?, ?)
    ON CONFLICT(email) DO UPDATE SET name=excluded.name;
    """, (email.strip().lower(), name.strip(), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_user(email: str) -> Optional[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),))
    row = cur.fetchone()
    conn.close()
    return row

def list_teams() -> List[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT team_a AS t FROM fixtures
        UNION
        SELECT DISTINCT team_b AS t FROM fixtures
        ORDER BY t COLLATE NOCASE;
    """)
    rows = cur.fetchall()
    conn.close()
    return [r["t"] for r in rows]

def insert_fixtures(rows: List[Dict]):
    """rows: list of dicts with keys: match_id, match_date, team_a, team_b, week"""
    _ensure_fixture_columns()
    conn = get_conn()
    cur = conn.cursor()
    for r in rows:
        cur.execute("""
        INSERT OR REPLACE INTO fixtures (match_id, match_date, team_a, team_b, week, day, time_ist, venue)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            str(r["match_id"]),
            r.get("match_date"),
            r.get("team_a"),
            r.get("team_b"),
            int(r.get("week")) if r.get("week") is not None else None,
            r.get("day"),
            r.get("time_ist"),
            r.get("venue"),
        ))
    conn.commit()
    conn.close()

def insert_results(rows: List[Dict]):
    """rows: list of dicts with keys: match_id, winner"""
    conn = get_conn()
    cur = conn.cursor()
    for r in rows:
        cur.execute("""
        INSERT OR REPLACE INTO results (match_id, winner) VALUES (?, ?);
        """, (str(r["match_id"]), r["winner"]))
    conn.commit()
    conn.close()

def list_fixtures() -> List[sqlite3.Row]:
    _ensure_fixture_columns()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.*, r.winner
        FROM fixtures f
        LEFT JOIN results r ON r.match_id = f.match_id
        ORDER BY datetime(f.match_date) ASC, f.match_id ASC;
    """)
    rows = cur.fetchall()
    conn.close()
    return _rows_to_dicts(rows) # <-- return list of dicts

def list_weeks() -> List[int]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT week FROM fixtures ORDER BY week;")
    rows = cur.fetchall()
    conn.close()
    # rows may be dicts now; handle both
    return [ (r["week"] if isinstance(r, dict) else r[0]) for r in rows if (r["week"] if isinstance(r, dict) else r[0]) is not None]


def save_match_prediction(email: str, match_id: str, predicted_winner: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO predictions_match (email, match_id, predicted_winner)
    VALUES (?, ?, ?)
    ON CONFLICT(email, match_id) DO UPDATE SET predicted_winner=excluded.predicted_winner;
    """, (email.strip().lower(), match_id, predicted_winner))
    conn.commit()
    conn.close()


def save_match_predictions_bulk(email: str, predictions: Dict[str, str]):
    """Save many match predictions for a user in one transaction."""
    if not predictions:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO predictions_match (email, match_id, predicted_winner)
        VALUES (?, ?, ?)
        ON CONFLICT(email, match_id) DO UPDATE SET predicted_winner=excluded.predicted_winner;
        """,
        [
            (email.strip().lower(), str(match_id), predicted_winner)
            for match_id, predicted_winner in predictions.items()
        ],
    )
    conn.commit()
    conn.close()

def get_user_match_predictions(email: str) -> Dict[str, str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    SELECT match_id, predicted_winner FROM predictions_match WHERE email=?;
    """, (email.strip().lower(),))
    rows = cur.fetchall()
    conn.close()
    return {r["match_id"]: r["predicted_winner"] for r in rows}

def save_meta_predictions(email: str, playoff_teams: List[str], finalists: List[str], champion: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO predictions_meta (email, playoff_teams, finalists, champion)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(email) DO UPDATE SET playoff_teams=excluded.playoff_teams,
                                    finalists=excluded.finalists,
                                    champion=excluded.champion;
    """, (
        email.strip().lower(),
        json.dumps(list(playoff_teams)),
        json.dumps(list(finalists)),
        champion
    ))
    conn.commit()
    conn.close()

def get_meta_predictions(email: str) -> Optional[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM predictions_meta WHERE email=?", (email.strip().lower(),))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def set_actual_meta(key: str, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO meta_actuals (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value=excluded.value;
    """, (key, json.dumps(value)))
    conn.commit()
    conn.close()

def get_actual_meta(key: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM meta_actuals WHERE key=?", (key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    try:
        return json.loads(row["value"])
    except Exception:
        return row["value"]

def list_users() -> List[sqlite3.Row]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY name COLLATE NOCASE;")
    rows = cur.fetchall()
    conn.close()
    return _rows_to_dicts(rows)