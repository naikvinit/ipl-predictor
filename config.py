# config.py
from datetime import datetime, timezone

# --- IMPORTANT: EDIT THESE FOR YOUR SEASON ---
# Use ISO 8601 with timezone. Example shown is IST (UTC+05:30).
CUTOFF_ISO = "2026-03-20T18:00:00+05:30"  # When predictions close (pre-IPL)
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

def cutoff_dt_utc() -> datetime:
    """Return the cutoff datetime in UTC."""
    # We parse as naive then assume it's a valid ISO with offset; Python will parse it as aware.
    dt = datetime.fromisoformat(CUTOFF_ISO)
    if dt.tzinfo is None:
        # If no tz, assume UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)