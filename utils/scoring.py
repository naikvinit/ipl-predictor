# utils/scoring.py
from contextlib import contextmanager
from typing import Dict, List, Tuple
import pandas as pd

from utils import db_pg as db      # Supabase
#from utils import db as db       # (optional) SQLite local
from config import POINTS


@contextmanager
def _read_handle():
    """Yield a DB handle that works for both SQLAlchemy engines and sqlite3 connections."""
    handle = db.get_engine()
    try:
        yield handle
    finally:
        # sqlite3 connections expose .cursor; SQLAlchemy engines do not.
        if hasattr(handle, "cursor"):
            try:
                handle.close()
            except Exception:
                pass

def _load_baseframes():
    with _read_handle() as engine:
        fixtures = pd.read_sql_query("""
            SELECT f.match_id, f.match_date, f.team_a, f.team_b, f.week, r.winner
            FROM fixtures f
            LEFT JOIN results r ON r.match_id = f.match_id
            ORDER BY f.match_date, f.match_id;
        """, engine)

        users = pd.read_sql_query("SELECT email, name FROM users;", engine)
    if not fixtures.empty:
        fixtures = fixtures.reset_index(drop=True)
        fixtures["fixture_order"] = fixtures.index
    else:
        fixtures["fixture_order"] = pd.Series(dtype=int)
    return fixtures, users

def compute_match_scores() -> pd.DataFrame:
    """Returns per-user per-match scoring joined with fixtures and results."""
    fixtures, users = _load_baseframes()

    # Predictions (match-level)
    with _read_handle() as engine:
        pred = pd.read_sql_query("SELECT * FROM predictions_match", engine)

    if pred.empty:
        return pd.DataFrame()

    # Join predicted with actual results
    merge_cols = ["match_id", "week", "winner"]
    if "fixture_order" in fixtures.columns:
        merge_cols.append("fixture_order")
    df = pred.merge(fixtures[merge_cols], on="match_id", how="left")

    def score_row(r):
        if pd.isna(r["winner"]):
            return 0
        return POINTS["match_winner"] if (r["predicted_winner"] == r["winner"]) else 0

    df["match_points"] = df.apply(score_row, axis=1)

    # Attach user names
    if not users.empty:
        df = df.merge(users[["email", "name"]], on="email", how="left")

    return df

def compute_meta_scores() -> pd.DataFrame:
    """Returns per-user meta (playoffs/finalists/champion) scores as columns."""
    with _read_handle() as engine:
        meta = pd.read_sql_query("SELECT * FROM predictions_meta", engine)

    if meta.empty:
        return pd.DataFrame(columns=["email", "playoff_points", "finalist_points", "champion_points", "meta_total"])

    # Load actuals
    actual_playoffs = set(db.get_actual_meta("playoff_teams") or [])
    actual_finalists = set(db.get_actual_meta("finalists") or [])
    actual_champion = db.get_actual_meta("champion")

    def calc_row(r):
        import json
        try:
            playoffs_pred = set(json.loads(r["playoff_teams"] or "[]"))
            finalists_pred = set(json.loads(r["finalists"] or "[]"))
            champion_pred = r["champion"]
        except Exception:
            playoffs_pred, finalists_pred, champion_pred = set(), set(), None

        playoff_pts = sum(POINTS["playoff_team"] for t in playoffs_pred if t in actual_playoffs)
        finalist_pts = sum(POINTS["finalist"] for t in finalists_pred if t in actual_finalists)
        champion_pts = POINTS["champion"] if champion_pred and actual_champion and champion_pred == actual_champion else 0

        return pd.Series({
            "playoff_points": playoff_pts,
            "finalist_points": finalist_pts,
            "champion_points": champion_pts,
            "meta_total": playoff_pts + finalist_pts + champion_pts
        })

    meta_scores = meta.copy()
    meta_scores = pd.concat([meta_scores, meta.apply(calc_row, axis=1)], axis=1)
    return meta_scores[["email", "playoff_points", "finalist_points", "champion_points", "meta_total"]]

def overall_leaderboard() -> pd.DataFrame:
    """Aggregate match + meta points into a leaderboard: email, name, total_points."""
    match_scores = compute_match_scores()
    meta_scores = compute_meta_scores()

    # Sum match points
    if match_scores.empty:
        match_agg = pd.DataFrame(columns=["email", "match_points"])
    else:
        match_agg = match_scores.groupby("email", as_index=False)["match_points"].sum()

    # Merge with meta
    if match_agg.empty and meta_scores.empty:
        fixtures, users = _load_baseframes()
        lb = users[["email", "name"]].copy()
        lb[["match_points", "playoff_points", "finalist_points", "champion_points", "meta_total"]] = 0
    else:
        lb = match_agg.merge(meta_scores, on="email", how="outer").fillna(0)
        fixtures, users = _load_baseframes()
        lb = lb.merge(users[["email", "name"]], on="email", how="left")

    # Total
    point_cols = ["match_points", "meta_total"]
    for c in ["playoff_points", "finalist_points", "champion_points"]:
        if c not in lb.columns:
            lb[c] = 0
    if "match_points" not in lb.columns:
        lb["match_points"] = 0
    if "meta_total" not in lb.columns:
        lb["meta_total"] = lb[["playoff_points", "finalist_points", "champion_points"]].sum(axis=1)

    lb["total_points"] = lb["match_points"] + lb["meta_total"]
    lb = lb.sort_values(["total_points", "match_points", "playoff_points"], ascending=[False, False, False]).reset_index(drop=True)

    # Add rank with ties
    lb["rank"] = lb["total_points"].rank(method="min", ascending=False).astype(int)
    # Order columns
    cols = ["rank", "name", "match_points", "playoff_points", "finalist_points", "champion_points", "total_points"]
    lb = lb[cols]
    return lb

def weekly_winners() -> Tuple[pd.DataFrame, Dict[int, pd.DataFrame]]:
    """Returns (weekly_totals, winners_by_week) with streak-based tie breaker."""
    match_scores = compute_match_scores()
    if match_scores.empty:
        return pd.DataFrame(), {}

    # Per-week totals
    weekly = match_scores.groupby(["email", "name", "week"], as_index=False)["match_points"].sum()

    # Compute longest streak of correct picks per user/week
    streak_data = []
    if "fixture_order" not in match_scores.columns:
        match_scores["fixture_order"] = 0
    ordered = match_scores.sort_values(["email", "week", "fixture_order"], na_position="last")
    for (email, week), sub in ordered.groupby(["email", "week"]):
        current = best = 0
        for _, row in sub.iterrows():
            if row.get("match_points", 0) > 0:
                current += 1
                if current > best:
                    best = current
            else:
                current = 0
        streak_data.append({"email": email, "week": week, "best_streak": best})
    streak_df = pd.DataFrame(streak_data)
    weekly = weekly.merge(streak_df, on=["email", "week"], how="left") if not streak_df.empty else weekly
    if "best_streak" not in weekly.columns:
        weekly["best_streak"] = 0

    winners_by_week = {}
    for week, sub in weekly.groupby("week"):
        top_points = sub["match_points"].max()
        contenders = sub[sub["match_points"] == top_points]
        best_streak = contenders["best_streak"].max()
        winners = contenders[contenders["best_streak"] == best_streak].sort_values("name")
        winners_by_week[week] = winners.reset_index(drop=True)

    weekly_totals = weekly.sort_values(["week", "match_points", "best_streak"], ascending=[True, False, False])
    return weekly_totals, winners_by_week
