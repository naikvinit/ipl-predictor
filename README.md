# IPL Predictor

Streamlit app for running an IPL prediction challenge: upload fixtures, collect user picks, track leaderboards, and highlight weekly winners. This README walks you (or future collaborators) through setup, database choices, and deployment so the project can be hosted on any Streamlit account with its own data.

## Features

- Secure sign-in via name + email, stored in the database
- Match-by-match predictions with season-wide meta picks (playoffs, finalists, champion)
- Admin tools for uploading fixtures/results data
- Automated scoring logic, read-only public schedule page, weekly winner summaries, and a public team-squads browser
- Supabase/Postgres backend by default (via `utils/db_pg.py`) with an optional lightweight SQLite fallback (`utils/db.py`)

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

By default the app uses Supabase/Postgres via `utils/db_pg.py`. Create a database in Supabase (or any hosted Postgres), then add your connection string as `DB_URL` in `.streamlit/secrets.toml` or the Streamlit Cloud secrets UI. If you prefer a file-based local run, swap the imports back to `utils/db.py` (SQLite) temporarily.

### Add an authorized roster

Before anyone can sign in, populate `data/authorized_users.csv` with the official participant list (header: `email,name`). Only addresses in this file can create new accounts, which prevents typos from polluting the database. You can edit the CSV directly or upload a new version through the Admin tools.

## Switching Databases

| Option | How | When to use |
| ------ | --- | ----------- |
| Supabase/Postgres (default) | `from utils import db_pg as db`, set `DB_URL` secret, optional `db.init_db()` to bootstrap tables | Hosted deployments, team access, persistent cloud storage |
| SQLite (legacy) | switch imports back to `from utils import db as db` | Quick local experiments without a Postgres instance |

For Supabase/Postgres:
1. Create a new Supabase project (or any Postgres database) and grab the connection string.
2. Add `DB_URL="postgresql://user:pass@host:5432/db"` to `.streamlit/secrets.toml` locally and to Streamlit Cloud secrets in production.
3. Ensure the tables exist (run `db.init_db()` once or execute the SQL in `utils/db_pg.py`).

For SQLite fallback, simply swap the imports and the app will recreate `ipl.db` automatically (make sure the file is writable in your environment). The file lives at the repo root (e.g., `/app/<repo>/ipl.db` on Streamlit Cloud) and is **not** committed to Git—download or copy it manually if you need backups.

## Populating Data

- Fixtures: edit `data/fixtures_template.csv` (columns: match_id, match_date/date, team_a, team_b, week, time_ist, venue, optional day), then use the Admin page (`pages/6_Admin.py`) to upload.
- Results: update `data/results_template.csv` and upload once real outcomes exist.
- Authorized players: maintain `data/authorized_users.csv` via the Admin → **Manage Authorized Players** section (upload a CSV or edit inline).
- Public schedule: `pages/4_Schedule.py` renders the fixture list for everyone (no login required).
- Team rosters: `pages/5_Team_Squads.py` lists every squad grouped by role (also public).
- Team logos: place PNG files under `assets/logos/` using the names in `TEAM_LOGOS` inside `utils/ui.py`.

### Backing up SQLite on Streamlit Cloud

If you deploy with the SQLite adapter, open the Admin page and expand **💾 Database Backup** to download the current `ipl.db`. Store the file somewhere safe; restoring is as simple as uploading the file back into the Streamlit workspace (or replacing it locally) before restarting the app. Postgres/Supabase deployments should instead rely on their managed backup tooling.

## Gameplay Notes

- **Points system** (configurable via `POINTS`): 5 pts per correct match winner, 10 per playoff team, 15 per finalist, 20 for champion.
- **Per-match locking**: The Make Predictions page prevents edits after the global cutoff *and* individually locks matches once their scheduled start time passes, so reopening the cutoff for new fixtures won’t revive older picks.
- **Weekly tie-breaker**: Weekly Winners ranks by total weekly points, then breaks ties using the longest streak of consecutive correct picks within that week. The page shows both the points and streak data.
- **Privacy**: Leaderboard and Weekly Winners pages display player names only (emails stay hidden) to avoid leaking login addresses.

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
