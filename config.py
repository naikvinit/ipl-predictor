# config.py
from datetime import datetime, timezone
from typing import Optional

# --- IMPORTANT: EDIT THESE FOR YOUR SEASON ---
# Use ISO 8601 with timezone. Default is CET (UTC+02:00 in summer / +01:00 in winter).
CUTOFF_ISO = "2026-03-20T18:00:00+02:00"  # When predictions close (pre-IPL)
ADMIN_CODE = None  # Prefer to set via environment/Secrets. Fallback can be set here (string).

# Scoring system (feel free to tune)
POINTS = {
    "match_winner": 5,   # Correct league match winner
    "playoff_team": 10,   # Each correctly predicted playoff team (4 total)
    "finalist": 15,       # Each correctly predicted finalist (2 total)
    "champion": 20       # Correct champion
}

# Optional: Name your competition
APP_TITLE = "IPL Prediction Challenge"

DEFAULT_CUTOFF_KEY = "cutoff_iso"


def _parse_cutoff_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def cutoff_dt_utc(db_client=None) -> datetime:
    """Return the cutoff datetime in UTC, preferring the DB override if available."""
    if db_client is not None:
        try:
            dynamic_value = db_client.get_actual_meta(DEFAULT_CUTOFF_KEY)
            if isinstance(dynamic_value, str) and dynamic_value.strip():
                return _parse_cutoff_iso(dynamic_value.strip())
        except Exception:
            pass
    return _parse_cutoff_iso(CUTOFF_ISO)