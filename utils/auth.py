from __future__ import annotations
import csv
from functools import lru_cache
from pathlib import Path
from typing import Dict

ROSTER_PATH = Path("data/authorized_users.csv")


def _iter_rows(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            yield raw


@lru_cache(maxsize=1)
def load_authorized_users() -> Dict[str, str]:
    """Return a mapping of authorized email -> canonical name."""
    if not ROSTER_PATH.exists():
        return {}

    try:
        reader = csv.DictReader(_iter_rows(ROSTER_PATH))
    except Exception:
        return {}

    allowed = {}
    for row in reader:
        email = (row.get("email") or "").strip().lower()
        name = (row.get("name") or "").strip()
        if not email:
            continue
        allowed[email] = name or allowed.get(email) or "Player"
    return allowed


def refresh_authorized_users():
    load_authorized_users.cache_clear()
    return load_authorized_users()
