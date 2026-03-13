# IPL Predictor

Streamlit app for running an IPL prediction challenge: upload fixtures, collect user picks, track leaderboards, and highlight weekly winners. This README walks you (or future collaborators) through setup, database choices, and deployment so the project can be hosted on any Streamlit account with its own data.

## Features

- Secure sign-in via name + email, stored in the database
- Match-by-match predictions with season-wide meta picks (playoffs, finalists, champion)
- Admin tools for uploading fixtures/results data
- Automated scoring logic and weekly winner summaries
- Optional Supabase/Postgres backend (via `utils/db_pg.py`) or lightweight SQLite (default `utils/db.py`)

## Repository Layout

```
app.py                 # Landing page + sign-in
pages/                 # Streamlit multipage routes (predictions, leaderboard, admin)
utils/                 # Database adapters, scoring logic, reusable UI helpers
config.py              # Global settings/cutoffs/point values
styles.css             # Custom theme loaded on every page
assets/logos/          # Team logos referenced by utils/ui.py
```

## Prerequisites

- Python 3.10+
- Streamlit account (for cloud deployment) or local environment
- Data source for fixtures/results (CSV templates live under `data/`)

## Quick Start (Local)

```bash
# 1. Clone the repo
 git clone <your-fork-url> && cd ipl-predictor

# 2. Create & activate a virtual environment
 python -m venv .venv
 .venv\Scripts\activate      # Windows
 source .venv/bin/activate    # macOS / Linux

# 3. Install dependencies
 pip install -r requirements.txt

# 4. Launch Streamlit locally
 streamlit run app.py
```

By default the app uses SQLite (`utils/db.py`) and creates `ipl.db` in the project root. This keeps each deployment isolated—delete the file if you need a fresh database.

### Add an authorized roster

Before anyone can sign in, populate `data/authorized_users.csv` with the official participant list (header: `email,name`). Only addresses in this file can create new accounts, which prevents typos from polluting the database. You can edit the CSV directly or upload a new version through the Admin tools.

## Switching Databases

| Option | How | When to use |
| ------ | --- | ----------- |
| SQLite (default) | `from utils import db as db` | Simple self-contained deployment, Streamlit Cloud, small leagues |
| Supabase/Postgres | change imports to `db_pg`, configure credentials in `utils/db_pg.py` or Streamlit secrets | Need multi-user scale, shared hosted DB |

1. For SQLite, no extra steps—`db.init_db()` runs automatically.
2. For Supabase/Postgres:
   - Copy `utils/db_pg.py` to your liking, set connection URL via environment variable or `.streamlit/secrets.toml`.
   - Update every file currently doing `from utils import db as db` to instead import `db_pg`.
   - Make sure required tables exist (use SQL in `utils/db_pg.py` or run migrations manually).

## Populating Data

- Fixtures: edit `data/fixtures_template.csv`, then use the Admin page (`pages/4_Admin.py`) to upload.
- Results: update `data/results_template.csv` and upload once real outcomes exist.
- Authorized players: maintain `data/authorized_users.csv` via the Admin → **Manage Authorized Players** section (upload a CSV or edit inline).
- Team logos: place PNG files under `assets/logos/` using the names in `TEAM_LOGOS` inside `utils/ui.py`.

## Configuration

Key settings live in `config.py`:

- `APP_TITLE`: text shown in the browser tab
- `POINTS`: scoring weights for winners/playoffs/finals/champion
- `cutoff_dt_utc()`: function defining when predictions lock (update before each match phase)

## Deploying to Streamlit Community Cloud

1. Push your fork to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io/), create a new app pointing to `app.py` in your repo.
3. Add secrets/environment variables if using a remote DB (under *App settings → Secrets*).
4. Press **Deploy**. Streamlit Cloud installs dependencies from `requirements.txt` automatically.
5. Upload fixtures via the Admin page to seed the new database.

> 💡 Each Streamlit deployment has its own filesystem. If you stay on SQLite, every redeploy reuses the `ipl.db` file unless you delete it manually in the workspace. Supabase/Postgres keeps data external and persistent.

## Collaboration Tips

- Use branches/pull requests for any scoring logic or schema changes.
- Check in CSV templates and logos, but **not** generated databases (`ipl.db`) or user data.
- Document new environment variables in this README to help future deployers.

## Support / Contributions

Bug reports and feature ideas are welcome. Open an issue or pull request describing:

- Environment (local vs Streamlit Cloud)
- Database backend (SQLite vs Supabase)
- Steps to reproduce + expected behavior

Enjoy running your own IPL predictor league! 🎉
